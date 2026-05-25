import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dbPath = path.join(__dirname, '../../data/qrcode.db');
const db = new Database(dbPath);

db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

const initTables = () => {
  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      email TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      name TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS qr_codes (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      name TEXT,
      type TEXT NOT NULL,
      content TEXT NOT NULL,
      style_config TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS dynamic_codes (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      short_code TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      original_url TEXT NOT NULL,
      type TEXT NOT NULL,
      style_config TEXT,
      scan_count INTEGER DEFAULT 0,
      is_active BOOLEAN DEFAULT 1,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS scan_logs (
      id TEXT PRIMARY KEY,
      dynamic_code_id TEXT NOT NULL,
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
      ip_address TEXT,
      user_agent TEXT,
      country TEXT,
      region TEXT,
      device_type TEXT,
      FOREIGN KEY (dynamic_code_id) REFERENCES dynamic_codes(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_dynamic_short_code ON dynamic_codes(short_code);
    CREATE INDEX IF NOT EXISTS idx_scan_log_code_id ON scan_logs(dynamic_code_id);
    CREATE INDEX IF NOT EXISTS idx_scan_log_timestamp ON scan_logs(timestamp);
    CREATE INDEX IF NOT EXISTS idx_qr_codes_user_id ON qr_codes(user_id);
  `);
};

initTables();

export default db;
