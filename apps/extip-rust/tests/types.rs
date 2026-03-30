use extip_rust::utils::types::{ServiceState, SimpleIpInfo, Status};

#[test]
fn test_status_ready_serialization() {
    let status = Status::Ready;
    let json = serde_json::to_string(&status).unwrap();
    assert_eq!(json, "\"ready\"");
}

#[test]
fn test_status_error_serialization() {
    let status = Status::Error;
    let json = serde_json::to_string(&status).unwrap();
    assert_eq!(json, "\"error\"");
}

#[test]
fn test_status_updating_serialization() {
    let status = Status::Updating;
    let json = serde_json::to_string(&status).unwrap();
    assert_eq!(json, "\"updating\"");
}

#[test]
fn test_status_deserialization() {
    let status: Status = serde_json::from_str("\"ready\"").unwrap();
    assert_eq!(status, Status::Ready);

    let status: Status = serde_json::from_str("\"error\"").unwrap();
    assert_eq!(status, Status::Error);

    let status: Status = serde_json::from_str("\"updating\"").unwrap();
    assert_eq!(status, Status::Updating);
}

#[test]
fn test_simple_ipinfo_serialization() {
    let info = SimpleIpInfo {
        ip: "192.168.1.1".to_string(),
        asn: "AS12345".to_string(),
        as_name: "Example ASN".to_string(),
        as_domain: "example.com".to_string(),
        country_code: "US".to_string(),
        country: "United States".to_string(),
        continent_code: "NA".to_string(),
        continent: "North America".to_string(),
    };

    let json = serde_json::to_string(&info).unwrap();
    assert!(json.contains("192.168.1.1"));
    assert!(json.contains("AS12345"));
    assert!(json.contains("US"));
}

#[test]
fn test_simple_ipinfo_deserialization() {
    let json = r#"{
        "ip": "8.8.8.8",
        "asn": "AS15169",
        "as_name": "Google LLC",
        "as_domain": "google.com",
        "country_code": "US",
        "country": "United States",
        "continent_code": "NA",
        "continent": "North America"
    }"#;

    let info: SimpleIpInfo = serde_json::from_str(json).unwrap();
    assert_eq!(info.ip, "8.8.8.8");
    assert_eq!(info.asn, "AS15169");
    assert_eq!(info.as_name, "Google LLC");
    assert_eq!(info.as_domain, "google.com");
    assert_eq!(info.country_code, "US");
    assert_eq!(info.country, "United States");
    assert_eq!(info.continent_code, "NA");
    assert_eq!(info.continent, "North America");
}

#[test]
fn test_service_state_with_info() {
    let info = SimpleIpInfo {
        ip: "1.2.3.4".to_string(),
        asn: "AS123".to_string(),
        as_name: "Test Network".to_string(),
        as_domain: "test.net".to_string(),
        country_code: "DE".to_string(),
        country: "Germany".to_string(),
        continent_code: "EU".to_string(),
        continent: "Europe".to_string(),
    };

    let state = ServiceState {
        status: Status::Ready,
        info: Some(info),
        message: "Fetched 1.2.3.4".to_string(),
    };

    let json = serde_json::to_string(&state).unwrap();
    assert!(json.contains("\"ready\""));
    assert!(json.contains("1.2.3.4"));
    assert!(json.contains("Fetched 1.2.3.4"));
}

#[test]
fn test_service_state_without_info() {
    let state = ServiceState {
        status: Status::Error,
        info: None,
        message: "Connection failed".to_string(),
    };

    let json = serde_json::to_string(&state).unwrap();
    assert!(json.contains("\"error\""));
    assert!(json.contains("Connection failed"));
    assert!(json.contains("\"info\":null"));
}

#[test]
fn test_service_state_roundtrip() {
    let original = ServiceState {
        status: Status::Ready,
        info: Some(SimpleIpInfo {
            ip: "10.0.0.1".to_string(),
            asn: "AS100".to_string(),
            as_name: "Test ASN".to_string(),
            as_domain: "test.asn".to_string(),
            country_code: "RU".to_string(),
            country: "Russia".to_string(),
            continent_code: "EU".to_string(),
            continent: "Europe".to_string(),
        }),
        message: "OK".to_string(),
    };

    let json = serde_json::to_string(&original).unwrap();
    let decoded: ServiceState = serde_json::from_str(&json).unwrap();

    assert_eq!(decoded.status, original.status);
    assert_eq!(decoded.message, original.message);
    assert!(decoded.info.is_some());
    let info = decoded.info.unwrap();
    assert_eq!(info.ip, "10.0.0.1");
    assert_eq!(info.asn, "AS100");
}

#[test]
fn test_status_clone() {
    let status = Status::Ready;
    let cloned = status.clone();
    assert_eq!(status, cloned);
}

#[test]
fn test_simple_ipinfo_clone() {
    let info = SimpleIpInfo {
        ip: "1.1.1.1".to_string(),
        asn: "AS13335".to_string(),
        as_name: "Cloudflare".to_string(),
        as_domain: "cloudflare.com".to_string(),
        country_code: "US".to_string(),
        country: "United States".to_string(),
        continent_code: "NA".to_string(),
        continent: "North America".to_string(),
    };
    let cloned = info.clone();
    assert_eq!(info.ip, cloned.ip);
    assert_eq!(info.asn, cloned.asn);
}
