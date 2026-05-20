use crate::models::{
    ClipboardContent, ContentType, ChunkData, TransferRequest, 
    TransferProgress, TransferStatus, TransferDirection, HistoryItem
};
use crate::crypto::{CryptoManager, md5_hash, EncryptedData};
use crate::history::HistoryManager;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use chrono::Utc;

const CHUNK_SIZE: usize = 1024 * 1024;

#[derive(Clone)]
pub struct TransferManager {
    crypto: CryptoManager,
    history: HistoryManager,
    pending_requests: Arc<RwLock<HashMap<String, TransferRequest>>>,
    progress: Arc<RwLock<HashMap<String, TransferProgress>>>,
    incoming_chunks: Arc<RwLock<HashMap<String, Vec<ChunkData>>>>,
}

impl TransferManager {
    pub fn new() -> Self {
        Self {
            crypto: CryptoManager::new(),
            history: HistoryManager::new(),
            pending_requests: Arc::new(RwLock::new(HashMap::new())),
            progress: Arc::new(RwLock::new(HashMap::new())),
            incoming_chunks: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub async fn send_content(&self, device_id: &str, content: ClipboardContent) -> Result<(), String> {
        let transfer_id = uuid::Uuid::new_v4().to_string();
        
        self.progress.write().await.insert(transfer_id.clone(), TransferProgress {
            transfer_id: transfer_id.clone(),
            current: 0,
            total: content.data.len() as u64,
            percentage: 0.0,
            status: TransferStatus::Pending,
        });
        
        let chunks = self.split_into_chunks(&transfer_id, &content.data).await;
        
        if self.crypto.has_shared_secret(device_id).await {
            for mut chunk in chunks {
                let encrypted = self.crypto.encrypt(device_id, &chunk.data).await
                    .map_err(|e| format!("加密失败: {:?}", e))?;
                chunk.data = encrypted.data;
                chunk.encrypted = true;
                chunk.nonce = Some(encrypted.nonce);
                chunk.tag = Some(encrypted.tag);
                
                self.send_chunk(device_id, &chunk).await?;
            }
        } else {
            for chunk in chunks {
                self.send_chunk(device_id, &chunk).await?;
            }
        }
        
        self.history.add(HistoryItem {
            id: uuid::Uuid::new_v4().to_string(),
            timestamp: Utc::now(),
            direction: TransferDirection::Send,
            content_type: content.content_type,
            content_preview: content.text_preview.unwrap_or_else(|| "已发送".to_string()),
            peer_device_id: device_id.to_string(),
            peer_device_name: "未知设备".to_string(),
            encrypted: self.crypto.has_shared_secret(device_id).await,
        }).await;
        
        Ok(())
    }

    pub async fn send_file(&self, device_id: &str, file_path: &str) -> Result<(), String> {
        let data = tokio::fs::read(file_path).await
            .map_err(|e| e.to_string())?;
        
        let file_name = std::path::Path::new(file_path)
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("unknown")
            .to_string();
        
        let content = ClipboardContent {
            content_type: ContentType::File,
            data,
            text_preview: Some(file_name.clone()),
            file_name: Some(file_name),
            file_size: None,
        };
        
        self.send_content(device_id, content).await
    }

    async fn split_into_chunks(&self, transfer_id: &str, data: &[u8]) -> Vec<ChunkData> {
        let total_chunks = (data.len() + CHUNK_SIZE - 1) / CHUNK_SIZE;
        let mut chunks = Vec::new();
        
        for i in 0..total_chunks {
            let start = i * CHUNK_SIZE;
            let end = std::cmp::min(start + CHUNK_SIZE, data.len());
            let chunk_data = data[start..end].to_vec();
            let md5 = md5_hash(&chunk_data);
            
            chunks.push(ChunkData {
                transfer_id: transfer_id.to_string(),
                chunk_index: i as u32,
                total_chunks: total_chunks as u32,
                data: chunk_data,
                md5,
                encrypted: false,
                nonce: None,
                tag: None,
            });
        }
        
        chunks
    }

    async fn send_chunk(&self, _device_id: &str, _chunk: &ChunkData) -> Result<(), String> {
        Ok(())
    }

    pub async fn respond_request(&self, request_id: &str, accepted: bool) -> Result<(), String> {
        let mut requests = self.pending_requests.write().await;
        
        if accepted {
            if let Some(progress) = self.progress.write().await.get_mut(request_id) {
                progress.status = TransferStatus::Transferring;
            }
        } else {
            if let Some(progress) = self.progress.write().await.get_mut(request_id) {
                progress.status = TransferStatus::Rejected;
            }
            requests.remove(request_id);
        }
        
        Ok(())
    }

    pub async fn get_progress(&self, transfer_id: &str) -> Result<TransferProgress, String> {
        self.progress.read().await
            .get(transfer_id)
            .cloned()
            .ok_or_else(|| "传输不存在".to_string())
    }
}

impl Default for TransferManager {
    fn default() -> Self {
        Self::new()
    }
}
