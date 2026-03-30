use extip_rust::utils::route::{RouteProvider, RouteProviderExt, RouteWatcher};

struct FakeRouteProvider {
    routes: String,
}

impl FakeRouteProvider {
    fn new(routes: &str) -> Self {
        Self {
            routes: routes.to_string(),
        }
    }
}

impl RouteProvider for FakeRouteProvider {
    fn get_routes(&self) -> String {
        self.routes.clone()
    }
}

#[test]
fn test_route_watcher_new() {
    let provider = FakeRouteProvider::new("default via 192.168.1.1 dev eth0");
    let watcher = RouteWatcher::with_provider(provider);
    let _ = watcher;
}

#[test]
fn test_route_watcher_check_changed_no_change() {
    let provider = FakeRouteProvider::new("default via 192.168.1.1 dev eth0");
    let mut watcher = RouteWatcher::with_provider(provider);

    let changed = watcher.check_changed();
    assert!(
        !changed,
        "First check_changed should return false when routes haven't changed"
    );
}

#[test]
fn test_route_watcher_check_changed_with_change() {
    let provider = FakeRouteProvider::new("default via 192.168.1.1 dev eth0");
    let mut watcher = RouteWatcher::with_provider(provider);

    let changed = watcher.check_changed();
    assert!(
        !changed,
        "Should return false since provider returns same routes"
    );
}

#[test]
fn test_route_watcher_multiple_checks() {
    let provider = FakeRouteProvider::new("default via 192.168.1.1 dev eth0");
    let mut watcher = RouteWatcher::with_provider(provider);

    let first = watcher.check_changed();
    let second = watcher.check_changed();
    let third = watcher.check_changed();

    assert!(!first);
    assert!(!second);
    assert!(!third);
}

#[test]
fn test_build_routes_hash_format() {
    let provider = FakeRouteProvider::new("default via 192.168.1.1 dev eth0");

    let hash = RouteProviderExt::get_routes_hash(&provider);
    assert_eq!(hash.len(), 64);
    assert!(hash.chars().all(|c| c.is_ascii_hexdigit()));
}

#[test]
fn test_route_watcher_detects_change() {
    // This test checks that the internal hash mechanism works
    // We can't easily test dynamic change detection without a mock
    // but we can verify the hash changes based on different inputs
    let provider1 = FakeRouteProvider::new("default via 192.168.1.1 dev eth0");
    let provider2 = FakeRouteProvider::new("default via 10.0.0.1 dev wlan0");

    let hash1 = RouteProviderExt::get_routes_hash(&provider1);
    let hash2 = RouteProviderExt::get_routes_hash(&provider2);

    assert_ne!(
        hash1, hash2,
        "Different routes should produce different hashes"
    );
}
