use clap::{Parser, Subcommand};
use std::path::PathBuf;

use commands::client::ClientArgs;
use commands::service::ServiceArgs;

mod commands;
mod utils;

#[derive(Parser)]
#[command(name = "extip-rust")]
#[command(about = "External IP service with socket-based client")]
struct Cli {
    #[arg(short, long, default_value = "/tmp/extip.sock", env = "EXTIP_SOCKET")]
    socket_path: PathBuf,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Service(ServiceArgs),
    Client(ClientArgs),
}

fn main() {
    dotenv::dotenv().ok();

    let cli = Cli::parse();

    match cli.command {
        Commands::Service(args) => {
            commands::service::run(&cli.socket_path, args);
        }
        Commands::Client(args) => {
            commands::client::run(&cli.socket_path, args);
        }
    }
}
