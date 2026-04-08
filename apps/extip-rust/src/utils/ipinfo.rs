use reqwest::Client;
use thiserror::Error;

use crate::utils::types::SimpleIpInfo;

pub const UPDATING_TIMEOUT: f64 = 15.0;
pub const IPTABLES_TIMEOUT: f64 = 2.0;

#[derive(Error, Debug)]
pub enum IpInfoClientError {
    #[error("Response status {0}")]
    Status(u16),
    #[error("Request error: {0}")]
    Request(#[from] reqwest::Error),
    #[error("JSON parse error: {0}")]
    Json(#[from] serde_json::Error),
}

impl IpInfoClientError {
    pub fn error_type(&self) -> &'static str {
        match self {
            IpInfoClientError::Status(_) => "Response Error",
            IpInfoClientError::Request(e) => {
                if e.is_timeout() {
                    "Timeout"
                } else if e.is_connect() {
                    "No Internet"
                } else if e.is_request() {
                    "Request Error"
                } else {
                    "Network Error"
                }
            }
            IpInfoClientError::Json(_) => "Parse Error",
        }
    }
}

pub struct IpInfoClient {
    token: Option<String>,
}

impl IpInfoClient {
    pub fn new(token: Option<String>) -> Self {
        Self { token }
    }

    fn create_client(&self) -> Client {
        Client::builder()
            .timeout(std::time::Duration::from_secs_f64(UPDATING_TIMEOUT))
            .build()
            .expect("Failed to create HTTP client")
    }

    pub async fn fetch_simple_data(&self) -> Result<SimpleIpInfo, IpInfoClientError> {
        let client = self.create_client();
        
        let mut url = "https://api.ipinfo.io/lite/me".to_string();
        if let Some(ref token) = self.token {
            url = format!("{}?token={}", url, token);
        }

        let response = client.get(&url).send().await?;

        if response.status() != reqwest::StatusCode::OK {
            return Err(IpInfoClientError::Status(response.status().as_u16()));
        }

        let ip_info: SimpleIpInfo = response.json().await?;
        Ok(ip_info)
    }
}
