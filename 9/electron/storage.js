const fs = require('fs');
const fsp = fs.promises;
const path = require('path');
const crypto = require('crypto');
const { app } = require('electron');

const ALGORITHM = 'aes-256-gcm';
const IV_LENGTH = 12;
const TAG_LENGTH = 16;
const SALT_LENGTH = 32;
const KEY_ITERATIONS = 100000;
const KEY_LENGTH = 32;

function getDeviceKey() {
  const machineId = app.getPath('userData');
  return crypto.createHash('sha256').update(machineId + app.getName()).digest();
}

function deriveKey(salt, secret) {
  return crypto.pbkdf2Sync(secret, salt, KEY_ITERATIONS, KEY_LENGTH, 'sha512');
}

function encrypt(text, secret) {
  const iv = crypto.randomBytes(IV_LENGTH);
  const salt = crypto.randomBytes(SALT_LENGTH);
  const key = deriveKey(salt, secret);
  const cipher = crypto.createCipheriv(ALGORITHM, key, iv);
  const encrypted = Buffer.concat([cipher.update(text, 'utf-8'), cipher.final()]);
  const tag = cipher.getAuthTag();
  return Buffer.concat([salt, iv, tag, encrypted]).toString('base64');
}

function decrypt(encryptedData, secret) {
  try {
    const buffer = Buffer.from(encryptedData, 'base64');
    const salt = buffer.slice(0, SALT_LENGTH);
    const iv = buffer.slice(SALT_LENGTH, SALT_LENGTH + IV_LENGTH);
    const tag = buffer.slice(SALT_LENGTH + IV_LENGTH, SALT_LENGTH + IV_LENGTH + TAG_LENGTH);
    const encrypted = buffer.slice(SALT_LENGTH + IV_LENGTH + TAG_LENGTH);
    const key = deriveKey(salt, secret);
    const decipher = crypto.createDecipheriv(ALGORITHM, key, iv);
    decipher.setAuthTag(tag);
    const decrypted = Buffer.concat([decipher.update(encrypted), decipher.final()]);
    return decrypted.toString('utf-8');
  } catch (error) {
    console.error('Decryption failed:', error);
    return null;
  }
}

class Storage {
  constructor() {
    const userDataPath = app.getPath('userData');
    this.snippetsPath = path.join(userDataPath, 'snippets.json.enc');
    this.settingsPath = path.join(userDataPath, 'settings.json');
    this._writeTimeout = null;
    this._pendingSnippets = null;
    this._secret = getDeviceKey();
    this._encryptionEnabled = true;
  }

  async loadSettings() {
    try {
      await fsp.access(this.settingsPath);
      const data = await fsp.readFile(this.settingsPath, 'utf-8');
      return JSON.parse(data);
    } catch (error) {
      if (error.code !== 'ENOENT') {
        console.error('Error loading settings:', error);
      }
      return { encryptionEnabled: true, githubToken: null, gistId: null };
    }
  }

  async saveSettings(settings) {
    try {
      const data = JSON.stringify(settings, null, 2);
      await fsp.writeFile(this.settingsPath, data, 'utf-8');
      this._encryptionEnabled = settings.encryptionEnabled ?? true;
      return true;
    } catch (error) {
      console.error('Error saving settings:', error);
      return false;
    }
  }

  async load() {
    try {
      await fsp.access(this.snippetsPath);
      const data = await fsp.readFile(this.snippetsPath, 'utf-8');
      let jsonStr = data;
      if (this._encryptionEnabled) {
        const decrypted = decrypt(data, this._secret);
        if (decrypted === null) {
          console.warn('Decryption failed, attempting raw read');
          try {
            return JSON.parse(data);
          } catch {
            return [];
          }
        }
        jsonStr = decrypted;
      }
      return JSON.parse(jsonStr);
    } catch (error) {
      if (error.code !== 'ENOENT') {
        console.error('Error loading snippets:', error);
      }
      return [];
    }
  }

  _serializeData(snippets) {
    return new Promise((resolve, reject) => {
      setImmediate(() => {
        try {
          let data = JSON.stringify(snippets, null, 2);
          if (this._encryptionEnabled) {
            data = encrypt(data, this._secret);
          }
          resolve(data);
        } catch (error) {
          reject(error);
        }
      });
    });
  }

  async _flushWrite() {
    if (!this._pendingSnippets) return;
    const snippets = this._pendingSnippets;
    this._pendingSnippets = null;

    try {
      const data = await this._serializeData(snippets);
      await fsp.writeFile(this.snippetsPath, data, 'utf-8');
    } catch (error) {
      console.error('Error saving snippets:', error);
    }
  }

  save(snippets) {
    this._pendingSnippets = snippets;

    if (this._writeTimeout) {
      clearTimeout(this._writeTimeout);
    }

    return new Promise((resolve) => {
      this._writeTimeout = setTimeout(async () => {
        await this._flushWrite();
        resolve(true);
      }, 200);
    });
  }

  async saveNow(snippets) {
    if (this._writeTimeout) {
      clearTimeout(this._writeTimeout);
      this._writeTimeout = null;
    }
    this._pendingSnippets = snippets;
    await this._flushWrite();
    return true;
  }

  getSnippetsPath() {
    return this.snippetsPath;
  }

  getSettingsPath() {
    return this.settingsPath;
  }

  setEncryptionEnabled(enabled) {
    this._encryptionEnabled = enabled;
  }

  isEncryptionEnabled() {
    return this._encryptionEnabled;
  }
}

module.exports = Storage;
