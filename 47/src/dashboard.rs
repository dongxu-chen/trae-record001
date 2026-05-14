use crate::storage::Storage;
use metrics::{counter, gauge, histogram, Counter, Gauge, Histogram};
use metrics_exporter_prometheus::{Matcher, PrometheusBuilder, PrometheusHandle};
use std::sync::Arc;
use std::time::Duration;

#[derive(Debug, Clone)]
pub struct MetricsRegistry {
    check_total: Counter,
    check_success: Counter,
    check_failure: Counter,
    check_duration: Histogram,
    active_urls: Gauge,
    unhealthy_urls: Gauge,
    avg_response_time: Gauge,
    alerts_active: Gauge,
    http_client: reqwest::Client,
}

impl MetricsRegistry {
    pub fn new() -> Self {
        let _ = PrometheusBuilder::new()
            .set_buckets_for_metric(
                Matcher::Full("url_check_duration_seconds".to_string()),
                &[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
            )
            .unwrap()
            .install_recorder();

        let http_client = reqwest::Client::builder()
            .timeout(Duration::from_secs(5))
            .build()
            .unwrap_or_default();

        MetricsRegistry {
            check_total: counter!("url_check_total", "Total number of URL checks"),
            check_success: counter!("url_check_success_total", "Total successful checks"),
            check_failure: counter!("url_check_failure_total", "Total failed checks"),
            check_duration: histogram!("url_check_duration_seconds", "URL check duration"),
            active_urls: gauge!("url_active_count", "Number of active monitored URLs"),
            unhealthy_urls: gauge!("url_unhealthy_count", "Number of unhealthy URLs"),
            avg_response_time: gauge!("url_avg_response_time_ms", "Average response time in ms"),
            alerts_active: gauge!("url_alerts_active_count", "Number of active alerts"),
            http_client,
        }
    }

    pub fn record_check(&self, success: bool, response_time_ms: i64, url: &str) {
        let labels = &[("url", url.to_string())];

        self.check_total.increment(1);
        self.check_duration.record(response_time_ms as f64 / 1000.0);

        if success {
            self.check_success.increment(1);
        } else {
            self.check_failure.increment(1);
        }
    }

    pub fn set_active_urls(&self, count: usize) {
        self.active_urls.set(count as f64);
    }

    pub fn set_unhealthy_urls(&self, count: usize) {
        self.unhealthy_urls.set(count as f64);
    }

    pub fn set_avg_response_time(&self, avg_ms: f64) {
        self.avg_response_time.set(avg_ms);
    }

    pub fn set_active_alerts(&self, count: usize) {
        self.alerts_active.set(count as f64);
    }

    pub fn get_prometheus_handle() -> Option<PrometheusHandle> {
        PrometheusBuilder::new()
            .set_buckets_for_metric(
                Matcher::Full("url_check_duration_seconds".to_string()),
                &[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
            )
            .ok()
            .and_then(|builder| builder.install_recorder().ok())
    }
}

impl Default for MetricsRegistry {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct DashboardSummary {
    pub total_urls: usize,
    pub healthy_urls: usize,
    pub unhealthy_urls: usize,
    pub active_alerts: usize,
    pub avg_response_time_ms: f64,
    pub uptime_24h_percentage: f64,
    pub uptime_7d_percentage: f64,
    pub checks_last_hour: i64,
    pub checks_last_24h: i64,
}

pub struct DashboardService {
    storage: Arc<Storage>,
    metrics: Arc<MetricsRegistry>,
}

impl DashboardService {
    pub fn new(storage: Arc<Storage>, metrics: Arc<MetricsRegistry>) -> Self {
        DashboardService { storage, metrics }
    }

    pub async fn get_summary(&self) -> Result<DashboardSummary, Box<dyn std::error::Error>> {
        let targets = self.storage.get_active_url_targets().await?;
        let total_urls = targets.len();

        let now = chrono::Utc::now();
        let one_hour_ago = now - chrono::Duration::hours(1);
        let one_day_ago = now - chrono::Duration::hours(24);
        let seven_days_ago = now - chrono::Duration::days(7);

        let mut healthy_count = 0;
        let mut total_response_time: i64 = 0;
        let mut checks_count: i64 = 0;
        let mut checks_24h: i64 = 0;
        let mut healthy_24h: i64 = 0;
        let mut checks_7d: i64 = 0;
        let mut healthy_7d: i64 = 0;

        for target in &targets {
            let target_id = target.id.unwrap_or(0);

            let recent_results = self
                .storage
                .get_latest_results_by_target(target_id, 10)
                .await
                .unwrap_or_default();

            if let Some(latest) = recent_results.first() {
                if latest.is_healthy {
                    healthy_count += 1;
                }
            }

            for result in &recent_results {
                total_response_time += result.response_time_ms;
                checks_count += 1;
            }

            let results_24h = self
                .storage
                .get_results_for_sla(target_id, one_day_ago, now)
                .await
                .unwrap_or_default();
            checks_24h += results_24h.len() as i64;
            healthy_24h += results_24h.iter().filter(|r| r.is_healthy).count() as i64;

            let results_7d = self
                .storage
                .get_results_for_sla(target_id, seven_days_ago, now)
                .await
                .unwrap_or_default();
            checks_7d += results_7d.len() as i64;
            healthy_7d += results_7d.iter().filter(|r| r.is_healthy).count() as i64;
        }

        let unhealthy_urls = total_urls.saturating_sub(healthy_count);
        let avg_response_time_ms = if checks_count > 0 {
            total_response_time as f64 / checks_count as f64
        } else {
            0.0
        };

        let uptime_24h_percentage = if checks_24h > 0 {
            (healthy_24h as f64 / checks_24h as f64) * 100.0
        } else {
            100.0
        };

        let uptime_7d_percentage = if checks_7d > 0 {
            (healthy_7d as f64 / checks_7d as f64) * 100.0
        } else {
            100.0
        };

        let active_alerts = self
            .storage
            .get_alerts(Some(false), 1000)
            .await
            .unwrap_or_default()
            .len();

        self.metrics.set_active_urls(total_urls);
        self.metrics.set_unhealthy_urls(unhealthy_urls);
        self.metrics.set_avg_response_time(avg_response_time_ms);
        self.metrics.set_active_alerts(active_alerts);

        let mut checks_last_hour = 0;
        for target in &targets {
            let target_id = target.id.unwrap_or(0);
            let results = self
                .storage
                .get_results_for_sla(target_id, one_hour_ago, now)
                .await
                .unwrap_or_default();
            checks_last_hour += results.len() as i64;
        }

        Ok(DashboardSummary {
            total_urls,
            healthy_urls: healthy_count,
            unhealthy_urls,
            active_alerts,
            avg_response_time_ms,
            uptime_24h_percentage,
            uptime_7d_percentage,
            checks_last_hour,
            checks_last_24h: checks_24h,
        })
    }

    pub fn get_metrics(&self) -> &Arc<MetricsRegistry> {
        &self.metrics
    }
}

use serde::Serialize;

pub fn render_prometheus_metrics() -> String {
    if let Some(handle) = MetricsRegistry::get_prometheus_handle() {
        handle.render()
    } else {
        String::from("# Prometheus metrics not initialized\n")
    }
}
