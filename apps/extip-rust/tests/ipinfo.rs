use extip_rust::utils::ipinfo::{IpInfoClient, IpInfoClientError, IPTABLES_TIMEOUT, UPDATING_TIMEOUT};
use mockito::Server;

#[test]
fn test_client_creation_without_token() {
    let client = IpInfoClient::new(None);
    // Client should be created successfully
    // Just verify it doesn't panic
    let _ = client;
}

#[test]
fn test_client_creation_with_token() {
    let client = IpInfoClient::new(Some("test_token".to_string()));
    let _ = client;
}

#[tokio::test]
async fn test_fetch_simple_data_success() {
    let mut server = Server::new_async().await;
    
    let mock = server.mock("GET", "/lite/me")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(r#"{
            "ip": "8.8.8.8",
            "asn": "AS15169",
            "as_name": "Google LLC",
            "as_domain": "google.com",
            "country_code": "US",
            "country": "United States",
            "continent_code": "NA",
            "continent": "North America"
        }"#)
        .create();

    let url = server.url();
    
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .unwrap();
    
    let response = client.get(format!("{}/lite/me", url)).send().await.unwrap();
    assert_eq!(response.status(), 200);
    
    let ip_info: extip_rust::utils::types::SimpleIpInfo = response.json().await.unwrap();
    assert_eq!(ip_info.ip, "8.8.8.8");
    assert_eq!(ip_info.asn, "AS15169");
    assert_eq!(ip_info.country_code, "US");
    
    mock.assert();
}

#[tokio::test]
async fn test_fetch_simple_data_with_token() {
    let mut server = Server::new_async().await;
    
    let mock = server.mock("GET", "/lite/me")
        .match_query(mockito::Matcher::Regex("token=test123".to_string()))
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(r#"{
            "ip": "1.2.3.4",
            "asn": "AS12345",
            "as_name": "Test Network",
            "as_domain": "test.net",
            "country_code": "DE",
            "country": "Germany",
            "continent_code": "EU",
            "continent": "Europe"
        }"#)
        .create();

    let url = server.url();
    
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .unwrap();
    
    let response = client.get(format!("{}/lite/me?token=test123", url)).send().await.unwrap();
    assert_eq!(response.status(), 200);
    
    let ip_info: extip_rust::utils::types::SimpleIpInfo = response.json().await.unwrap();
    assert_eq!(ip_info.ip, "1.2.3.4");
    assert_eq!(ip_info.country_code, "DE");
    
    mock.assert();
}

#[tokio::test]
async fn test_fetch_simple_data_error_status() {
    let mut server = Server::new_async().await;
    
    let mock = server.mock("GET", "/lite/me")
        .with_status(429)
        .with_header("content-type", "application/json")
        .with_body(r#"{"error": "Rate limit exceeded"}"#)
        .create();

    let url = server.url();
    
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .unwrap();
    
    let response = client.get(format!("{}/lite/me", url)).send().await.unwrap();
    assert_eq!(response.status().as_u16(), 429);
    
    mock.assert();
}

#[test]
fn test_constants_defined() {
    let timeout = UPDATING_TIMEOUT;
    assert_eq!(timeout, 15.0);
    
    let ipt_timeout = IPTABLES_TIMEOUT;
    assert_eq!(ipt_timeout, 2.0);
}

#[test]
fn test_error_type_status() {
    let err = IpInfoClientError::Status(429);
    assert_eq!(err.error_type(), "Response Error");
}

#[test]
fn test_error_type_status_500() {
    let err = IpInfoClientError::Status(500);
    assert_eq!(err.error_type(), "Response Error");
}

#[test]
fn test_error_type_status_401() {
    let err = IpInfoClientError::Status(401);
    assert_eq!(err.error_type(), "Response Error");
}
