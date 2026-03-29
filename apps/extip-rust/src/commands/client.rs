use clap::Args;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use tinytemplate::TinyTemplate;
use tokio::io::AsyncReadExt;
use tokio::net::UnixStream;

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
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Status {
    Ready,
    Error,
    Updating,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct SimpleIpInfo {
    pub ip: String,
    pub asn: String,
    pub as_name: String,
    pub as_domain: String,
    pub country_code: String,
    pub country: String,
    pub continent_code: String,
    pub continent: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ServiceState {
    pub status: Status,
    pub info: Option<SimpleIpInfo>,
    pub message: String,
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
    tt.add_template("output", template_str).unwrap();
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
