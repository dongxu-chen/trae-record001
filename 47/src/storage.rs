use chrono::{DateTime, Utc};
use deadpool_postgres::{Config, Manager, ManagerConfig, Pool, RecyclingMethod};
use serde::{Deserialize, Serialize};
use tokio_postgres::NoTls;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct CheckResult {
    pub id: Option<i32>,
    pub url: String,
    pub status_code: Option<i32>,
    pub response_time_ms: i64,
    pub is_healthy: bool,
    pub error_message: Option<String>,
    pub checked_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct UrlTarget {
    pub id: Option<i32>,
    pub url: String,
    pub interval_seconds: i32,
    pub is_active: bool,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ResponseTimeHistory {
    pub id: Option<i32>,
    pub url_target_id: i32,
    pub url: String,
    pub avg_response_time_ms: f64,
    pub min_response_time_ms: i64,
    pub max_response_time_ms: i64,
    pub sample_count: i64,
    pub healthy_count: i64,
    pub unhealthy_count: i64,
    pub window_start: DateTime<Utc>,
    pub window_end: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct AlertRecord {
    pub id: Option<i32>,
    pub url_target_id: i32,
    pub url: String,
    pub alert_type: String,
    pub severity: String,
    pub message: String,
    pub resolved: bool,
    pub created_at: DateTime<Utc>,
    pub resolved_at: Option<DateTime<Utc>>,
}

pub struct Storage {
    pool: Pool,
}

impl Storage {
    pub fn new() -> Result<Self, Box<dyn std::error::Error>> {
        let mut cfg = Config::new();
        cfg.dbname = Some(
            std::env::var("DB_NAME").unwrap_or_else(|_| "url_checker".to_string()),
        );
        cfg.user = Some(
            std::env::var("DB_USER").unwrap_or_else(|_| "postgres".to_string()),
        );
        cfg.password = Some(
            std::env::var("DB_PASSWORD").unwrap_or_else(|_| "postgres".to_string()),
        );
        cfg.host = Some(
            std::env::var("DB_HOST").unwrap_or_else(|_| "localhost".to_string()),
        );
        cfg.port = Some(
            std::env::var("DB_PORT")
                .unwrap_or_else(|_| "5432".to_string())
                .parse()
                .unwrap_or(5432),
        );
        cfg.manager = Some(ManagerConfig {
            recycling_method: RecyclingMethod::Fast,
        });

        let manager = Manager::from_config(cfg, NoTls, ManagerConfig::default());
        let pool = Pool::builder(manager).max_size(16).build()?;

        Ok(Storage { pool })
    }

    pub fn get_pool(&self) -> Pool {
        self.pool.clone()
    }

    pub async fn init_schema(&self) -> Result<(), Box<dyn std::error::Error>> {
        let client = self.pool.get().await?;

        client
            .execute(
                r#"
                CREATE TABLE IF NOT EXISTS url_targets (
                    id SERIAL PRIMARY KEY,
                    url TEXT NOT NULL UNIQUE,
                    interval_seconds INTEGER NOT NULL DEFAULT 60,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                "#,
                &[],
            )
            .await?;

        client
            .execute(
                r#"
                CREATE TABLE IF NOT EXISTS check_results (
                    id SERIAL PRIMARY KEY,
                    url_target_id INTEGER REFERENCES url_targets(id) ON DELETE CASCADE,
                    url TEXT NOT NULL,
                    status_code INTEGER,
                    response_time_ms BIGINT NOT NULL,
                    is_healthy BOOLEAN NOT NULL,
                    error_message TEXT,
                    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                "#,
                &[],
            )
            .await?;

        client
            .execute(
                r#"
                CREATE INDEX IF NOT EXISTS idx_check_results_checked_at 
                ON check_results(checked_at DESC)
                "#,
                &[],
            )
            .await?;

        client
            .execute(
                r#"
                CREATE TABLE IF NOT EXISTS response_time_history (
                    id SERIAL PRIMARY KEY,
                    url_target_id INTEGER REFERENCES url_targets(id) ON DELETE CASCADE,
                    url TEXT NOT NULL,
                    avg_response_time_ms DOUBLE PRECISION NOT NULL,
                    min_response_time_ms BIGINT NOT NULL,
                    max_response_time_ms BIGINT NOT NULL,
                    sample_count BIGINT NOT NULL,
                    healthy_count BIGINT NOT NULL DEFAULT 0,
                    unhealthy_count BIGINT NOT NULL DEFAULT 0,
                    window_start TIMESTAMPTZ NOT NULL,
                    window_end TIMESTAMPTZ NOT NULL
                )
                "#,
                &[],
            )
            .await?;

        client
            .execute(
                r#"
                CREATE INDEX IF NOT EXISTS idx_response_time_history_window
                ON response_time_history(url_target_id, window_end DESC)
                "#,
                &[],
            )
            .await?;

        client
            .execute(
                r#"
                CREATE TABLE IF NOT EXISTS alert_records (
                    id SERIAL PRIMARY KEY,
                    url_target_id INTEGER REFERENCES url_targets(id) ON DELETE CASCADE,
                    url TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'warning',
                    message TEXT NOT NULL,
                    resolved BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    resolved_at TIMESTAMPTZ
                )
                "#,
                &[],
            )
            .await?;

        client
            .execute(
                r#"
                CREATE INDEX IF NOT EXISTS idx_alert_records_url_resolved
                ON alert_records(url_target_id, resolved, created_at DESC)
                "#,
                &[],
            )
            .await?;

        Ok(())
    }

    pub async fn add_url_target(&self, url: &str, interval_seconds: i32) -> Result<UrlTarget, Box<dyn std::error::Error>> {
        let client = self.pool.get().await?;
        let row = client
            .query_one(
                r#"
                INSERT INTO url_targets (url, interval_seconds)
                VALUES ($1, $2)
                ON CONFLICT (url) DO UPDATE SET
                    interval_seconds = EXCLUDED.interval_seconds,
                    is_active = TRUE
                RETURNING id, url, interval_seconds, is_active, created_at
                "#,
                &[&url, &interval_seconds],
            )
            .await?;

        Ok(UrlTarget {
            id: Some(row.get(0)),
            url: row.get(1),
            interval_seconds: row.get(2),
            is_active: row.get(3),
            created_at: row.get(4),
        })
    }

    pub async fn get_active_url_targets(&self) -> Result<Vec<UrlTarget>, Box<dyn std::error::Error>> {
        let client = self.pool.get().await?;
        let rows = client
            .query(
                r#"
                SELECT id, url, interval_seconds, is_active, created_at
                FROM url_targets
                WHERE is_active = TRUE
                "#,
                &[],
            )
            .await?;

        Ok(rows
            .into_iter()
            .map(|row| UrlTarget {
                id: Some(row.get(0)),
                url: row.get(1),
                interval_seconds: row.get(2),
                is_active: row.get(3),
                created_at: row.get(4),
            })
            .collect())
    }

    pub async fn save_check_result(
        &self,
        url_target_id: i32,
        result: &CheckResult,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let client = self.pool.get().await?;
        client
            .execute(
                r#"
                INSERT INTO check_results 
                (url_target_id, url, status_code, response_time_ms, is_healthy, error_message, checked_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                "#,
                &[
                    &url_target_id,
                    &result.url,
                    &result.status_code,
                    &result.response_time_ms,
                    &result.is_healthy,
                    &result.error_message,
                    &result.checked_at,
                ],
            )
            .await?;

        Ok(())
    }

    pub async fn save_check_results_batch(
        &self,
        results: &[(i32, CheckResult)],
    ) -> Result<usize, Box<dyn std::error::Error>> {
        if results.is_empty() {
            return Ok(0);
        }

        let mut client = self.pool.get().await?;
        let transaction = client.transaction().await?;

        let mut saved_count = 0;
        for (url_target_id, result) in results {
            transaction
                .execute(
                    r#"
                    INSERT INTO check_results 
                    (url_target_id, url, status_code, response_time_ms, is_healthy, error_message, checked_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    "#,
                    &[
                        url_target_id,
                        &result.url,
                        &result.status_code,
                        &result.response_time_ms,
                        &result.is_healthy,
                        &result.error_message,
                        &result.checked_at,
                    ],
                )
                .await?;
            saved_count += 1;
        }

        transaction.commit().await?;
        Ok(saved_count)
    }

    pub async fn get_recent_results(
        &self,
        limit: i64,
    ) -> Result<Vec<CheckResult>, Box<dyn std::error::Error>> {
        let client = self.pool.get().await?;
        let rows = client
            .query(
                r#"
                SELECT id, url, status_code, response_time_ms, is_healthy, error_message, checked_at
                FROM check_results
                ORDER BY checked_at DESC
                LIMIT $1
                "#,
                &[&limit],
            )
            .await?;

        Ok(rows
            .into_iter()
            .map(|row| CheckResult {
                id: Some(row.get(0)),
                url: row.get(1),
                status_code: row.get(2),
                response_time_ms: row.get(3),
                is_healthy: row.get(4),
                error_message: row.get(5),
                checked_at: row.get(6),
            })
            .collect())
    }

    pub async fn get_results_by_url(
        &self,
        url: &str,
        limit: i64,
    ) -> Result<Vec<CheckResult>, Box<dyn std::error::Error>> {
        let client = self.pool.get().await?;
        let rows = client
            .query(
                r#"
                SELECT id, url, status_code, response_time_ms, is_healthy, error_message, checked_at
                FROM check_results
                WHERE url = $1
                ORDER BY checked_at DESC
                LIMIT $2
                "#,
                &[&url, &limit],
            )
            .await?;

        Ok(rows
            .into_iter()
            .map(|row| CheckResult {
                id: Some(row.get(0)),
                url: row.get(1),
                status_code: row.get(2),
                response_time_ms: row.get(3),
                is_healthy: row.get(4),
                error_message: row.get(5),
                checked_at: row.get(6),
            })
            .collect())
    }

    pub async fn delete_url_target(&self, url: &str) -> Result<(), Box<dyn std::error::Error>> {
        let client = self.pool.get().await?;
        client
            .execute("DELETE FROM url_targets WHERE url = $1", &[&url])
            .await?;
        Ok(())
    }

    pub async fn get_results_for_sla(
        &self,
        url_target_id: i32,
        from: DateTime<Utc>,
        to: DateTime<Utc>,
    ) -> Result<Vec<CheckResult>, Box<dyn std::error::Error>> {
        let client = self.pool.get().await?;
        let rows = client
            .query(
                r#"
                SELECT id, url, status_code, response_time_ms, is_healthy, error_message, checked_at
                FROM check_results
                WHERE url_target_id = $1 AND checked_at >= $2 AND checked_at <= $3
                ORDER BY checked_at ASC
                "#,
                &[&url_target_id, &from, &to],
            )
            .await?;

        Ok(rows
            .into_iter()
            .map(|row| CheckResult {
                id: Some(row.get(0)),
                url: row.get(1),
                status_code: row.get(2),
                response_time_ms: row.get(3),
                is_healthy: row.get(4),
                error_message: row.get(5),
                checked_at: row.get(6),
            })
            .collect())
    }

    pub async fn get_latest_results_by_target(
        &self,
        url_target_id: i32,
        limit: i64,
    ) -> Result<Vec<CheckResult>, Box<dyn std::error::Error>> {
        let client = self.pool.get().await?;
        let rows = client
            .query(
                r#"
                SELECT id, url, status_code, response_time_ms, is_healthy, error_message, checked_at
                FROM check_results
                WHERE url_target_id = $1
                ORDER BY checked_at DESC
                LIMIT $2
                "#,
                &[&url_target_id, &limit],
            )
            .await?;

        Ok(rows
            .into_iter()
            .map(|row| CheckResult {
                id: Some(row.get(0)),
                url: row.get(1),
                status_code: row.get(2),
                response_time_ms: row.get(3),
                is_healthy: row.get(4),
                error_message: row.get(5),
                checked_at: row.get(6),
            })
            .collect())
    }

    pub async fn save_response_time_history(
        &self,
        history: &ResponseTimeHistory,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let client = self.pool.get().await?;
        client
            .execute(
                r#"
                INSERT INTO response_time_history
                (url_target_id, url, avg_response_time_ms, min_response_time_ms, max_response_time_ms,
                 sample_count, healthy_count, unhealthy_count, window_start, window_end)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                "#,
                &[
                    &history.url_target_id,
                    &history.url,
                    &history.avg_response_time_ms,
                    &history.min_response_time_ms,
                    &history.max_response_time_ms,
                    &history.sample_count,
                    &history.healthy_count,
                    &history.unhealthy_count,
                    &history.window_start,
                    &history.window_end,
                ],
            )
            .await?;
        Ok(())
    }

    pub async fn get_response_time_history(
        &self,
        url_target_id: i32,
        limit: i64,
    ) -> Result<Vec<ResponseTimeHistory>, Box<dyn std::error::Error>> {
        let client = self.pool.get().await?;
        let rows = client
            .query(
                r#"
                SELECT id, url_target_id, url, avg_response_time_ms, min_response_time_ms, 
                       max_response_time_ms, sample_count, healthy_count, unhealthy_count, 
                       window_start, window_end
                FROM response_time_history
                WHERE url_target_id = $1
                ORDER BY window_end DESC
                LIMIT $2
                "#,
                &[&url_target_id, &limit],
            )
            .await?;

        Ok(rows
            .into_iter()
            .map(|row| ResponseTimeHistory {
                id: Some(row.get(0)),
                url_target_id: row.get(1),
                url: row.get(2),
                avg_response_time_ms: row.get(3),
                min_response_time_ms: row.get(4),
                max_response_time_ms: row.get(5),
                sample_count: row.get(6),
                healthy_count: row.get(7),
                unhealthy_count: row.get(8),
                window_start: row.get(9),
                window_end: row.get(10),
            })
            .collect())
    }

    pub async fn get_response_time_history_by_time(
        &self,
        url_target_id: i32,
        from: DateTime<Utc>,
        to: DateTime<Utc>,
    ) -> Result<Vec<ResponseTimeHistory>, Box<dyn std::error::Error>> {
        let client = self.pool.get().await?;
        let rows = client
            .query(
                r#"
                SELECT id, url_target_id, url, avg_response_time_ms, min_response_time_ms, 
                       max_response_time_ms, sample_count, healthy_count, unhealthy_count, 
                       window_start, window_end
                FROM response_time_history
                WHERE url_target_id = $1 AND window_end >= $2 AND window_start <= $3
                ORDER BY window_end ASC
                "#,
                &[&url_target_id, &from, &to],
            )
            .await?;

        Ok(rows
            .into_iter()
            .map(|row| ResponseTimeHistory {
                id: Some(row.get(0)),
                url_target_id: row.get(1),
                url: row.get(2),
                avg_response_time_ms: row.get(3),
                min_response_time_ms: row.get(4),
                max_response_time_ms: row.get(5),
                sample_count: row.get(6),
                healthy_count: row.get(7),
                unhealthy_count: row.get(8),
                window_start: row.get(9),
                window_end: row.get(10),
            })
            .collect())
    }

    pub async fn create_alert(
        &self,
        alert: &AlertRecord,
    ) -> Result<i32, Box<dyn std::error::Error>> {
        let client = self.pool.get().await?;
        let row = client
            .query_one(
                r#"
                INSERT INTO alert_records
                (url_target_id, url, alert_type, severity, message, resolved, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                "#,
                &[
                    &alert.url_target_id,
                    &alert.url,
                    &alert.alert_type,
                    &alert.severity,
                    &alert.message,
                    &alert.resolved,
                    &alert.created_at,
                ],
            )
            .await?;
        Ok(row.get(0))
    }

    pub async fn resolve_alert(
        &self,
        alert_id: i32,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let client = self.pool.get().await?;
        client
            .execute(
                r#"
                UPDATE alert_records
                SET resolved = TRUE, resolved_at = NOW()
                WHERE id = $1
                "#,
                &[&alert_id],
            )
            .await?;
        Ok(())
    }

    pub async fn get_active_alerts_for_url(
        &self,
        url_target_id: i32,
        alert_type: &str,
    ) -> Result<Vec<AlertRecord>, Box<dyn std::error::Error>> {
        let client = self.pool.get().await?;
        let rows = client
            .query(
                r#"
                SELECT id, url_target_id, url, alert_type, severity, message, resolved, created_at, resolved_at
                FROM alert_records
                WHERE url_target_id = $1 AND alert_type = $2 AND resolved = FALSE
                ORDER BY created_at DESC
                "#,
                &[&url_target_id, &alert_type],
            )
            .await?;

        Ok(rows
            .into_iter()
            .map(|row| AlertRecord {
                id: Some(row.get(0)),
                url_target_id: row.get(1),
                url: row.get(2),
                alert_type: row.get(3),
                severity: row.get(4),
                message: row.get(5),
                resolved: row.get(6),
                created_at: row.get(7),
                resolved_at: row.get(8),
            })
            .collect())
    }

    pub async fn get_alerts(
        &self,
        resolved: Option<bool>,
        limit: i64,
    ) -> Result<Vec<AlertRecord>, Box<dyn std::error::Error>> {
        let client = self.pool.get().await?;

        let rows = match resolved {
            Some(r) => {
                client
                    .query(
                        r#"
                        SELECT id, url_target_id, url, alert_type, severity, message, resolved, created_at, resolved_at
                        FROM alert_records
                        WHERE resolved = $1
                        ORDER BY created_at DESC
                        LIMIT $2
                        "#,
                        &[&r, &limit],
                    )
                    .await?
            }
            None => {
                client
                    .query(
                        r#"
                        SELECT id, url_target_id, url, alert_type, severity, message, resolved, created_at, resolved_at
                        FROM alert_records
                        ORDER BY created_at DESC
                        LIMIT $1
                        "#,
                        &[&limit],
                    )
                    .await?
            }
        };

        Ok(rows
            .into_iter()
            .map(|row| AlertRecord {
                id: Some(row.get(0)),
                url_target_id: row.get(1),
                url: row.get(2),
                alert_type: row.get(3),
                severity: row.get(4),
                message: row.get(5),
                resolved: row.get(6),
                created_at: row.get(7),
                resolved_at: row.get(8),
            })
            .collect())
    }

    pub async fn get_url_target_by_id(
        &self,
        id: i32,
    ) -> Result<Option<UrlTarget>, Box<dyn std::error::Error>> {
        let client = self.pool.get().await?;
        let rows = client
            .query(
                r#"
                SELECT id, url, interval_seconds, is_active, created_at
                FROM url_targets
                WHERE id = $1
                "#,
                &[&id],
            )
            .await?;

        Ok(rows.first().map(|row| UrlTarget {
            id: Some(row.get(0)),
            url: row.get(1),
            interval_seconds: row.get(2),
            is_active: row.get(3),
            created_at: row.get(4),
        }))
    }
}
