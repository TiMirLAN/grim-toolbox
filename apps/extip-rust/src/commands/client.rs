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

fn render_template(template_str: &str, state: &ServiceState) -> String {
    let mut tt = TinyTemplate::new();
    tt.add_template("output", template_str).unwrap();
    tt.render("output", state).unwrap_or_else(|_| template_str.to_string())
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
