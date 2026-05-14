use crate::storage::CheckResult;
use chrono::Utc;
use reqwest::Client;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::Semaphore;

#[derive(Debug, Clone)]
pub struct CheckerConfig {
    pub timeout_seconds: u64,
    pub max_concurrent_requests: usize,
    pub connect_timeout_seconds: u64,
}

impl Default for CheckerConfig {
    fn default() -> Self {
        CheckerConfig {
            timeout_seconds: 10,
            max_concurrent_requests: 32,
            connect_timeout_seconds: 5,
        }
    }
}

pub struct HealthChecker {
    client: Client,
    config: CheckerConfig,
    semaphore: Arc<Semaphore>,
}

impl HealthChecker {
    pub fn new(timeout_seconds: u64) -> Result<Self, Box<dyn std::error::Error>> {
        let config = CheckerConfig {
            timeout_seconds,
            ..Default::default()
        };
        Self::with_config(config)
    }

    pub fn with_config(config: CheckerConfig) -> Result<Self, Box<dyn std::error::Error>> {
        let client = Client::builder()
            .timeout(Duration::from_secs(config.timeout_seconds))
            .connect_timeout(Duration::from_secs(config.connect_timeout_seconds))
            .pool_idle_timeout(Duration::from_secs(30))
            .build()?;

        let semaphore = Arc::new(Semaphore::new(config.max_concurrent_requests));

        Ok(HealthChecker {
            client,
            config,
            semaphore,
        })
    }

    pub async fn check_url(&self, url: &str) -> CheckResult {
        let permit = match self.semaphore.clone().acquire_owned().await {
            Ok(p) => p,
            Err(e) => {
                return CheckResult {
                    id: None,
                    url: url.to_string(),
                    status_code: None,
                    response_time_ms: 0,
                    is_healthy: false,
                    error_message: Some(format!("Failed to acquire semaphore: {}", e)),
                    checked_at: Utc::now(),
                };
            }
        };

        let start = Instant::now();
        let checked_at = Utc::now();

        let result = self.client.get(url).send().await;

        let response_time_ms = start.elapsed().as_millis() as i64;

        drop(permit);

        match result {
            Ok(response) => {
                let status_code = response.status().as_u16() as i32;
                let is_healthy = Self::is_status_healthy(status_code);

                CheckResult {
                    id: None,
                    url: url.to_string(),
                    status_code: Some(status_code),
                    response_time_ms,
                    is_healthy,
                    error_message: None,
                    checked_at,
                }
            }
            Err(e) => CheckResult {
                id: None,
                url: url.to_string(),
                status_code: None,
                response_time_ms,
                is_healthy: false,
                error_message: Some(e.to_string()),
                checked_at,
            },
        }
    }

    fn is_status_healthy(status_code: i32) -> bool {
        (200..=299).contains(&status_code) || (300..=399).contains(&status_code)
    }

    pub async fn check_url_post(
        &self,
        url: &str,
        method: &str,
        body: Option<serde_json::Value>,
    ) -> CheckResult {
        let permit = match self.semaphore.clone().acquire_owned().await {
            Ok(p) => p,
            Err(e) => {
                return CheckResult {
                    id: None,
                    url: url.to_string(),
                    status_code: None,
                    response_time_ms: 0,
                    is_healthy: false,
                    error_message: Some(format!("Failed to acquire semaphore: {}", e)),
                    checked_at: Utc::now(),
                };
            }
        };

        let start = Instant::now();
        let checked_at = Utc::now();

        let request_builder = match method.to_uppercase().as_str() {
            "POST" => {
                let mut req = self.client.post(url);
                if let Some(b) = body {
                    req.json(&b)
                } else {
                    req
                }
            }
            "PUT" => {
                let mut req = self.client.put(url);
                if let Some(b) = body {
                    req.json(&b)
                } else {
                    req
                }
            }
            "DELETE" => self.client.delete(url),
            "HEAD" => self.client.head(url),
            _ => self.client.get(url),
        };

        let result = request_builder.send().await;
        let response_time_ms = start.elapsed().as_millis() as i64;

        drop(permit);

        match result {
            Ok(response) => {
                let status_code = response.status().as_u16() as i32;
                let is_healthy = Self::is_status_healthy(status_code);

                CheckResult {
                    id: None,
                    url: url.to_string(),
                    status_code: Some(status_code),
                    response_time_ms,
                    is_healthy,
                    error_message: None,
                    checked_at,
                }
            }
            Err(e) => CheckResult {
                id: None,
                url: url.to_string(),
                status_code: None,
                response_time_ms,
                is_healthy: false,
                error_message: Some(e.to_string()),
                checked_at,
            },
        }
    }

    pub fn get_timeout(&self) -> u64 {
        self.config.timeout_seconds
    }

    pub fn get_config(&self) -> &CheckerConfig {
        &self.config
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_status_healthy() {
        assert!(HealthChecker::is_status_healthy(200));
        assert!(HealthChecker::is_status_healthy(299));
        assert!(HealthChecker::is_status_healthy(301));
        assert!(HealthChecker::is_status_healthy(399));
        assert!(!HealthChecker::is_status_healthy(400));
        assert!(!HealthChecker::is_status_healthy(500));
    }
}
