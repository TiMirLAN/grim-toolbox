use clap::Args;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::io::AsyncWriteExt;
use tokio::net::UnixListener;
use tokio::signal::ctrl_c;
use tokio::sync::Mutex;
use tracing::{debug, error, info, Level};
use tracing_appender::rolling::{RollingFileAppender, Rotation};
use tracing_subscriber::fmt::format::FmtSpan;
use tracing_subscriber::layer::SubscriberExt;
use tracing_subscriber::util::SubscriberInitExt;
use tracing_subscriber::Layer;

use crate::utils::ipinfo::{IpInfoClient, IPTABLES_TIMEOUT, UPDATING_TIMEOUT};
use crate::utils::route::RouteWatcher;
use crate::utils::serde::serialize_state;
use crate::utils::types::{ServiceState, SimpleIpInfo, Status};

#[derive(Args)]
pub struct ServiceArgs {
    #[arg(short, long, env = "EXTIP_TOKEN")]
    pub token: Option<String>,

    #[arg(short, long, default_value = "INFO", env = "EXTIP_LOG_LEVEL")]
    pub log_level: String,

    #[arg(long, env = "EXTIP_LOG_COLORIZE")]
    pub log_colorize: bool,

    #[arg(short = 'F', long, env = "EXTIP_LOG_FORMAT")]
    pub log_format: Option<String>,

    #[arg(long, env = "EXTIP_LOG_FILE")]
    pub log_file: Option<PathBuf>,
}

fn setup_logging(
    _log_level: &str,
    _log_colorize: bool,
    _log_format: Option<&str>,
    log_file: Option<&PathBuf>,
) {
    let env_filter = tracing_subscriber::EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info"));

    let subscriber = tracing_subscriber::registry().with(env_filter);

    if let Some(file) = log_file {
        let file_appender = RollingFileAppender::new(
            Rotation::DAILY,
            file.parent().unwrap_or(&PathBuf::from(".")),
            file.file_name().and_then(|n| n.to_str()).unwrap_or("extip.log"),
        );
        let (non_blocking, _guard) = tracing_appender::non_blocking(file_appender);

        let layer = tracing_subscriber::fmt::layer()
            .with_writer(non_blocking)
            .with_ansi(false)
            .with_span_events(FmtSpan::CLOSE);

        subscriber.with(layer).init();
    } else {
        let stdout_layer = tracing_subscriber::fmt::layer()
            .with_span_events(FmtSpan::CLOSE)
            .with_ansi(true)
            .with_target(true)
            .with_thread_ids(true)
            .with_line_number(true);

        let stderr_layer = tracing_subscriber::fmt::layer()
            .with_span_events(FmtSpan::CLOSE)
            .with_ansi(true)
            .with_target(true)
            .with_thread_ids(true)
            .with_line_number(true);

        let stdout_filter = tracing_subscriber::filter::LevelFilter::from_level(Level::INFO);
        let stderr_filter = tracing_subscriber::filter::LevelFilter::from_level(Level::ERROR);

        subscriber
            .with(stdout_layer.with_filter(stdout_filter))
            .with(stderr_layer.with_filter(stderr_filter))
            .init();
    }
}

struct ServiceStateInner {
    status: Status,
    info: Option<SimpleIpInfo>,
    message: String,
}

impl ServiceStateInner {
    fn new() -> Self {
        Self {
            status: Status::Updating,
            info: None,
            message: String::new(),
        }
    }
}

struct Service {
    ipinfo_client: IpInfoClient,
    attempt_number: u32,
    route_watcher: RouteWatcher,
}

impl Service {
    fn new(token: Option<String>) -> Self {
        Self {
            ipinfo_client: IpInfoClient::new(token),
            attempt_number: 0,
            route_watcher: RouteWatcher::new(),
        }
    }
}

pub fn run(socket_path: &PathBuf, args: ServiceArgs) {
    setup_logging(
        &args.log_level,
        args.log_colorize,
        args.log_format.as_deref(),
        args.log_file.as_ref(),
    );

    info!("Starting service...");

    let rt = tokio::runtime::Runtime::new().expect("Failed to create runtime");
    rt.block_on(async {
        run_service(socket_path, args.token).await;
    });
}

