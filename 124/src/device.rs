use crate::models::DeviceInfo;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use dirs::home_dir;
use serde_json;

#[derive(Clone)]
pub struct DeviceManager {
    whitelist: Arc<RwLock<HashMap<String, DeviceInfo>>>,
    data_path: std::path::PathBuf,
}

impl DeviceManager {
    pub async fn new() -> Self {
        let data_path = home_dir()
            .unwrap_or_else(|| std::path::PathBuf::from("."))
            .join(".clipboard-sync");
        
        std::fs::create_dir_all(&data_path).ok();
        
        let mut manager = Self {
            whitelist: Arc::new(RwLock::new(HashMap::new())),
            data_path,
        };
        
        manager.load_whitelist().await;
        manager
    }

    async fn load_whitelist(&mut self) {
        let path = self.data_path.join("whitelist.json");
        if let Ok(data) = std::fs::read_to_string(path) {
            if let Ok(devices) = serde_json::from_str::<Vec<DeviceInfo>>(&data) {
                let mut whitelist = self.whitelist.write().await;
                for device in devices {
                    whitelist.insert(device.id.clone(), device);
                }
            }
        }
    }

    async fn save_whitelist(&self) {
        let path = self.data_path.join("whitelist.json");
        let whitelist = self.whitelist.read().await;
        let devices: Vec<DeviceInfo> = whitelist.values().cloned().collect();
        if let Ok(json) = serde_json::to_string_pretty(&devices) {
            std::fs::write(path, json).ok();
        }
    }

    pub async fn add_to_whitelist(&self, device: DeviceInfo) {
        self.whitelist.write().await.insert(device.id.clone(), device);
        self.save_whitelist().await;
    }

    pub async fn remove_from_whitelist(&self, device_id: &str) {
        self.whitelist.write().await.remove(device_id);
        self.save_whitelist().await;
    }

    pub async fn is_trusted(&self, device_id: &str) -> bool {
        self.whitelist.read().await.contains_key(device_id)
    }

    pub async fn get_whitelist(&self) -> Vec<DeviceInfo> {
        self.whitelist.read().await.values().cloned().collect()
    }
}
