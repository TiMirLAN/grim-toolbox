use std::process::Command;

use sha2::{Digest, Sha256};

pub trait RouteProvider: Send + Sync {
    fn get_routes(&self) -> String;
}

pub struct SystemRouteProvider;

impl RouteProvider for SystemRouteProvider {
    fn get_routes(&self) -> String {
        let output = Command::new("ip")
            .arg("route")
            .arg("show")
            .output()
            .expect("Failed to run ip route show")
            .stdout;
        String::from_utf8_lossy(&output).to_string()
    }
}

pub struct RouteWatcher<R: RouteProvider> {
    table_cache: String,
    provider: R,
}

impl RouteWatcher<SystemRouteProvider> {
    pub fn new() -> Self {
        let provider = SystemRouteProvider;
        let table_cache = provider.get_routes_hash();
        Self {
            table_cache,
            provider,
        }
    }
}

impl<R: RouteProvider> RouteWatcher<R> {
    #[allow(dead_code)]
    pub fn with_provider(provider: R) -> Self {
        let table_cache = provider.get_routes_hash();
        Self {
            table_cache,
            provider,
        }
    }

    pub fn check_changed(&mut self) -> bool {
        let cache = self.provider.get_routes_hash();
        if cache == self.table_cache {
            return false;
        }
        self.table_cache = cache;
        true
    }
}

pub trait RouteProviderExt {
    fn get_routes_hash(&self) -> String;
}

impl<R: RouteProvider> RouteProviderExt for R {
    fn get_routes_hash(&self) -> String {
        let output = self.get_routes();
        let mut hasher = Sha256::new();
        hasher.update(output.as_bytes());
        format!("{:x}", hasher.finalize())
    }
}
