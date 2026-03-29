use clap::Args;
use serde::Deserialize;
use std::path::PathBuf;
use tinytemplate::TinyTemplate;
use tokio::io::AsyncReadExt;
use tokio::net::UnixStream;

#[derive(Args)]
pub struct ClientArgs {
    #[arg(
        short,
        long,
        default_value = "{{info.asn}} {{info.ip}}",
        env = "EXTIP_INFO_FORMAT"
    )]
    pub info_format: String,
}

#[derive(Debug, Clone, Deserialize, serde::Serialize)]
#[serde(rename_all = "lowercase")]
pub(crate) enum Status {
    Ready,
    Error,
    Updating,
}

#[derive(Debug, Clone, Deserialize, serde::Serialize)]
pub(crate) struct SimpleIpInfo {
    ip: String,
    asn: String,
    as_name: String,
    as_domain: String,
    country_code: String,
    country: String,
    continent_code: String,
    continent: String,
}

#[derive(Debug, Clone, Deserialize, serde::Serialize)]
pub(crate) struct ServiceState {
    status: Status,
    info: Option<SimpleIpInfo>,
    message: String,
}

pub async fn fetch_info(socket_path: &PathBuf) -> Result<ServiceState, String> {
    let mut stream = UnixStream::connect(socket_path)
        .await
        .map_err(|e| format!("{}", e))?;

    let mut buffer = Vec::new();
    stream.read_to_end(&mut buffer)
        .await
        .map_err(|e| format!("{}", e))?;

    let state: ServiceState = serde_json::from_slice(&buffer)
        .map_err(|e| format!("Failed to parse JSON: {}", e))?;

    Ok(state)
}

fn render_template(template_str: &str, state: &ServiceState) -> String {
    let mut tt = TinyTemplate::new();
    let transformed = template_str.replace("{{", "{").replace("}}", "}");
    tt.add_template("output", &transformed).unwrap();
    tt.render("output", state).unwrap_or_else(|_| template_str.to_string())
}

pub fn run(socket_path: &PathBuf, args: ClientArgs) {
    let rt = tokio::runtime::Runtime::new().unwrap();
    let result = rt.block_on(async {
        fetch_info(socket_path).await
    });

    match result {
        Ok(state) => {
            match state.status {
                Status::Ready => {
                    let output = render_template(&args.info_format, &state);
                    print!("{}", output);
                }
                Status::Updating => {
                    print!("{}", state.message);
                }
                Status::Error => {
                    print!("Error: {}", state.message);
                }
            }
        }
        Err(e) => {
            if e.contains("No such file or directory") || e.contains("not found") {
                print!("Service is not started");
            } else {
                print!("Unknown error: {}", e);
            }
        }
    }
}
