use clap::Args;
use std::path::PathBuf;

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

pub fn run(socket_path: &PathBuf, args: ServiceArgs) {
    println!("service not implemented");
    println!("socket_path: {:?}", socket_path);
    println!();
    println!("Environment variables used:");
    println!("  EXTIP_TOKEN: {:?}", args.token);
    println!("  EXTIP_LOG_LEVEL: {}", args.log_level);
    println!("  EXTIP_LOG_COLORIZE: {}", args.log_colorize);
    println!("  EXTIP_LOG_FORMAT: {:?}", args.log_format);
    println!("  EXTIP_LOG_FILE: {:?}", args.log_file);
}
