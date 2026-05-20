use crate::types::Config;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, thiserror::Error)]
pub enum ConfigError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    
    #[error("TOML parse error: {0}")]
    TomlParse(#[from] toml::de::Error),
    
    #[error("TOML serialize error: {0}")]
    TomlSerialize(#[from] toml::ser::Error),
}

pub fn find_config_file() -> Option<PathBuf> {
    let candidates = [
        "commitlint.toml",
        ".commitlint.toml",
        "commitlintrc.toml",
        ".commitlintrc",
    ];
    
    for candidate in &candidates {
        let path = Path::new(candidate);
        if path.exists() {
            return Some(path.to_path_buf());
        }
    }
    
    None
}

pub fn load_config() -> Result<Config, ConfigError> {
    if let Some(path) = find_config_file() {
        let content = fs::read_to_string(&path)?;
        let config: Config = toml::from_str(&content)?;
        Ok(config)
    } else {
        Ok(Config::default())
    }
}

pub fn load_config_from<P: AsRef<Path>>(path: P) -> Result<Config, ConfigError> {
    let content = fs::read_to_string(path)?;
    let config: Config = toml::from_str(&content)?;
    Ok(config)
}

pub fn save_config<P: AsRef<Path>>(config: &Config, path: P) -> Result<(), ConfigError> {
    let content = toml::to_string_pretty(config)?;
    fs::write(path, content)?;
    Ok(())
}

pub fn generate_default_config<P: AsRef<Path>>(path: P) -> Result<(), ConfigError> {
    let config = Config::default();
    save_config(&config, path)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs::File;
    use std::io::Write;
    use tempfile::tempdir;

    #[test]
    fn test_load_default_config() {
        let config = load_config();
        assert!(config.is_ok());
    }

    #[test]
    fn test_save_and_load_config() {
        let dir = tempdir().unwrap();
        let config_path = dir.path().join("commitlint.toml");
        
        let mut config = Config::default();
        config.min_length = 5;
        config.max_length = 80;
        
        save_config(&config, &config_path).unwrap();
        let loaded = load_config_from(&config_path).unwrap();
        
        assert_eq!(loaded.min_length, 5);
        assert_eq!(loaded.max_length, 80);
    }

    #[test]
    fn test_generate_default_config() {
        let dir = tempdir().unwrap();
        let config_path = dir.path().join("commitlint.toml");
        
        generate_default_config(&config_path).unwrap();
        assert!(config_path.exists());
        
        let content = fs::read_to_string(&config_path).unwrap();
        assert!(content.contains("types"));
    }
}
