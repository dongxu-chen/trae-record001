use crate::models::{DeviceInfo, ChunkData, TransferRequest};
use crate::crypto::CryptoManager;
use warp::Filter;
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Clone)]
pub struct HttpServer {
    crypto: CryptoManager,
    port: u16,
    running: Arc<RwLock<bool>>,
    pending_requests: Arc<RwLock<std::collections::HashMap<String, TransferRequest>>>,
}

impl HttpServer {
    pub fn new() -> Self {
        Self {
            crypto: CryptoManager::new(),
            port: 38765,
            running: Arc::new(RwLock::new(false)),
            pending_requests: Arc::new(RwLock::new(std::collections::HashMap::new())),
        }
    }

    pub async fn start(&self) -> Result<(), Box<dyn std::error::Error>> {
        *self.running.write().await = true;
        
        let crypto = self.crypto.clone();
        let pending = self.pending_requests.clone();
        
        let get_device = warp::path!("api" / "device")
            .and(warp::get())
            .map(|| {
                let device = DeviceInfo {
                    id: uuid::Uuid::new_v4().to_string(),
                    name: format!("{}-{}", get_hostname(), std::env::consts::OS),
                    platform: std::env::consts::OS.to_string(),
                    address: "127.0.0.1".to_string(),
                    port: 38765,
                    public_key: None,
                    source: crate::models::DeviceSource::Manual,
                    trusted: true,
                    last_seen: chrono::Utc::now(),
                };
                warp::reply::json(&device)
            });
        
        let receive_chunk = warp::path!("api" / "transfer" / "chunk")
            .and(warp::post())
            .and(warp::body::json())
            .map(move |chunk: ChunkData| {
                warp::reply::json(&serde_json::json!({ "status": "ok" }))
            });
        
        let transfer_request = warp::path!("api" / "transfer" / "request")
            .and(warp::post())
            .and(warp::body::json())
            .map(move |request: TransferRequest| {
                warp::reply::json(&serde_json::json!({ "status": "pending" }))
            });
        
        let routes = get_device.or(receive_chunk).or(transfer_request);
        
        let server = warp::serve(routes).run(([0, 0, 0, 0], self.port));
        tokio::spawn(server);
        
        Ok(())
    }

    pub async fn stop(&self) {
        *self.running.write().await = false;
    }
}

impl Default for HttpServer {
    fn default() -> Self {
        Self::new()
    }
}

fn get_hostname() -> String {
    hostname::get()
        .ok()
        .and_then(|h| h.into_string().ok())
        .unwrap_or_else(|| "unknown".to_string())
}
