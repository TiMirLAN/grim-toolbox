use clap::{Args, Parser, Subcommand};
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "extip-rust")]
#[command(about = "External IP service with socket-based client")]
struct Cli {
    #[arg(short, long, default_value = "/tmp/extip.sock")]
    socket_path: PathBuf,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Service(ServiceArgs),
    Client(ClientArgs),
}

#[derive(Args)]
struct ServiceArgs {
    #[arg(short, long)]
    token: Option<String>,

    #[arg(short, long, default_value = "INFO")]
    log_level: String,

    #[arg(long)]
    log_colorize: bool,

    #[arg(short = 'F', long)]
    log_format: Option<String>,

    #[arg(long)]
    log_file: Option<PathBuf>,
}

#[derive(Args)]
struct ClientArgs {
    #[arg(short, long, default_value = "{{info.asn}} {{info.ip}}")]
    info_format: String,
}

fn main() {
    let cli = Cli::parse();

    match cli.command {
        Commands::Service(args) => {
            println!("service not implemented");
            println!("socket_path: {:?}", cli.socket_path);
            println!("token: {:?}", args.token);
            println!("log_level: {}", args.log_level);
            println!("log_colorize: {}", args.log_colorize);
            println!("log_format: {:?}", args.log_format);
            println!("log_file: {:?}", args.log_file);
        }
        Commands::Client(args) => {
            println!("client not implemented");
            println!("socket_path: {:?}", cli.socket_path);
            println!("info_format: {}", args.info_format);
        }
    }
}
