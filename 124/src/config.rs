use serde::{Serialize, Deserialize};
use dirs::home_dir;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub device_id: String,
    pub device_name: String,
    pub server_port: u16,
    pub chunk_size: usize,
    pub confirm_timeout: u64,
    pub max_retry: u32,
    pub enable_encryption: bool,
    pub auto_accept_trusted: bool,
    pub history_limit: usize,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            device_id: uuid::Uuid::new_v4().to_string(),
            device_name: format!("{}-{}", get_hostname(), std::env::consts::OS),
            server_port: 38765,
            chunk_size: 1024 * 1024,
            confirm_timeout: 30,
            max_retry: 3,
            enable_encryption: true,
            auto_accept_trusted: true,
            history_limit: 200,
        }
    }
}

impl AppConfig {
    pub async fn load() -> Self {
        let path = Self::config_path();
        if let Ok(data) = tokio::fs::read_to_string(path).await {
            if let Ok(config) = serde_json::from_str(&data) {
                return config;
            }
        }
        let config = Self::default();
        config.save().await;
        config
    }

    pub async fn save(&self) {
        let path = Self::config_path();
        if let Ok(json) = serde_json::to_string_pretty(self) {
            tokio::fs::create_dir_all(path.parent().unwrap()).await.ok();
            tokio::fs::write(path, json).await.ok();
        }
    }

    fn config_path() -> PathBuf {
        home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".clipboard-sync")
            .join("config.json")
    }
}

fn get_hostname() -> String {
    hostname::get()
        .ok()
        .and_then(|h| h.into_string().ok())
        .unwrap_or_else(|| "unknown".to_string())
}
