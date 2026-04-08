use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Status {
    Ready,
    Error,
    Updating,
}

#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
pub struct SimpleIpInfo {
    pub ip: String,
    pub asn: String,
    pub as_name: String,
    pub as_domain: String,
    pub country_code: String,
    pub country: String,
    pub continent_code: String,
    pub continent: String,
}

#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
pub struct ServiceState {
    pub status: Status,
    pub info: Option<SimpleIpInfo>,
    pub message: String,
    pub error_type: Option<String>,
}
