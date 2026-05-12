use base64::{engine::general_purpose, Engine as _};
use chrono::{DateTime, Utc};
use rusqlite::{params, Connection, OptionalExtension};
use std::path::PathBuf;
use std::sync::Arc;
use std::sync::Mutex;

#[derive(Debug)]
pub enum DbError {
    DatabaseError(String),
    PathNotFound,
    EntryNotFound,
}

impl From<rusqlite::Error> for DbError {
    fn from(err: rusqlite::Error) -> Self {
        DbError::DatabaseError(err.to_string())
    }
}

impl From<std::sync::PoisonError<std::sync::MutexGuard<'_, Connection>>> for DbError {
    fn from(err: std::sync::PoisonError<std::sync::MutexGuard<'_, Connection>>) -> Self {
        DbError::DatabaseError(err.to_string())
    }
}

#[derive(Clone)]
pub struct PasswordEntry {
    pub id: i64,
    pub service: String,
    pub username: String,
    pub encrypted_password: String,
    pub notes: Option<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Clone)]
pub struct Database {
    conn: Arc<Mutex<Connection>>,
}

impl Database {
    pub fn new(db_path: PathBuf) -> Result<Self, DbError> {
        if let Some(parent) = db_path.parent() {
            std::fs::create_dir_all(parent).map_err(|_| DbError::PathNotFound)?;
        }

        let conn = Connection::open(&db_path)?;

        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )",
            [],
        )?;

        conn.execute(
            "CREATE TABLE IF NOT EXISTS passwords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT NOT NULL,
                username TEXT NOT NULL,
                encrypted_password TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )",
            [],
        )?;

        Ok(Database {
            conn: Arc::new(Mutex::new(conn)),
        })
    }

    fn with_conn<F, T>(&self, f: F) -> Result<T, DbError>
    where
        F: FnOnce(&Connection) -> Result<T, DbError>,
    {
        let guard = self.conn.lock()?;
        f(&guard)
    }

    pub fn get_setting(&self, key: &str) -> Result<Option<String>, DbError> {
        self.with_conn(|conn| {
            Ok(conn
                .query_row(
                    "SELECT value FROM settings WHERE key = ?1",
                    params![key],
                    |row| row.get(0),
                )
                .optional()?)
        })
    }

    pub fn set_setting(&self, key: &str, value: &str) -> Result<(), DbError> {
        self.with_conn(|conn| {
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?1, ?2)
                 ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                params![key, value],
            )?;
            Ok(())
        })
    }

    pub fn get_salt(&self) -> Result<Option<[u8; 16]>, DbError> {
        let salt_str = self.get_setting("salt")?;
        match salt_str {
            Some(s) => {
                let bytes = general_purpose::STANDARD
                    .decode(&s)
                    .map_err(|_| DbError::PathNotFound)?;
                if bytes.len() != 16 {
                    return Err(DbError::PathNotFound);
                }
                let mut salt = [0u8; 16];
                salt.copy_from_slice(&bytes);
                Ok(Some(salt))
            }
            None => Ok(None),
        }
    }

    pub fn set_salt(&self, salt: &[u8; 16]) -> Result<(), DbError> {
        let salt_str = general_purpose::STANDARD.encode(salt);
        self.set_setting("salt", &salt_str)
    }

    pub fn add_password(
        &self,
        service: &str,
        username: &str,
        encrypted_password: &str,
        notes: Option<&str>,
    ) -> Result<i64, DbError> {
        self.with_conn(|conn| {
            let now = Utc::now().to_rfc3339();
            conn.execute(
                "INSERT INTO passwords (service, username, encrypted_password, notes, created_at, updated_at)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?5)",
                params![service, username, encrypted_password, notes, now],
            )?;
            Ok(conn.last_insert_rowid())
        })
    }

    pub fn update_password(
        &self,
        id: i64,
        service: &str,
        username: &str,
        encrypted_password: &str,
        notes: Option<&str>,
    ) -> Result<(), DbError> {
        let affected = self.with_conn(|conn| {
            let now = Utc::now().to_rfc3339();
            Ok(conn.execute(
                "UPDATE passwords
                 SET service = ?1, username = ?2, encrypted_password = ?3, notes = ?4, updated_at = ?5
                 WHERE id = ?6",
                params![service, username, encrypted_password, notes, now, id],
            )?)
        })?;
        if affected == 0 {
            return Err(DbError::EntryNotFound);
        }
        Ok(())
    }

    pub fn delete_password(&self, id: i64) -> Result<(), DbError> {
        let affected = self.with_conn(|conn| {
            Ok(conn.execute(
                "DELETE FROM passwords WHERE id = ?1",
                params![id],
            )?)
        })?;
        if affected == 0 {
            return Err(DbError::EntryNotFound);
        }
        Ok(())
    }

    pub fn get_all_passwords(&self) -> Result<Vec<PasswordEntry>, DbError> {
        self.with_conn(|conn| {
            let mut stmt = conn.prepare(
                "SELECT id, service, username, encrypted_password, notes, created_at, updated_at
                 FROM passwords ORDER BY service ASC",
            )?;

            let entries = stmt.query_map([], |row| {
                let created_at: String = row.get(5)?;
                let updated_at: String = row.get(6)?;

                Ok(PasswordEntry {
                    id: row.get(0)?,
                    service: row.get(1)?,
                    username: row.get(2)?,
                    encrypted_password: row.get(3)?,
                    notes: row.get(4)?,
                    created_at: DateTime::parse_from_rfc3339(&created_at)
                        .unwrap_or_else(|_| Utc::now().into())
                        .with_timezone(&Utc),
                    updated_at: DateTime::parse_from_rfc3339(&updated_at)
                        .unwrap_or_else(|_| Utc::now().into())
                        .with_timezone(&Utc),
                })
            })?;

            let mut result = Vec::new();
            for entry in entries {
                result.push(entry.map_err(DbError::from)?);
            }

            Ok(result)
        })
    }

    pub fn search_passwords(&self, query: &str) -> Result<Vec<PasswordEntry>, DbError> {
        self.with_conn(|conn| {
            let search_pattern = format!("%{}%", query);
            let mut stmt = conn.prepare(
                "SELECT id, service, username, encrypted_password, notes, created_at, updated_at
                 FROM passwords
                 WHERE service LIKE ?1 OR username LIKE ?1 OR notes LIKE ?1
                 ORDER BY service ASC",
            )?;

            let entries = stmt.query_map(params![search_pattern], |row| {
                let created_at: String = row.get(5)?;
                let updated_at: String = row.get(6)?;

                Ok(PasswordEntry {
                    id: row.get(0)?,
                    service: row.get(1)?,
                    username: row.get(2)?,
                    encrypted_password: row.get(3)?,
                    notes: row.get(4)?,
                    created_at: DateTime::parse_from_rfc3339(&created_at)
                        .unwrap_or_else(|_| Utc::now().into())
                        .with_timezone(&Utc),
                    updated_at: DateTime::parse_from_rfc3339(&updated_at)
                        .unwrap_or_else(|_| Utc::now().into())
                        .with_timezone(&Utc),
                })
            })?;

            let mut result = Vec::new();
            for entry in entries {
                result.push(entry.map_err(DbError::from)?);
            }

            Ok(result)
        })
    }

    pub fn update_encrypted_password(&self, id: i64, new_encrypted: &str) -> Result<(), DbError> {
        let affected = self.with_conn(|conn| {
            let now = Utc::now().to_rfc3339();
            Ok(conn.execute(
                "UPDATE passwords SET encrypted_password = ?1, updated_at = ?2 WHERE id = ?3",
                params![new_encrypted, now, id],
            )?)
        })?;
        if affected == 0 {
            return Err(DbError::EntryNotFound);
        }
        Ok(())
    }
}

