use serde::{Serialize, Deserialize};
use chrono::{DateTime, Utc};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceInfo {
    pub id: String,
    pub name: String,
    pub platform: String,
    pub address: String,
    pub port: u16,
    pub public_key: Option<String>,
    pub source: DeviceSource,
    pub trusted: bool,
    pub last_seen: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DeviceSource {
    #[serde(rename = "mdns")]
    Mdns,
    #[serde(rename = "ip_scan")]
    IpScan,
    #[serde(rename = "qrcode")]
    QrCode,
    #[serde(rename = "manual")]
    Manual,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClipboardContent {
    pub content_type: ContentType,
    pub data: Vec<u8>,
    pub text_preview: Option<String>,
    pub file_name: Option<String>,
    pub file_size: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ContentType {
    #[serde(rename = "text")]
    Text,
    #[serde(rename = "image")]
    Image,
    #[serde(rename = "file")]
    File,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistoryItem {
    pub id: String,
    pub timestamp: DateTime<Utc>,
    pub direction: TransferDirection,
    pub content_type: ContentType,
    pub content_preview: String,
    pub peer_device_id: String,
    pub peer_device_name: String,
    pub encrypted: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TransferDirection {
    #[serde(rename = "send")]
    Send,
    #[serde(rename = "receive")]
    Receive,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransferRequest {
    pub request_id: String,
    pub from_device_id: String,
    pub from_device_name: String,
    pub content_type: ContentType,
    pub content_preview: String,
    pub total_size: u64,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransferProgress {
    pub transfer_id: String,
    pub current: u64,
    pub total: u64,
    pub percentage: f32,
    pub status: TransferStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TransferStatus {
    #[serde(rename = "pending")]
    Pending,
    #[serde(rename = "transferring")]
    Transferring,
    #[serde(rename = "completed")]
    Completed,
    #[serde(rename = "failed")]
    Failed,
    #[serde(rename = "rejected")]
    Rejected,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChunkData {
    pub transfer_id: String,
    pub chunk_index: u32,
    pub total_chunks: u32,
    pub data: Vec<u8>,
    pub md5: String,
    pub encrypted: bool,
    pub nonce: Option<Vec<u8>>,
    pub tag: Option<Vec<u8>>,
}

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

fn get_hostname() -> String {
    hostname::get()
        .ok()
        .and_then(|h| h.into_string().ok())
        .unwrap_or_else(|| "unknown".to_string())
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PairingQrData {
    pub device_id: String,
    pub device_name: String,
    pub public_key: String,
    pub ips: Vec<String>,
    pub port: u16,
    pub timestamp: i64,
}