async fn run_service(socket_path: &PathBuf, token: Option<String>) {
    let state = Arc::new(Mutex::new(ServiceStateInner::new()));
    let service = Arc::new(Mutex::new(Service::new(token)));

    let server_handle = {
        let state = Arc::clone(&state);
        let socket_path = socket_path.clone();
        tokio::spawn(async move {
            if let Err(e) = run_server(&state, &socket_path).await {
                error!("Server error: {}", e);
            }
        })
    };

    let update_handle = {
        let state = Arc::clone(&state);
        let service = Arc::clone(&service);
        tokio::spawn(async move {
            loop {
                {
                    let mut s = service.lock().await;
                    s.attempt_number += 1;
                    let attempt = s.attempt_number;

                    {
                        let mut st = state.lock().await;
                        st.status = Status::Updating;
                        st.message = format!("Updating... Attempt #{}", attempt);
                    }

                    debug!("[{}] Updating ip...", attempt);

                    match s.ipinfo_client.fetch_simple_data().await {
                        Ok(info) => {
                            let ip = info.ip.clone();
                            let as_domain = info.as_domain.clone();
                            let mut st = state.lock().await;
                            st.status = Status::Ready;
                            st.info = Some(info);
                            st.message = format!("Fetched {}", ip);
                            debug!("IP fetched {} {}", ip, as_domain);
                        }
                        Err(e) => {
                            let err_msg = format!("IpInfoClientError: {}", e);
                            error!("Error '{}' fetching ip...", err_msg);
                            let mut st = state.lock().await;
                            st.status = Status::Error;
                            st.message = err_msg;
                        }
                    }
                }
                tokio::time::sleep(std::time::Duration::from_secs_f64(UPDATING_TIMEOUT)).await;

                {
                    let mut s = service.lock().await;
                    s.attempt_number = 0;
                }
            }
        })
    };

    let watcher_handle = {
        let state = Arc::clone(&state);
        let service = Arc::clone(&service);
        tokio::spawn(async move {
            loop {
                {
                    let mut s = service.lock().await;
                    if s.route_watcher.check_changed() {
                        info!("Iptables changed");

                        let attempt = {
                            let mut s = service.lock().await;
                            s.attempt_number += 1;
                            s.attempt_number
                        };

                        {
                            let mut st = state.lock().await;
                            st.status = Status::Updating;
                            st.message = format!("Updating... Attempt #{}", attempt);
                        }

                        match s.ipinfo_client.fetch_simple_data().await {
                            Ok(info) => {
                                let ip = info.ip.clone();
                                let mut st = state.lock().await;
                                st.status = Status::Ready;
                                st.info = Some(info);
                                st.message = format!("Fetched {}", ip);
                            }
                            Err(e) => {
                                let err_msg = format!("IpInfoClientError: {}", e);
                                error!("Error '{}' fetching ip...", err_msg);
                                let mut st = state.lock().await;
                                st.status = Status::Error;
                                st.message = err_msg;
                            }
                        }
                    }
                }
                tokio::time::sleep(std::time::Duration::from_secs_f64(IPTABLES_TIMEOUT)).await;
            }
        })
    };

    tokio::select! {
        _ = ctrl_c() => {
            info!("Service stopped by keyboard interrupt");
        }
        _ = server_handle => {}
        _ = update_handle => {}
        _ = watcher_handle => {}
    }
}

async fn run_server(
    state: &Arc<Mutex<ServiceStateInner>>,
    socket_path: &PathBuf,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    if socket_path.exists() {
        std::fs::remove_file(socket_path)?;
    }

    let listener = UnixListener::bind(socket_path)?;
    info!("Server started on {:?}", socket_path);

    loop {
        match listener.accept().await {
            Ok((mut writer, _)) => {
                debug!("Client connected");
                let st = state.lock().await;
                let response = ServiceState {
                    status: st.status.clone(),
                    info: st.info.clone(),
                    message: st.message.clone(),
                };
                let json = serialize_state(&response).map_err(|e| Box::new(e) as Box<dyn std::error::Error + Send + Sync>)?;
                writer.write_all(json.as_bytes()).await?;
            }
            Err(e) => {
                error!("Accept error: {}", e);
            }
        }
    }
}
