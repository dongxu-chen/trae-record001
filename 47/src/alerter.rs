use crate::storage::{AlertRecord, Storage};
use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::{mpsc, RwLock};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertConfig {
    pub dingtalk_webhook_url: Option<String>,
    pub dingtalk_secret: Option<String>,
    pub consecutive_failures_threshold: u32,
    pub response_time_threshold_ms: i64,
    pub sla_warning_threshold: f64,
    pub sla_critical_threshold: f64,
    pub alert_cooldown_seconds: i64,
}

impl Default for AlertConfig {
    fn default() -> Self {
        AlertConfig {
            dingtalk_webhook_url: std::env::var("DINGTALK_WEBHOOK_URL").ok(),
            dingtalk_secret: std::env::var("DINGTALK_SECRET").ok(),
            consecutive_failures_threshold: 3,
            response_time_threshold_ms: 3000,
            sla_warning_threshold: 99.0,
            sla_critical_threshold: 95.0,
            alert_cooldown_seconds: 300,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum AlertType {
    ConsecutiveFailure,
    SlowResponse,
    SLAWarning,
    SLACritical,
    Recovery,
}

impl AlertType {
    pub fn as_str(&self) -> &'static str {
        match self {
            AlertType::ConsecutiveFailure => "consecutive_failure",
            AlertType::SlowResponse => "slow_response",
            AlertType::SLAWarning => "sla_warning",
            AlertType::SLACritical => "sla_critical",
            AlertType::Recovery => "recovery",
        }
    }

    pub fn from_str(s: &str) -> Self {
        match s {
            "consecutive_failure" => AlertType::ConsecutiveFailure,
            "slow_response" => AlertType::SlowResponse,
            "sla_warning" => AlertType::SLAWarning,
            "sla_critical" => AlertType::SLACritical,
            "recovery" => AlertType::Recovery,
            _ => AlertType::ConsecutiveFailure,
        }
    }

    pub fn severity(&self) -> &'static str {
        match self {
            AlertType::ConsecutiveFailure => "critical",
            AlertType::SlowResponse => "warning",
            AlertType::SLAWarning => "warning",
            AlertType::SLACritical => "critical",
            AlertType::Recovery => "info",
        }
    }
}

#[derive(Debug, Clone)]
pub struct AlertContext {
    pub url_target_id: i32,
    pub url: String,
    pub consecutive_failures: u32,
    pub last_response_time_ms: Option<i64>,
    pub sla_percentage: Option<f64>,
}

pub struct AlertMessage {
    pub alert_type: AlertType,
    pub url: String,
    pub message: String,
    pub severity: String,
}

struct AlertState {
    last_alert_times: HashMap<i32, HashMap<String, chrono::DateTime<chrono::Utc>>>,
    consecutive_failures: HashMap<i32, u32>,
    is_alerts_open: HashMap<i32, HashMap<String, bool>>,
}

pub struct AlerterService {
    storage: Arc<Storage>,
    config: AlertConfig,
    state: Arc<RwLock<AlertState>>,
    http_client: reqwest::Client,
    shutdown_tx: Option<mpsc::Sender<()>>,
}

impl AlerterService {
    pub fn new(storage: Arc<Storage>, config: Option<AlertConfig>) -> Self {
        let config = config.unwrap_or_default();
        let http_client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(10))
            .build()
            .unwrap_or_default();

        AlerterService {
            storage,
            config,
            state: Arc::new(RwLock::new(AlertState {
                last_alert_times: HashMap::new(),
                consecutive_failures: HashMap::new(),
                is_alerts_open: HashMap::new(),
            })),
            http_client,
            shutdown_tx: None,
        }
    }

