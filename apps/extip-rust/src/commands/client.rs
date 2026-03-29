use clap::Args;
use std::path::PathBuf;

#[derive(Args)]
pub struct ClientArgs {
    #[arg(short, long, default_value = "{{info.asn}} {{info.ip}}")]
    pub info_format: String,
}

pub fn run(socket_path: &PathBuf, args: ClientArgs) {
    println!("client not implemented");
    println!("socket_path: {:?}", socket_path);
    println!("info_format: {}", args.info_format);
}
