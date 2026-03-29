use std::path::PathBuf;
use tokio::io::AsyncReadExt;
use tokio::net::UnixStream;

use super::types::ServiceState;

pub async fn receive_state(socket_path: &PathBuf) -> Result<ServiceState, String> {
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

pub fn serialize_state(state: &ServiceState) -> Result<String, serde_json::Error> {
    serde_json::to_string(state)
}
