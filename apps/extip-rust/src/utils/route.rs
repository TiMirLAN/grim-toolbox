use std::process::Command;

use sha2::{Digest, Sha256};

pub struct RouteWatcher {
    table_cache: String,
}

impl RouteWatcher {
    pub fn new() -> Self {
        let table_cache = Self::build_routes_hash();
        Self { table_cache }
    }

    fn build_routes_hash() -> String {
        let output = Command::new("ip")
            .arg("route")
            .arg("show")
            .output()
            .expect("Failed to run ip route show")
            .stdout;
        let mut hasher = Sha256::new();
        hasher.update(&output);
        format!("{:x}", hasher.finalize())
    }

    pub fn check_changed(&mut self) -> bool {
        let cache = Self::build_routes_hash();
        if cache == self.table_cache {
            return false;
        }
        self.table_cache = cache;
        true
    }
}
