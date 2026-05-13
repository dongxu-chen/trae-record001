module DB where

import qualified Data.Pool as Pool
import Database.SQLite.Simple
import System.Directory

type ConnectionPool = Pool.Pool Connection

createConnection :: IO Connection
createConnection = do
  conn <- open "notes.db"
  execute_ conn "PRAGMA journal_mode = WAL"
  execute_ conn "PRAGMA synchronous = NORMAL"
  execute_ conn "PRAGMA foreign_keys = ON"
  execute_ conn "PRAGMA busy_timeout = 30000"
  return conn

initDB :: IO ConnectionPool
initDB = do
  dbExists <- doesFileExist "notes.db"
  pool <- Pool.createPool createConnection close 1 60 10
  Pool.withResource pool $ \conn ->
    if dbExists
      then return ()
      else do
        execute_ conn "CREATE TABLE notes (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
        execute_ conn "CREATE TABLE share_links (id INTEGER PRIMARY KEY AUTOINCREMENT, note_id INTEGER NOT NULL, short_code TEXT NOT NULL UNIQUE, expires_at TEXT, created_at TEXT NOT NULL, FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE)"
        execute_ conn "CREATE TABLE api_keys (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT NOT NULL UNIQUE, name TEXT NOT NULL, created_at TEXT NOT NULL, last_used_at TEXT)"
        execute_ conn "CREATE INDEX idx_share_links_short_code ON share_links(short_code)"
        execute_ conn "CREATE INDEX idx_share_links_note_id ON share_links(note_id)"
        execute_ conn "CREATE INDEX idx_api_keys_key ON api_keys(key)"
        execute_ conn "CREATE VIRTUAL TABLE notes_fts USING fts5(title, content, content_rowid, tokenize='trigram')"
        execute_ conn "INSERT INTO notes_fts(rowid, title, content) SELECT id, title, content FROM notes"
  return pool
