use crate::models::{DeviceInfo, DeviceSource, PairingQrData};
use crate::crypto::CryptoManager;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio::time::{sleep, Duration};
use local_ip_address::list_afinet_netifas;
use qrcode::QrCode;
use qrcode::render::unicode;
use serde_json;
use chrono::Utc;

#[derive(Clone)]
pub struct DiscoveryService {
    devices: Arc<RwLock<HashMap<String, DeviceInfo>>>,
    local_device: Arc<RwLock<Option<DeviceInfo>>>,
    crypto: CryptoManager,
    running: Arc<RwLock<bool>>,
    port: u16,
}

impl DiscoveryService {
    pub fn new() -> Self {
        Self {
            devices: Arc::new(RwLock::new(HashMap::new())),
            local_device: Arc::new(RwLock::new(None)),
            crypto: CryptoManager::new(),
            running: Arc::new(RwLock::new(false)),
            port: 38765,
        }
    }

    pub async fn start(&self) -> Result<(), Box<dyn std::error::Error>> {
        *self.running.write().await = true;
        
        self.crypto.generate_keypair().await?;
        self.init_local_device().await;
        
        let service = self.clone();
        tokio::spawn(async move {
            while *service.running.read().await {
                service.broadcast_mdns().await.ok();
                service.listen_mdns().await.ok();
                sleep(Duration::from_secs(5)).await;
            }
        });
        
        Ok(())
    }

    pub async fn stop(&self) {
        *self.running.write().await = false;
    }

    async fn init_local_device(&self) {
        let ips = self.get_local_ips().await;
        let public_key = self.crypto.get_public_key_der().await.ok();
        
        let device = DeviceInfo {
            id: uuid::Uuid::new_v4().to_string(),
            name: format!("{}-{}", get_hostname(), std::env::consts::OS),
            platform: std::env::consts::OS.to_string(),
            address: ips.first().cloned().unwrap_or_else(|| "127.0.0.1".to_string()),
            port: self.port,
            public_key: public_key.map(hex::encode),
            source: DeviceSource::Manual,
            trusted: true,
            last_seen: Utc::now(),
        };
        
        *self.local_device.write().await = Some(device);
    }

    async fn get_local_ips(&self) -> Vec<String> {
        let mut ips = Vec::new();
        if let Ok(interfaces) = list_afinet_netifas() {
            for (_, ip) in interfaces {
                if !ip.is_loopback() {
                    ips.push(ip.to_string());
                }
            }
        }
        if ips.is_empty() {
            ips.push("127.0.0.1".to_string());
        }
        ips
    }

    async fn broadcast_mdns(&self) -> Result<(), Box<dyn std::error::Error>> {
        Ok(())
    }

    async fn listen_mdns(&self) -> Result<(), Box<dyn std::error::Error>> {
        Ok(())
    }

    pub async fn scan_ip_range(&self, start_ip: &str, end_ip: &str) -> Result<Vec<DeviceInfo>, String> {
        let mut devices = Vec::new();
        let start = parse_ip(start_ip).ok_or_else(|| "无效的起始IP".to_string())?;
        let end = parse_ip(end_ip).ok_or_else(|| "无效的结束IP".to_string())?;
        
        let mut handles = Vec::new();
        
        for i in start..=end {
            let ip = format!("{}.{}.{}.{}", 
                (i >> 24) & 0xFF,
                (i >> 16) & 0xFF,
                (i >> 8) & 0xFF,
                i & 0xFF
            );
            
            let port = self.port;
            handles.push(tokio::spawn(async move {
                if let Ok(device) = Self::probe_device(&ip, port).await {
                    Some(device)
                } else {
                    None
                }
            }));
        }
        
        for handle in handles {
            if let Ok(Some(device)) = handle.await {
                self.devices.write().await.insert(device.id.clone(), device.clone());
                devices.push(device);
            }
        }
        
        Ok(devices)
    }

    async fn probe_device(ip: &str, port: u16) -> Result<DeviceInfo, ()> {
        let addr = format!("{}:{}", ip, port);
        match tokio::time::timeout(Duration::from_millis(500), tokio::net::TcpStream::connect(&addr)).await {
            Ok(Ok(_)) => {
                if let Ok(resp) = reqwest::get(format!("http://{}/api/device", addr)).await {
                    if let Ok(device) = resp.json::<DeviceInfo>().await {
                        return Ok(device);
                    }
                }
                Err(())
            }
            _ => Err(()),
        }
    }

    pub async fn get_devices(&self) -> Vec<DeviceInfo> {
        self.devices.read().await.values().cloned().collect()
    }

    pub async fn get_local_device(&self) -> DeviceInfo {
        self.local_device.read().await.as_ref().unwrap().clone()
    }

    pub async fn generate_pairing_qrcode(&self) -> Result<String, String> {
        let local_device = self.get_local_device().await;
        let ips = self.get_local_ips().await;
        
        let qr_data = PairingQrData {
            device_id: local_device.id,
            device_name: local_device.name,
            public_key: local_device.public_key.unwrap_or_default(),
            ips,
            port: self.port,
            timestamp: Utc::now().timestamp(),
        };
        
        let json = serde_json::to_string(&qr_data).map_err(|e| e.to_string())?;
        
        let code = QrCode::new(json.as_bytes()).map_err(|e| format!("{:?}", e))?;
        let image = code.render::<unicode::Dense1x2>()
            .dark_color(unicode::Dense1x2::Light)
            .light_color(unicode::Dense1x2::Dark)
            .build();
        
        Ok(image)
    }

    pub async fn parse_pairing_qrcode(&self, data: &str) -> Result<DeviceInfo, String> {
        let qr_data: PairingQrData = serde_json::from_str(data).map_err(|e| e.to_string())?;
        
        let device = DeviceInfo {
            id: qr_data.device_id,
            name: qr_data.device_name,
            platform: "unknown".to_string(),
            address: qr_data.ips.first().cloned().unwrap_or_default(),
            port: qr_data.port,
            public_key: Some(qr_data.public_key),
            source: DeviceSource::QrCode,
            trusted: false,
            last_seen: Utc::now(),
        };
        
        self.devices.write().await.insert(device.id.clone(), device.clone());
        
        Ok(device)
    }
}

impl Default for DiscoveryService {
    fn default() -> Self {
        Self::new()
    }
}

fn parse_ip(ip: &str) -> Option<u32> {
    let parts: Vec<&str> = ip.split('.').collect();
    if parts.len() != 4 {
        return None;
    }
    
    let mut result = 0u32;
    for part in parts {
        if let Ok(n) = part.parse::<u8>() {
            result = (result << 8) | n as u32;
        } else {
            return None;
        }
    }
    Some(result)
}

fn get_hostname() -> String {
    hostname::get()
        .ok()
        .and_then(|h| h.into_string().ok())
        .unwrap_or_else(|| "unknown".to_string())
}
