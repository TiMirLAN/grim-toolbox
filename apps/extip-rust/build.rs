use std::{
    env,
    fs::{self, File},
    io::{BufRead, BufReader, Read},
    path::Path,
};

use sha2::{Digest, Sha256};

fn main() {
    let out_dir = env::var("OUT_DIR").unwrap();
    let dest_path = Path::new(&out_dir).join("version.rs");

    let content = if cfg!(feature = "dev-version") {
        let hash = compute_file_hash();
        let line = "\npub const VERSION: &str = \"";
        let mid = " (dev)\";\npub const BUILD_HASH: &str = \"";
        let end = "\";";
        format!("{}{}{}{}{}", line, hash, mid, hash, end)
    } else {
        let v = get_cargo_version().unwrap_or_else(|| "0.0.0".to_string());
        let line = "\npub const VERSION: &str = \"";
        let mid = " (release)\";\npub const BUILD_HASH: &str = \"";
        let end = "\";";
        format!("{}{}{}{}", line, v, mid, end)
    };

    fs::write(&dest_path, content).unwrap();
    println!("cargo:rerun-if-changed=src/*");
    println!("cargo:rerun-if-changed=Cargo.toml");
    println!("cargo:rerun-if-changed=build.rs");
}

fn get_cargo_version() -> Option<String> {
    let file = File::open("Cargo.toml").ok()?;
    let reader = BufReader::new(file);
    let mut in_package = false;

    for line in reader.lines().flatten() {
        let line = line.trim();
        if line.starts_with("[package]") {
            in_package = true;
            continue;
        }
        if in_package && line.starts_with("version") {
            let version = line.split('=').nth(1)?.trim();
            let version = version.trim_matches('"');
            return Some(version.to_string());
        }
    }
    None
}

fn compute_file_hash() -> String {
    let mut hasher = Sha256::new();
    let sources = [
        "src/main.rs",
        "src/lib.rs",
        "src/commands/mod.rs",
        "src/commands/client.rs",
        "src/commands/service.rs",
        "src/utils/mod.rs",
    ];

    for source in &sources {
        if let Ok(mut file) = File::open(source) {
            let mut content = String::new();
            let _ = file.read_to_string(&mut content);
            hasher.update(content.as_bytes());
        }
    }

    let result = hasher.finalize();
    format!("{:x}", result)[..8].to_string()
}
