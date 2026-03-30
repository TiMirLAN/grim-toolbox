use extip_rust::utils::serde::serialize_state;
use extip_rust::utils::types::{ServiceState, SimpleIpInfo, Status};

#[test]
fn test_serialize_state_ready_with_info() {
    let state = ServiceState {
        status: Status::Ready,
        info: Some(SimpleIpInfo {
            ip: "192.168.1.1".to_string(),
            asn: "AS12345".to_string(),
            as_name: "Test Network".to_string(),
            as_domain: "test.com".to_string(),
            country_code: "US".to_string(),
            country: "United States".to_string(),
            continent_code: "NA".to_string(),
            continent: "North America".to_string(),
        }),
        message: "OK".to_string(),
    };

    let result = serialize_state(&state);
    assert!(result.is_ok());

    let json = result.unwrap();
    assert!(json.contains("\"ready\""));
    assert!(json.contains("192.168.1.1"));
    assert!(json.contains("AS12345"));
    assert!(json.contains("\"US\""));
}

#[test]
fn test_serialize_state_error_without_info() {
    let state = ServiceState {
        status: Status::Error,
        info: None,
        message: "Connection refused".to_string(),
    };

    let result = serialize_state(&state);
    assert!(result.is_ok());

    let json = result.unwrap();
    assert!(json.contains("\"error\""));
    assert!(json.contains("Connection refused"));
    assert!(json.contains("\"info\":null"));
}

#[test]
fn test_serialize_state_updating() {
    let state = ServiceState {
        status: Status::Updating,
        info: None,
        message: "Updating... Attempt #1".to_string(),
    };

    let result = serialize_state(&state);
    assert!(result.is_ok());

    let json = result.unwrap();
    assert!(json.contains("\"updating\""));
    assert!(json.contains("Updating"));
}

#[test]
fn test_serialize_state_valid_json() {
    let state = ServiceState {
        status: Status::Ready,
        info: Some(SimpleIpInfo {
            ip: "8.8.8.8".to_string(),
            asn: "AS15169".to_string(),
            as_name: "Google LLC".to_string(),
            as_domain: "google.com".to_string(),
            country_code: "US".to_string(),
            country: "United States".to_string(),
            continent_code: "NA".to_string(),
            continent: "North America".to_string(),
        }),
        message: "Fetched".to_string(),
    };

    let json = serialize_state(&state).unwrap();
    let parsed: ServiceState = serde_json::from_str(&json).unwrap();

    assert_eq!(parsed.status, Status::Ready);
    assert_eq!(parsed.info.as_ref().unwrap().ip, "8.8.8.8");
}

#[test]
fn test_serialize_state_empty_message() {
    let state = ServiceState {
        status: Status::Ready,
        info: None,
        message: String::new(),
    };

    let result = serialize_state(&state);
    assert!(result.is_ok());
}

#[test]
fn test_serialize_state_unicode_message() {
    let state = ServiceState {
        status: Status::Error,
        info: None,
        message: "Ошибка: невозможно подключиться".to_string(),
    };

    let result = serialize_state(&state);
    assert!(result.is_ok());

    let json = result.unwrap();
    assert!(json.contains("Ошибка"));
}
