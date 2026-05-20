use aes_gcm::{
    aead::{Aead, KeyInit, OsRng},
    Aes256Gcm, Nonce,
};
use p256::{
    ecdh::EphemeralSecret,
    PublicKey,
};
use sha2::{Sha256, Digest};
use rand::RngCore;
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Clone)]
pub struct CryptoManager {
    private_key: Arc<RwLock<Option<EphemeralSecret>>>,
    public_key: Arc<RwLock<Option<PublicKey>>>,
    shared_secrets: Arc<RwLock<std::collections::HashMap<String, Vec<u8>>>>,
}

impl CryptoManager {
    pub fn new() -> Self {
        Self {
            private_key: Arc::new(RwLock::new(None)),
            public_key: Arc::new(RwLock::new(None)),
            shared_secrets: Arc::new(RwLock::new(std::collections::HashMap::new())),
        }
    }

    pub async fn generate_keypair(&self) -> Result<(), CryptoError> {
        let secret = EphemeralSecret::random(&mut OsRng);
        let public = secret.public_key();
        
        *self.private_key.write().await = Some(secret);
        *self.public_key.write().await = Some(public);
        
        Ok(())
    }

    pub async fn get_public_key_der(&self) -> Result<Vec<u8>, CryptoError> {
        let public = self.public_key.read().await;
        if let Some(key) = public.as_ref() {
            Ok(key.to_sec1_bytes().to_vec())
        } else {
            Err(CryptoError::KeyNotGenerated)
        }
    }

    pub async fn derive_shared_secret(&self, device_id: &str, peer_public_der: &[u8]) -> Result<(), CryptoError> {
        let peer_public = PublicKey::from_sec1_bytes(peer_public_der)
            .map_err(|_| CryptoError::InvalidPublicKey)?;
        
        let private = self.private_key.read().await;
        let secret = private.as_ref().ok_or(CryptoError::KeyNotGenerated)?;
        
        let shared_secret = secret.diffie_hellman(&peer_public);
        let mut hasher = Sha256::new();
        hasher.update(shared_secret.as_bytes());
        let key = hasher.finalize().to_vec();
        
        self.shared_secrets.write().await.insert(device_id.to_string(), key);
        
        Ok(())
    }

    pub async fn encrypt(&self, device_id: &str, data: &[u8]) -> Result<EncryptedData, CryptoError> {
        let secrets = self.shared_secrets.read().await;
        let key = secrets.get(device_id).ok_or(CryptoError::NoSharedSecret)?;
        
        let cipher = Aes256Gcm::new(key.into());
        
        let mut nonce_bytes = vec![0u8; 12];
        OsRng.fill_bytes(&mut nonce_bytes);
        let nonce = Nonce::from_slice(&nonce_bytes);
        
        let ciphertext = cipher.encrypt(nonce, data)
            .map_err(|_| CryptoError::EncryptionFailed)?;
        
        let tag = ciphertext[ciphertext.len() - 16..].to_vec();
        let encrypted_data = ciphertext[..ciphertext.len() - 16].to_vec();
        
        Ok(EncryptedData {
            data: encrypted_data,
            nonce: nonce_bytes,
            tag,
        })
    }

    pub async fn decrypt(&self, device_id: &str, encrypted: &EncryptedData) -> Result<Vec<u8>, CryptoError> {
        let secrets = self.shared_secrets.read().await;
        let key = secrets.get(device_id).ok_or(CryptoError::NoSharedSecret)?;
        
        let cipher = Aes256Gcm::new(key.into());
        
        let nonce = Nonce::from_slice(&encrypted.nonce);
        
        let mut ciphertext_with_tag = encrypted.data.clone();
        ciphertext_with_tag.extend_from_slice(&encrypted.tag);
        
        let plaintext = cipher.decrypt(nonce, &ciphertext_with_tag[..])
            .map_err(|_| CryptoError::DecryptionFailed)?;
        
        Ok(plaintext)
    }

    pub async fn has_shared_secret(&self, device_id: &str) -> bool {
        self.shared_secrets.read().await.contains_key(device_id)
    }
}

impl Default for CryptoManager {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Debug, Clone)]
pub struct EncryptedData {
    pub data: Vec<u8>,
    pub nonce: Vec<u8>,
    pub tag: Vec<u8>,
}

#[derive(Debug, thiserror::Error)]
pub enum CryptoError {
    #[error("密钥未生成")]
    KeyNotGenerated,
    #[error("无效的公钥")]
    InvalidPublicKey,
    #[error("没有共享密钥")]
    NoSharedSecret,
    #[error("加密失败")]
    EncryptionFailed,
    #[error("解密失败")]
    DecryptionFailed,
}

pub fn md5_hash(data: &[u8]) -> String {
    use md5::{Md5};
    let mut hasher = Md5::new();
    hasher.update(data);
    let result = hasher.finalize();
    hex::encode(result)
}
