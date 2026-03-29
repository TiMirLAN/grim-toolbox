use clap::Args;
use std::path::PathBuf;
use tinytemplate::TinyTemplate;

use crate::utils::serde::receive_state;
use crate::utils::types::{ServiceState, Status};

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
                            eprintln!("{}", e);
                            std::process::exit(1);
                        }
                    }
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
