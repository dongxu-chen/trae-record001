use crate::crypto::Crypto;
use crate::db::{Database, PasswordEntry};
use base64::{engine::general_purpose, Engine as _};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::thread;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncConfig {
    pub enabled: bool,
    pub sync_type: SyncType,
    pub remote_url: Option<String>,
    pub local_path: Option<String>,
    pub api_key: Option<String>,
    pub auto_sync: bool,
    pub sync_interval_secs: u64,
}

impl Default for SyncConfig {
    fn default() -> Self {
        SyncConfig {
            enabled: false,
            sync_type: SyncType::LocalFile,
            remote_url: None,
            local_path: None,
            api_key: None,
            auto_sync: false,
            sync_interval_secs: 300,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SyncType {
    LocalFile,
    WebDav,
    CustomHttp,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncEntry {
    pub id: i64,
    pub service: String,
    pub username: String,
    pub encrypted_password: String,
    pub notes: Option<String>,
    pub created_at: String,
    pub updated_at: String,
    pub deleted: bool,
    pub sync_version: u64,
}

impl From<PasswordEntry> for SyncEntry {
    fn from(entry: PasswordEntry) -> Self {
        SyncEntry {
            id: entry.id,
            service: entry.service,
            username: entry.username,
            encrypted_password: entry.encrypted_password,
            notes: entry.notes,
            created_at: entry.created_at.to_rfc3339(),
            updated_at: entry.updated_at.to_rfc3339(),
            deleted: false,
            sync_version: 0,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncPayload {
    pub version: u32,
    pub device_id: String,
    pub timestamp: String,
    pub entries: Vec<SyncEntry>,
    pub checksum: String,
}

#[derive(Debug, Clone)]
pub enum SyncEvent {
    SyncStarted,
    SyncCompleted {
        pushed: usize,
        pulled: usize,
        merged: usize,
    },
    SyncFailed {
        message: String,
    },
    ConflictDetected {
        entry_id: i64,
        local_version: u64,
        remote_version: u64,
    },
}

pub type SyncCallback = Box<dyn Fn(SyncEvent) + Send + Sync + 'static>;

pub struct SyncManager {
    config: Arc<Mutex<SyncConfig>>,
    db: Option<Arc<Database>>,
    crypto: Option<Arc<Crypto>>,
    callback: Arc<Mutex<Option<SyncCallback>>>,
    device_id: String,
    running: Arc<Mutex<bool>>,
}

impl SyncManager {
    pub fn new() -> Self {
        let device_id = uuid::Uuid::new_v4().to_string();
        SyncManager {
            config: Arc::new(Mutex::new(SyncConfig::default())),
            db: None,
            crypto: None,
            callback: Arc::new(Mutex::new(None)),
            device_id,
            running: Arc::new(Mutex::new(false)),
        }
    }

    pub fn set_config(&mut self, config: SyncConfig) {
        *self.config.lock().unwrap() = config;
    }

    pub fn get_config(&self) -> SyncConfig {
        self.config.lock().unwrap().clone()
    }

    pub fn set_db(&mut self, db: Arc<Database>) {
        self.db = Some(db);
    }

    pub fn set_crypto(&mut self, crypto: Arc<Crypto>) {
        self.crypto = Some(crypto);
    }

    pub fn set_callback<F>(&mut self, callback: F)
    where
        F: Fn(SyncEvent) + Send + Sync + 'static,
    {
        *self.callback.lock().unwrap() = Some(Box::new(callback));
    }

    pub fn sync_now(&mut self) -> Result<(), SyncError> {
        let config = self.config.lock().unwrap().clone();
        if !config.enabled {
            return Err(SyncError::SyncDisabled);
        }

        let db = self.db.clone().ok_or(SyncError::NotInitialized)?;
        let crypto = self.crypto.clone().ok_or(SyncError::NotInitialized)?;

        self.emit_event(SyncEvent::SyncStarted);

        let result = match config.sync_type {
            SyncType::LocalFile => self.sync_local_file(&config, &db, &crypto),
            SyncType::WebDav | SyncType::CustomHttp => self.sync_http(&config, &db, &crypto),
        };

        match result {
            Ok((pushed, pulled, merged)) => {
                self.emit_event(SyncEvent::SyncCompleted {
                    pushed,
                    pulled,
                    merged,
                });
                Ok(())
            }
            Err(e) => {
                self.emit_event(SyncEvent::SyncFailed {
                    message: e.to_string(),
                });
                Err(e)
            }
        }
    }

    fn sync_local_file(
        &self,
        config: &SyncConfig,
        db: &Arc<Database>,
        crypto: &Arc<Crypto>,
    ) -> Result<(usize, usize, usize), SyncError> {
        let path = config
            .local_path
            .as_ref()
            .ok_or(SyncError::ConfigMissing("local_path"))?;

        let path = PathBuf::from(path);

        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).map_err(|_| SyncError::IoError)?;
        }

        let remote_payload = if path.exists() {
            let encrypted = std::fs::read_to_string(&path).map_err(|_| SyncError::IoError)?;
            Some(self.decrypt_payload(&encrypted, crypto)?)
        } else {
            None
        };

        let local_entries = self.collect_local_entries(db)?;

        let (merged, conflicts) =
            self.merge_entries(&local_entries, &remote_payload.unwrap_or_default());

        if !conflicts.is_empty() {
            for conflict in conflicts {
                self.emit_event(SyncEvent::ConflictDetected {
                    entry_id: conflict.0,
                    local_version: conflict.1,
                    remote_version: conflict.2,
                });
            }
        }

        self.apply_merged_entries(&merged, db)?;

        let to_push = self.collect_local_entries(db)?;
        let new_payload = self.create_payload(&to_push);
        let encrypted = self.encrypt_payload(&new_payload, crypto)?;
        std::fs::write(&path, &encrypted).map_err(|_| SyncError::IoError)?;

        let pushed = to_push.len();
        let pulled = if remote_payload.is_some() {
            remote_payload.unwrap().entries.len()
        } else {
            0
        };

        Ok((pushed, pulled, merged.len()))
    }

    fn sync_http(
        &self,
        _config: &SyncConfig,
        _db: &Arc<Database>,
        _crypto: &Arc<Crypto>,
    ) -> Result<(usize, usize, usize), SyncError> {
        Ok((0, 0, 0))
    }

    fn collect_local_entries(
        &self,
        db: &Arc<Database>,
    ) -> Result<Vec<SyncEntry>, SyncError> {
        let entries = db.get_all_passwords().map_err(|_| SyncError::DbError)?;
        Ok(entries.into_iter().map(SyncEntry::from).collect())
    }

    fn merge_entries(
        &self,
        local: &[SyncEntry],
        remote: &[SyncEntry],
    ) -> (Vec<SyncEntry>, Vec<(i64, u64, u64)>) {
        let mut local_map: HashMap<i64, SyncEntry> =
            local.iter().map(|e| (e.id, e.clone())).collect();
        let mut conflicts = Vec::new();

        for remote_entry in remote {
            match local_map.get(&remote_entry.id) {
                Some(local_entry) => {
                    if remote_entry.sync_version > local_entry.sync_version {
                        if remote_entry.updated_at > local_entry.updated_at {
                            local_map.insert(remote_entry.id, remote_entry.clone());
                        } else {
                            conflicts.push((
                                remote_entry.id,
                                local_entry.sync_version,
                                remote_entry.sync_version,
                            ));
                        }
                    } else if local_entry.sync_version > remote_entry.sync_version {
                        if local_entry.updated_at > remote_entry.updated_at {
                        } else {
                            conflicts.push((
                                remote_entry.id,
                                local_entry.sync_version,
                                remote_entry.sync_version,
                            ));
                        }
                    }
                }
                None => {
                    if !remote_entry.deleted {
                        local_map.insert(remote_entry.id, remote_entry.clone());
                    }
                }
            }
        }

        (local_map.into_values().collect(), conflicts)
    }

    fn apply_merged_entries(
        &self,
        entries: &[SyncEntry],
        db: &Arc<Database>,
    ) -> Result<(), SyncError> {
        for entry in entries {
            if entry.deleted {
                let _ = db.delete_password(entry.id);
            } else {
                match db.get_all_passwords() {
                    Ok(existing) => {
                        let exists = existing.iter().any(|e| e.id == entry.id);
                        if exists {
                            let notes_opt = entry.notes.as_deref();
                            if db
                                .update_password(
                                    entry.id,
                                    &entry.service,
                                    &entry.username,
                                    &entry.encrypted_password,
                                    notes_opt,
                                )
                                .is_err()
                            {
                                let _ = db.add_password(
                                    &entry.service,
                                    &entry.username,
                                    &entry.encrypted_password,
                                    entry.notes.as_deref(),
                                );
                            }
                        } else {
                            let _ = db.add_password(
                                &entry.service,
                                &entry.username,
                                &entry.encrypted_password,
                                entry.notes.as_deref(),
                            );
                        }
                    }
                    Err(_) => return Err(SyncError::DbError),
                }
            }
        }
        Ok(())
    }

    fn create_payload(&self, entries: &[SyncEntry]) -> SyncPayload {
        let checksum = format!("{:x}", md5::compute(serde_json::to_string(entries).unwrap_or_default()));
        SyncPayload {
            version: 1,
            device_id: self.device_id.clone(),
            timestamp: Utc::now().to_rfc3339(),
            entries: entries.to_vec(),
            checksum,
        }
    }

    fn encrypt_payload(
        &self,
        payload: &SyncPayload,
        crypto: &Arc<Crypto>,
    ) -> Result<String, SyncError> {
        let json = serde_json::to_string(payload).map_err(|_| SyncError::SerializeError)?;
        let encrypted = crypto.encrypt(&json).map_err(|_| SyncError::EncryptionError)?;
        Ok(format!("v1:{}", encrypted))
    }

    fn decrypt_payload(
        &self,
        encrypted: &str,
        crypto: &Arc<Crypto>,
    ) -> Result<Vec<SyncEntry>, SyncError> {
        let parts: Vec<&str> = encrypted.splitn(2, ':').collect();
        if parts.len() != 2 {
            return Err(SyncError::InvalidFormat);
        }

        let version = parts[0];
        let data = parts[1];

        match version {
            "v1" => {
                let decrypted = crypto.decrypt(data).map_err(|_| SyncError::DecryptionError)?;
                let payload: SyncPayload =
                    serde_json::from_str(&decrypted).map_err(|_| SyncError::DeserializeError)?;
                Ok(payload.entries)
            }
            _ => Err(SyncError::UnsupportedVersion),
        }
    }

    fn emit_event(&self, event: SyncEvent) {
        if let Some(ref cb) = *self.callback.lock().unwrap() {
            cb(event);
        }
    }

    pub fn start_auto_sync(&mut self) {
        let config = self.config.lock().unwrap().clone();
        if !config.enabled || !config.auto_sync {
            return;
        }

        if *self.running.lock().unwrap() {
            return;
        }

        *self.running.lock().unwrap() = true;

        let running = self.running.clone();
        let interval = config.sync_interval_secs;

        thread::spawn(move || {
            while *running.lock().unwrap() {
                thread::sleep(std::time::Duration::from_secs(interval));
            }
        });
    }

    pub fn stop_auto_sync(&mut self) {
        *self.running.lock().unwrap() = false;
    }
}

impl Default for SyncManager {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Debug)]
pub enum SyncError {
    SyncDisabled,
    NotInitialized,
    ConfigMissing(&'static str),
    DbError,
    IoError,
    NetworkError,
    EncryptionError,
    DecryptionError,
    SerializeError,
    DeserializeError,
    InvalidFormat,
    UnsupportedVersion,
    Conflict,
}

impl std::fmt::Display for SyncError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SyncError::SyncDisabled => write!(f, "Sync is disabled"),
            SyncError::NotInitialized => write!(f, "Sync manager not initialized"),
            SyncError::ConfigMissing(key) => write!(f, "Missing config: {}", key),
            SyncError::DbError => write!(f, "Database error"),
            SyncError::IoError => write!(f, "IO error"),
            SyncError::NetworkError => write!(f, "Network error"),
            SyncError::EncryptionError => write!(f, "Encryption error"),
            SyncError::DecryptionError => write!(f, "Decryption error - wrong password?"),
            SyncError::SerializeError => write!(f, "Serialization error"),
            SyncError::DeserializeError => write!(f, "Deserialization error"),
            SyncError::InvalidFormat => write!(f, "Invalid sync file format"),
            SyncError::UnsupportedVersion => write!(f, "Unsupported sync file version"),
            SyncError::Conflict => write!(f, "Sync conflict detected"),
        }
    }
}

impl std::error::Error for SyncError {}

