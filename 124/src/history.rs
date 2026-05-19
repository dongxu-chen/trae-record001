use crate::models::{HistoryItem, TransferDirection, ContentType};
use std::sync::Arc;
use tokio::sync::RwLock;
use dirs::home_dir;
use chrono::{DateTime, Utc};
use serde_json;

#[derive(Clone)]
pub struct HistoryManager {
    history: Arc<RwLock<Vec<HistoryItem>>>,
    data_path: std::path::PathBuf,
    limit: usize,
}

impl HistoryManager {
    pub async fn new() -> Self {
        let data_path = home_dir()
            .unwrap_or_else(|| std::path::PathBuf::from("."))
            .join(".clipboard-sync");
        
        std::fs::create_dir_all(&data_path).ok();
        
        let mut manager = Self {
            history: Arc::new(RwLock::new(Vec::new())),
            data_path,
            limit: 200,
        };
        
        manager.load().await;
        manager
    }

    async fn load(&mut self) {
        let path = self.data_path.join("history.json");
        if let Ok(data) = std::fs::read_to_string(path) {
            if let Ok(mut items) = serde_json::from_str::<Vec<HistoryItem>>(&data) {
                items.truncate(self.limit);
                *self.history.write().await = items;
            }
        }
    }

    async fn save(&self) {
        let path = self.data_path.join("history.json");
        let history = self.history.read().await;
        if let Ok(json) = serde_json::to_string_pretty(&*history) {
            std::fs::write(path, json).ok();
        }
    }

    pub async fn add(&self, item: HistoryItem) {
        let mut history = self.history.write().await;
        history.insert(0, item);
        history.truncate(self.limit);
        drop(history);
        self.save().await;
    }

    pub async fn get_all(&self) -> Vec<HistoryItem> {
        self.history.read().await.clone()
    }

    pub async fn search(
        &self,
        keyword: Option<&str>,
        item_type: Option<&str>,
        start_date: Option<&str>,
        end_date: Option<&str>,
    ) -> Vec<HistoryItem> {
        let history = self.history.read().await;
        
        history.iter()
            .filter(|item| {
                if let Some(kw) = keyword {
                    if !item.content_preview.to_lowercase().contains(&kw.to_lowercase())
                        && !item.peer_device_name.to_lowercase().contains(&kw.to_lowercase()) {
                        return false;
                    }
                }
                
                if let Some(t) = item_type {
                    let matches = match t {
                        "text" => matches!(item.content_type, ContentType::Text),
                        "image" => matches!(item.content_type, ContentType::Image),
                        "file" => matches!(item.content_type, ContentType::File),
                        _ => true,
                    };
                    if !matches {
                        return false;
                    }
                }
                
                if let Some(start) = start_date {
                    if let Ok(start_dt) = chrono::DateTime::parse_from_rfc3339(start) {
                        if item.timestamp < start_dt.with_timezone(&Utc) {
                            return false;
                        }
                    }
                }
                
                if let Some(end) = end_date {
                    if let Ok(end_dt) = chrono::DateTime::parse_from_rfc3339(end) {
                        let end_utc = end_dt.with_timezone(&Utc) + chrono::Duration::days(1);
                        if item.timestamp > end_utc {
                            return false;
                        }
                    }
                }
                
                true
            })
            .cloned()
            .collect()
    }

    pub async fn clear(&self) {
        self.history.write().await.clear();
        self.save().await;
    }
}