    pub async fn check_and_alert(
        &self,
        context: &AlertContext,
    ) -> Result<Vec<AlertMessage>, Box<dyn std::error::Error>> {
        let mut messages = Vec::new();
        let now = Utc::now();

        let consecutive_failure_count = self
            .update_consecutive_failures(context.url_target_id, context.last_response_time_ms.is_some() && context.consecutive_failures == 0)
            .await;

        if consecutive_failure_count >= self.config.consecutive_failures_threshold {
            if self
                .should_alert(context.url_target_id, &AlertType::ConsecutiveFailure.as_str(), now)
                .await
            {
                let msg = format!(
                    "⚠️ 网站不可用告警\nURL: {}\n连续失败次数: {}\n阈值: {}\n时间: {}",
                    context.url,
                    consecutive_failure_count,
                    self.config.consecutive_failures_threshold,
                    now.format("%Y-%m-%d %H:%M:%S UTC")
                );

                messages.push(AlertMessage {
                    alert_type: AlertType::ConsecutiveFailure,
                    url: context.url.clone(),
                    message: msg.clone(),
                    severity: AlertType::ConsecutiveFailure.severity().to_string(),
                });

                self.create_and_send_alert(
                    context.url_target_id,
                    &context.url,
                    AlertType::ConsecutiveFailure,
                    &msg,
                    now,
                )
                .await?;
            }
        } else if consecutive_failure_count == 0 {
            if self
                .is_alert_open(context.url_target_id, &AlertType::ConsecutiveFailure.as_str())
                .await
            {
                let recovery_msg = format!(
                    "✅ 网站恢复可用\nURL: {}\n时间: {}",
                    context.url,
                    now.format("%Y-%m-%d %H:%M:%S UTC")
                );

                messages.push(AlertMessage {
                    alert_type: AlertType::Recovery,
                    url: context.url.clone(),
                    message: recovery_msg.clone(),
                    severity: AlertType::Recovery.severity().to_string(),
                });

                self.resolve_and_send_alert(
                    context.url_target_id,
                    &AlertType::ConsecutiveFailure.as_str(),
                    &recovery_msg,
                    now,
                )
                .await?;
            }
        }

        if let Some(response_time) = context.last_response_time_ms {
            if response_time > self.config.response_time_threshold_ms {
                if self
                    .should_alert(context.url_target_id, &AlertType::SlowResponse.as_str(), now)
                    .await
                {
                    let msg = format!(
                        "⚠️ 响应时间过慢告警\nURL: {}\n当前响应: {}ms\n阈值: {}ms\n时间: {}",
                        context.url,
                        response_time,
                        self.config.response_time_threshold_ms,
                        now.format("%Y-%m-%d %H:%M:%S UTC")
                    );

                    messages.push(AlertMessage {
                        alert_type: AlertType::SlowResponse,
                        url: context.url.clone(),
                        message: msg.clone(),
                        severity: AlertType::SlowResponse.severity().to_string(),
                    });

                    self.create_and_send_alert(
                        context.url_target_id,
                        &context.url,
                        AlertType::SlowResponse,
                        &msg,
                        now,
                    )
                    .await?;
                }
            }
        }

        if let Some(sla) = context.sla_percentage {
            if sla < self.config.sla_critical_threshold {
                if self
                    .should_alert(context.url_target_id, &AlertType::SLACritical.as_str(), now)
                    .await
                {
                    let msg = format!(
                        "🚨 SLA 严重告警\nURL: {}\n当前 SLA: {:.2}%\n阈值: {}%\n时间: {}",
                        context.url,
                        sla,
                        self.config.sla_critical_threshold,
                        now.format("%Y-%m-%d %H:%M:%S UTC")
                    );

                    messages.push(AlertMessage {
                        alert_type: AlertType::SLACritical,
                        url: context.url.clone(),
                        message: msg.clone(),
                        severity: AlertType::SLACritical.severity().to_string(),
                    });

                    self.create_and_send_alert(
                        context.url_target_id,
                        &context.url,
                        AlertType::SLACritical,
                        &msg,
                        now,
                    )
                    .await?;
                }
            } else if sla < self.config.sla_warning_threshold {
                if self
                    .should_alert(context.url_target_id, &AlertType::SLAWarning.as_str(), now)
                    .await
                {
                    let msg = format!(
                        "⚠️ SLA 警告\nURL: {}\n当前 SLA: {:.2}%\n阈值: {}%\n时间: {}",
                        context.url,
                        sla,
                        self.config.sla_warning_threshold,
                        now.format("%Y-%m-%d %H:%M:%S UTC")
                    );

                    messages.push(AlertMessage {
                        alert_type: AlertType::SLAWarning,
                        url: context.url.clone(),
                        message: msg.clone(),
                        severity: AlertType::SLAWarning.severity().to_string(),
                    });

                    self.create_and_send_alert(
                        context.url_target_id,
                        &context.url,
                        AlertType::SLAWarning,
                        &msg,
                        now,
                    )
                    .await?;
                }
            }
        }

        Ok(messages)
    }

    async fn update_consecutive_failures(&self, url_target_id: i32, is_success: bool) -> u32 {
        let mut state = self.state.write().await;
        if is_success {
            state.consecutive_failures.insert(url_target_id, 0);
            0
        } else {
            let current = state
                .consecutive_failures
                .get(&url_target_id)
                .copied()
                .unwrap_or(0);
            let new_count = current + 1;
            state
                .consecutive_failures
                .insert(url_target_id, new_count);
            new_count
        }
    }

    async fn should_alert(
        &self,
        url_target_id: i32,
        alert_type: &str,
        now: chrono::DateTime<chrono::Utc>,
    ) -> bool {
        let state = self.state.read().await;

        if let Some(url_alerts) = state.is_alerts_open.get(&url_target_id) {
            if url_alerts.get(alert_type).copied().unwrap_or(false) {
                return false;
            }
        }

        if let Some(url_times) = state.last_alert_times.get(&url_target_id) {
            if let Some(last_time) = url_times.get(alert_type) {
                let cooldown = chrono::Duration::seconds(self.config.alert_cooldown_seconds);
                if now.signed_duration_since(*last_time) < cooldown {
                    return false;
                }
            }
        }

        true
    }

