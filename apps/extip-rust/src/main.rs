use clap::{Parser, Subcommand};
use std::path::PathBuf;

mod commands;
mod utils;

use commands::client::ClientArgs;
use commands::service::ServiceArgs;

include!(concat!(env!("OUT_DIR"), "/version.rs"));

#[derive(Parser)]
#[command(name = "extip-rust")]
#[command(version = VERSION)]
struct Cli {
    #[arg(short, long, default_value = "/tmp/extip.sock", env = "EXTIP_SOCKET")]
    socket_path: PathBuf,

    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Subcommand)]
enum Commands {
    Service(ServiceArgs),
    Client(ClientArgs),
}

fn main() {
    dotenv::dotenv().ok();

    let cli = Cli::parse();

    if cli.command.is_none() {
        println!("extip-rust {}", VERSION);
        return;
    }

    match cli.command.unwrap() {
        Commands::Service(args) => {
            commands::service::run(&cli.socket_path, args);
        }
        Commands::Client(args) => {
            commands::client::run(&cli.socket_path, args);
        }
    }
}
