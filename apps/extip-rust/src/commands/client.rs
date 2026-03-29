use clap::Args;
use std::path::PathBuf;
use tinytemplate::TinyTemplate;

use crate::utils::serde::receive_state;
use crate::utils::types::{ServiceState, Status};

const DEFAULT_LOG_FILE: &str = "~/.local/share/extip/client.log";

fn log_error(log_file: &Option<PathBuf>, message: &str) {
    let path = match log_file {
        Some(p) if p.as_os_str().is_empty() => return,
        Some(p) => p,
        None => &PathBuf::from(DEFAULT_LOG_FILE),
    };

    let path = if path.starts_with("~") {
        dirs::home_dir()
            .map(|h| h.join(path.strip_prefix("~").unwrap_or(path)))
            .unwrap_or_else(|| path.clone())
    } else {
        path.clone()
    };

    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }

    if let Ok(mut file) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&path)
    {
        use std::io::Write;
        let timestamp = chrono::Local::now().format("%Y-%m-%d %H:%M:%S");
        let _ = writeln!(file, "[{}] {}", timestamp, message);
    }
}

#[derive(Args)]
pub struct ClientArgs {
    #[arg(
        short,
        long,
        default_value = "{info.asn} {info.ip}",
        env = "EXTIP_INFO_FORMAT",
        help = "Specify how you want to display the IP info using placeholders like: {info.<field>}. Available fields: ip, asn, as_name, as_domain, country_code, country, continent_code, continent"
    )]
    pub info_format: String,

    #[arg(
        long,
        default_value = DEFAULT_LOG_FILE,
        env = "EXTIP_LOG_FILE",
        help = "Path to log file for errors. Set to empty string to disable file logging. [default: ~/.local/share/extip/client.log]"
    )]
    pub log_file: Option<PathBuf>,
}

fn render_template(template_str: &str, state: &ServiceState) -> Result<String, String> {
    let mut tt = TinyTemplate::new();
    tt.add_template("output", template_str)
        .map_err(|e| format!("Template error: {}", e))?;
    tt.render("output", state)
        .map_err(|e| format!("Template render error: {}", e))
}

pub fn run(socket_path: &PathBuf, args: ClientArgs) {
    let rt = tokio::runtime::Runtime::new().unwrap();
    let result = rt.block_on(async {
        receive_state(socket_path).await
    });

    match result {
        Ok(state) => {
            match state.status {
                Status::Ready => {
                    match render_template(&args.info_format, &state) {
                        Ok(output) => print!("{}", output),
                        Err(e) => {
                            log_error(&args.log_file, &e);
                            eprintln!("{}", e);
                            std::process::exit(1);
                        }
                    }
                }
                Status::Updating => {
                    print!("{}", state.message);
                }
                Status::Error => {
                    let err_msg = format!("Service error: {}", state.message);
                    log_error(&args.log_file, &err_msg);
                    print!("Error: {}", state.message);
                }
            }
        }
        Err(e) => {
            if e.contains("No such file or directory") || e.contains("not found") {
                print!("Missing service");
            } else {
                let err_msg = format!("Socket error [{}]: {}", socket_path.display(), e);
                log_error(&args.log_file, &err_msg);
                print!("Error");
            }
        }
    }
}
