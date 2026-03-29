use clap::Args;
use std::path::PathBuf;

#[derive(Args)]
pub struct ServiceArgs {
    #[arg(short, long)]
    pub token: Option<String>,

    #[arg(short, long, default_value = "INFO")]
    pub log_level: String,

    #[arg(long)]
    pub log_colorize: bool,

    #[arg(short = 'F', long)]
    pub log_format: Option<String>,

    #[arg(long)]
    pub log_file: Option<PathBuf>,
}

pub fn run(socket_path: &PathBuf, args: ServiceArgs) {
    println!("service not implemented");
    println!("socket_path: {:?}", socket_path);
    println!("token: {:?}", args.token);
    println!("log_level: {}", args.log_level);
    println!("log_colorize: {}", args.log_colorize);
    println!("log_format: {:?}", args.log_format);
    println!("log_file: {:?}", args.log_file);
}
