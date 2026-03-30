use extip_rust::commands::service::ServiceArgs;

#[test]
fn test_service_args_default_values() {
    let args = ServiceArgs {
        token: None,
        log_level: "INFO".to_string(),
        log_colorize: false,
        log_format: None,
        log_file: None,
    };
    assert_eq!(args.token, None);
    assert_eq!(args.log_level, "INFO");
    assert_eq!(args.log_colorize, false);
    assert_eq!(args.log_format, None);
    assert_eq!(args.log_file, None);
}

#[test]
fn test_service_args_with_token() {
    let args = ServiceArgs {
        token: Some("test_token".to_string()),
        log_level: "INFO".to_string(),
        log_colorize: false,
        log_format: None,
        log_file: None,
    };
    assert_eq!(args.token, Some("test_token".to_string()));
}

#[test]
fn test_service_args_with_log_level() {
    let args = ServiceArgs {
        token: None,
        log_level: "DEBUG".to_string(),
        log_colorize: false,
        log_format: None,
        log_file: None,
    };
    assert_eq!(args.log_level, "DEBUG");
}

#[test]
fn test_service_args_with_log_colorize() {
    let args = ServiceArgs {
        token: None,
        log_level: "INFO".to_string(),
        log_colorize: true,
        log_format: None,
        log_file: None,
    };
    assert_eq!(args.log_colorize, true);
}

#[test]
fn test_service_args_with_log_format() {
    let args = ServiceArgs {
        token: None,
        log_level: "INFO".to_string(),
        log_colorize: false,
        log_format: Some("%m%n".to_string()),
        log_file: None,
    };
    assert_eq!(args.log_format, Some("%m%n".to_string()));
}

#[test]
fn test_service_args_with_log_file() {
    let args = ServiceArgs {
        token: None,
        log_level: "INFO".to_string(),
        log_colorize: false,
        log_format: None,
        log_file: Some(std::path::PathBuf::from("/var/log/extip.log")),
    };
    assert!(args.log_file.is_some());
    assert_eq!(args.log_file.unwrap().to_str(), Some("/var/log/extip.log"));
}

#[test]
fn test_service_args_all_options() {
    let args = ServiceArgs {
        token: Some("my_token".to_string()),
        log_level: "WARN".to_string(),
        log_colorize: true,
        log_format: Some("%d %p %m".to_string()),
        log_file: Some(std::path::PathBuf::from("/tmp/extip.log")),
    };
    assert_eq!(args.token, Some("my_token".to_string()));
    assert_eq!(args.log_level, "WARN");
    assert_eq!(args.log_colorize, true);
    assert_eq!(args.log_format, Some("%d %p %m".to_string()));
    assert_eq!(args.log_file.unwrap().to_str(), Some("/tmp/extip.log"));
}

#[test]
fn test_service_args_error_log_level() {
    let args = ServiceArgs {
        token: None,
        log_level: "ERROR".to_string(),
        log_colorize: false,
        log_format: None,
        log_file: None,
    };
    assert_eq!(args.log_level, "ERROR");
}

#[test]
fn test_service_args_trace_log_level() {
    let args = ServiceArgs {
        token: None,
        log_level: "TRACE".to_string(),
        log_colorize: false,
        log_format: None,
        log_file: None,
    };
    assert_eq!(args.log_level, "TRACE");
}
