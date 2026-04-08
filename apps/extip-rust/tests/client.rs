use extip_rust::utils::types::{ServiceState, SimpleIpInfo, Status};

#[test]
fn test_render_template_ready_state() {
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
        error_type: None,
    };

    let result = extip_rust::commands::client::render_template("{info.ip}", &state);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "192.168.1.1");
}

#[test]
fn test_render_template_with_asn() {
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
        message: "OK".to_string(),
        error_type: None,
    };

    let result = extip_rust::commands::client::render_template("{info.asn} {info.ip}", &state);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "AS15169 8.8.8.8");
}

#[test]
fn test_render_template_all_fields() {
    let state = ServiceState {
        status: Status::Ready,
        info: Some(SimpleIpInfo {
            ip: "1.2.3.4".to_string(),
            asn: "AS100".to_string(),
            as_name: "Test".to_string(),
            as_domain: "test.net".to_string(),
            country_code: "RU".to_string(),
            country: "Russia".to_string(),
            continent_code: "EU".to_string(),
            continent: "Europe".to_string(),
        }),
        message: "OK".to_string(),
        error_type: None,
    };

    let template = "{info.asn} {info.ip} {info.country_code} {info.country}";
    let result = extip_rust::commands::client::render_template(template, &state);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "AS100 1.2.3.4 RU Russia");
}

#[test]
fn test_render_template_no_info() {
    let state = ServiceState {
        status: Status::Error,
        info: None,
        message: "Error".to_string(),
        error_type: Some("No Internet".to_string()),
    };

    let result = extip_rust::commands::client::render_template("No data", &state);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "No data");
}

#[test]
fn test_render_template_invalid_field() {
    let state = ServiceState {
        status: Status::Ready,
        info: Some(SimpleIpInfo {
            ip: "1.1.1.1".to_string(),
            asn: "AS13335".to_string(),
            as_name: "Cloudflare".to_string(),
            as_domain: "cloudflare.com".to_string(),
            country_code: "US".to_string(),
            country: "United States".to_string(),
            continent_code: "NA".to_string(),
            continent: "North America".to_string(),
        }),
        message: "OK".to_string(),
        error_type: None,
    };

    let result = extip_rust::commands::client::render_template("{info.invalid_field}", &state);
    assert!(result.is_err());
}

#[test]
fn test_render_template_country_and_continent() {
    let state = ServiceState {
        status: Status::Ready,
        info: Some(SimpleIpInfo {
            ip: "10.0.0.1".to_string(),
            asn: "AS200".to_string(),
            as_name: "Example".to_string(),
            as_domain: "example.org".to_string(),
            country_code: "JP".to_string(),
            country: "Japan".to_string(),
            continent_code: "AS".to_string(),
            continent: "Asia".to_string(),
        }),
        message: "OK".to_string(),
        error_type: None,
    };

    let result =
        extip_rust::commands::client::render_template("{info.country} ({info.continent})", &state);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "Japan (Asia)");
}

#[test]
fn test_render_template_as_domain() {
    let state = ServiceState {
        status: Status::Ready,
        info: Some(SimpleIpInfo {
            ip: "172.16.0.1".to_string(),
            asn: "AS400".to_string(),
            as_name: "Example Net".to_string(),
            as_domain: "example.net".to_string(),
            country_code: "GB".to_string(),
            country: "United Kingdom".to_string(),
            continent_code: "EU".to_string(),
            continent: "Europe".to_string(),
        }),
        message: "OK".to_string(),
        error_type: None,
    };

    let result = extip_rust::commands::client::render_template("{info.as_domain}", &state);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "example.net");
}

use tempfile::TempDir;

#[test]
fn test_client_args_default_info_format() {
    let args = extip_rust::commands::client::ClientArgs {
        info_format: "{info.asn} {info.ip}".to_string(),
        error_format: "{error_type}".to_string(),
        log_file: None,
    };
    assert_eq!(args.info_format, "{info.asn} {info.ip}");
}

#[test]
fn test_client_args_with_custom_format() {
    let args = extip_rust::commands::client::ClientArgs {
        info_format: "{info.country}".to_string(),
        error_format: "Error: {error_type}".to_string(),
        log_file: Some(std::path::PathBuf::from("/tmp/test.log")),
    };
    assert_eq!(args.info_format, "{info.country}");
    assert!(args.log_file.is_some());
}

#[test]
fn test_render_error_type_response_error() {
    let state = ServiceState {
        status: Status::Error,
        info: None,
        message: "Rate limit exceeded".to_string(),
        error_type: Some("Response Error".to_string()),
    };

    let result = extip_rust::commands::client::render_template("{error_type}", &state);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "Response Error");
}

#[test]
fn test_render_error_type_timeout() {
    let state = ServiceState {
        status: Status::Error,
        info: None,
        message: "Request timed out".to_string(),
        error_type: Some("Timeout".to_string()),
    };

    let result = extip_rust::commands::client::render_template("{error_type}", &state);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "Timeout");
}

#[test]
fn test_render_error_type_no_internet() {
    let state = ServiceState {
        status: Status::Error,
        info: None,
        message: "Connection refused".to_string(),
        error_type: Some("No Internet".to_string()),
    };

    let result = extip_rust::commands::client::render_template("{error_type}", &state);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "No Internet");
}

#[test]
fn test_render_error_type_combined_template() {
    let state = ServiceState {
        status: Status::Error,
        info: None,
        message: "Service unavailable".to_string(),
        error_type: Some("Network Error".to_string()),
    };

    let result = extip_rust::commands::client::render_template(
        "Status: {status}, Error: {error_type}",
        &state,
    );
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "Status: error, Error: Network Error");
}

#[test]
fn test_render_error_type_none_in_ready_state() {
    let state = ServiceState {
        status: Status::Ready,
        info: Some(SimpleIpInfo {
            ip: "1.2.3.4".to_string(),
            asn: "AS100".to_string(),
            as_name: "Test".to_string(),
            as_domain: "test.net".to_string(),
            country_code: "RU".to_string(),
            country: "Russia".to_string(),
            continent_code: "EU".to_string(),
            continent: "Europe".to_string(),
        }),
        message: "OK".to_string(),
        error_type: None,
    };

    let result = extip_rust::commands::client::render_template("{error_type}", &state);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "");
}

#[test]
fn test_error_format_custom_value() {
    let args = extip_rust::commands::client::ClientArgs {
        info_format: "{info.ip}".to_string(),
        error_format: "ERR: {error_type}".to_string(),
        log_file: None,
    };
    assert_eq!(args.error_format, "ERR: {error_type}");
}

#[test]
fn test_render_with_message_field() {
    let state = ServiceState {
        status: Status::Error,
        info: None,
        message: "Connection refused".to_string(),
        error_type: Some("No Internet".to_string()),
    };

    let result = extip_rust::commands::client::render_template("{message} ({error_type})", &state);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "Connection refused (No Internet)");
}
