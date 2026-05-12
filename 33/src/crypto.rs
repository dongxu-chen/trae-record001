use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Nonce,
};
use argon2::{Algorithm, Argon2, Params, Version};
use base64::{engine::general_purpose, Engine as _};
use rand_core::{OsRng, RngCore};

#[derive(Debug)]
pub enum CryptoError {
    EncryptionFailed,
    DecryptionFailed,
    KeyDerivationFailed,
    InvalidInput,
    RngError,
}

#[derive(Clone)]
pub struct Crypto {
    master_key: [u8; 32],
}

impl Crypto {
    pub fn new(master_password: &str, salt: &[u8]) -> Result<Self, CryptoError> {
        let params = Params::new(65536, 3, 1, Some(32))
            .map_err(|_| CryptoError::KeyDerivationFailed)?;
        
        let argon2 = Argon2::new(Algorithm::Argon2id, Version::V0x13, params);
        
        let mut key = [0u8; 32];
        argon2
            .hash_password_into(master_password.as_bytes(), salt, &mut key)
            .map_err(|_| CryptoError::KeyDerivationFailed)?;
        
        Ok(Crypto { master_key: key })
    }
    
    pub fn generate_salt() -> Result<[u8; 16], CryptoError> {
        let mut salt = [0u8; 16];
        OsRng
            .try_fill_bytes(&mut salt)
            .map_err(|_| CryptoError::RngError)?;
        Ok(salt)
    }
    
    fn generate_nonce() -> Result<[u8; 12], CryptoError> {
        let mut nonce = [0u8; 12];
        OsRng
            .try_fill_bytes(&mut nonce)
            .map_err(|_| CryptoError::RngError)?;
        Ok(nonce)
    }
    
    pub fn encrypt(&self, plaintext: &str) -> Result<String, CryptoError> {
        let cipher = Aes256Gcm::new_from_slice(&self.master_key)
            .map_err(|_| CryptoError::EncryptionFailed)?;
        
        let nonce = Self::generate_nonce()?;
        let nonce_bytes = Nonce::from_slice(&nonce);
        
        let ciphertext = cipher
            .encrypt(nonce_bytes, plaintext.as_bytes())
            .map_err(|_| CryptoError::EncryptionFailed)?;
        
        let mut result = Vec::with_capacity(12 + ciphertext.len());
        result.extend_from_slice(&nonce);
        result.extend_from_slice(&ciphertext);
        
        Ok(general_purpose::STANDARD.encode(&result))
    }
    
    pub fn decrypt(&self, ciphertext: &str) -> Result<String, CryptoError> {
        let cipher = Aes256Gcm::new_from_slice(&self.master_key)
            .map_err(|_| CryptoError::DecryptionFailed)?;
        
        let decoded = general_purpose::STANDARD
            .decode(ciphertext)
            .map_err(|_| CryptoError::InvalidInput)?;
        
        if decoded.len() < 12 {
            return Err(CryptoError::InvalidInput);
        }
        
        let (nonce_bytes, ciphertext_bytes) = decoded.split_at(12);
        let nonce = Nonce::from_slice(nonce_bytes);
        
        let plaintext = cipher
            .decrypt(nonce, ciphertext_bytes)
            .map_err(|_| CryptoError::DecryptionFailed)?;
        
        String::from_utf8(plaintext).map_err(|_| CryptoError::DecryptionFailed)
    }
}

