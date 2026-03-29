use clap::Args;
use std::path::PathBuf;

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

pub fn run(socket_path: &PathBuf, args: ClientArgs) {
    println!("client not implemented");
    println!("socket_path: {:?}", socket_path);
    println!();
    println!("Environment variables used:");
    println!("  EXTIP_INFO_FORMAT: {}", args.info_format);
}
