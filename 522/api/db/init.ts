import Database from 'better-sqlite3'
import path from 'path'
import fs from 'fs'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const dataDir = path.join(__dirname, '../data')
fs.mkdirSync(dataDir, { recursive: true })

const db = new Database(path.join(dataDir, 'filters.db'))

db.exec(`
  CREATE TABLE IF NOT EXISTS presets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    filterType TEXT NOT NULL,
    intensity REAL NOT NULL DEFAULT 0.5,
    customParams TEXT DEFAULT '{}',
    createdAt TEXT NOT NULL DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS custom_filters (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    filename TEXT NOT NULL,
    fragmentShader TEXT NOT NULL,
    uniforms TEXT DEFAULT '[]',
    createdAt TEXT NOT NULL DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS marketplace_presets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    author TEXT NOT NULL,
    filterType TEXT NOT NULL,
    intensity REAL NOT NULL DEFAULT 0.5,
    customParams TEXT DEFAULT '{}',
    thumbnailData TEXT,
    tags TEXT DEFAULT '[]',
    downloads INTEGER NOT NULL DEFAULT 0,
    rating REAL NOT NULL DEFAULT 0,
    ratingCount INTEGER NOT NULL DEFAULT 0,
    createdAt TEXT NOT NULL DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS marketplace_ratings (
    id TEXT PRIMARY KEY,
    presetId TEXT NOT NULL,
    userId TEXT NOT NULL,
    rating INTEGER NOT NULL,
    createdAt TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(presetId, userId)
  );

  CREATE INDEX IF NOT EXISTS idx_marketplace_tags ON marketplace_presets(tags);
  CREATE INDEX IF NOT EXISTS idx_marketplace_downloads ON marketplace_presets(downloads);
  CREATE INDEX IF NOT EXISTS idx_marketplace_rating ON marketplace_presets(rating);
`)

export default db