    async fn is_alert_open(&self, url_target_id: i32, alert_type: &str) -> bool {
        let state = self.state.read().await;
        state
            .is_alerts_open
            .get(&url_target_id)
            .and_then(|m| m.get(alert_type))
            .copied()
            .unwrap_or(false)
    }

    async fn create_and_send_alert(
        &self,
        url_target_id: i32,
        url: &str,
        alert_type: AlertType,
        message: &str,
        now: chrono::DateTime<chrono::Utc>,
    ) -> Result<(), Box<dyn std::error::Error>> {
        {
            let mut state = self.state.write().await;
            state
                .last_alert_times
                .entry(url_target_id)
                .or_default()
                .insert(alert_type.as_str().to_string(), now);
            state
                .is_alerts_open
                .entry(url_target_id)
                .or_default()
                .insert(alert_type.as_str().to_string(), true);
        }

        let alert = AlertRecord {
            id: None,
            url_target_id,
            url: url.to_string(),
            alert_type: alert_type.as_str().to_string(),
            severity: alert_type.severity().to_string(),
            message: message.to_string(),
            resolved: false,
            created_at: now,
            resolved_at: None,
        };

        if let Err(e) = self.storage.create_alert(&alert).await {
            eprintln!("Failed to create alert record: {}", e);
        }

        self.send_dingtalk_message(message).await;

        Ok(())
    }

    async fn resolve_and_send_alert(
        &self,
        url_target_id: i32,
        alert_type: &str,
        message: &str,
        now: chrono::DateTime<chrono::Utc>,
    ) -> Result<(), Box<dyn std::error::Error>> {
        {
            let mut state = self.state.write().await;
            if let Some(url_alerts) = state.is_alerts_open.get_mut(&url_target_id) {
                url_alerts.insert(alert_type.to_string(), false);
            }
        }

        let active_alerts = self
            .storage
            .get_active_alerts_for_url(url_target_id, alert_type)
            .await?;

        for alert in active_alerts {
            if let Some(alert_id) = alert.id {
                if let Err(e) = self.storage.resolve_alert(alert_id).await {
                    eprintln!("Failed to resolve alert {}: {}", alert_id, e);
                }
            }
        }

        self.send_dingtalk_message(message).await;

        Ok(())
    }

    async fn send_dingtalk_message(&self, message: &str) {
        let webhook_url = match &self.config.dingtalk_webhook_url {
            Some(url) if !url.is_empty() => url,
            _ => {
                println!("[Alerter] DingTalk webhook not configured, skipping: {}", message);
                return;
            }
        };

        let mut final_url = webhook_url.clone();

        if let Some(secret) = &self.config.dingtalk_secret {
            if !secret.is_empty() {
                let timestamp = std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_millis()
                    .to_string();

                let sign_str = format!("{}\n{}", timestamp, secret);
                if let Ok(signature) = calculate_hmac_signature(&sign_str, secret) {
                    final_url = format!(
                        "{}&timestamp={}&sign={}",
                        webhook_url, timestamp, signature
                    );
                }
            }
        }

        let payload = serde_json::json!({
            "msgtype": "text",
            "text": {
                "content": message
            }
        });

        match self
            .http_client
            .post(&final_url)
            .header("Content-Type", "application/json")
            .json(&payload)
            .send()
            .await
        {
            Ok(response) => {
                if !response.status().is_success() {
                    eprintln!(
                        "Failed to send DingTalk message: HTTP {}",
                        response.status()
                    );
                }
            }
            Err(e) => {
                eprintln!("Failed to send DingTalk message: {}", e);
            }
        }
    }

    pub fn get_config(&self) -> &AlertConfig {
        &self.config
    }

    pub fn with_http_client(mut self, client: reqwest::Client) -> Self {
        self.http_client = client;
        self
    }
}

fn calculate_hmac_signature(message: &str, secret: &str) -> Result<String, Box<dyn std::error::Error>> {
    use hmac::{Hmac, Mac};
    use sha2::Sha256;

    type HmacSha256 = Hmac<Sha256>;
    let mut mac = HmacSha256::new_from_slice(secret.as_bytes())?;
    mac.update(message.as_bytes());
    let result = mac.finalize();
    let code_bytes = result.into_bytes();

    use base64::{engine::general_purpose, Engine as _};
    let sign = general_purpose::STANDARD.encode(code_bytes);
    let sign_urlencoded = urlencoding::encode(&sign).into_owned();

    Ok(sign_urlencoded)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_alert_type() {
        assert_eq!(AlertType::ConsecutiveFailure.as_str(), "consecutive_failure");
        assert_eq!(AlertType::SlowResponse.as_str(), "slow_response");
        assert_eq!(AlertType::ConsecutiveFailure.severity(), "critical");
        assert_eq!(AlertType::SlowResponse.severity(), "warning");
    }
}
