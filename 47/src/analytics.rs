use crate::storage::{CheckResult, ResponseTimeHistory, Storage};
use chrono::{DateTime, Duration, Utc};
use serde::{Deserialize, Serialize};
use std::sync::Arc;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct SlaCalculation {
    pub url_target_id: i32,
    pub url: String,
    pub period_start: DateTime<Utc>,
    pub period_end: DateTime<Utc>,
    pub sla_percentage: f64,
    pub total_checks: i64,
    pub healthy_checks: i64,
    pub unhealthy_checks: i64,
    pub avg_response_time_ms: f64,
    pub min_response_time_ms: i64,
    pub max_response_time_ms: i64,
    pub p50_response_time_ms: Option<i64>,
    pub p95_response_time_ms: Option<i64>,
    pub p99_response_time_ms: Option<i64>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct TrendAnalysis {
    pub url_target_id: i32,
    pub url: String,
    pub trend_direction: TrendDirection,
    pub response_time_change_pct: f64,
    pub health_change_pct: f64,
    pub recent_avg_response_time_ms: f64,
    pub historical_avg_response_time_ms: f64,
    pub recent_health_rate: f64,
    pub historical_health_rate: f64,
}

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq, Eq)]
pub enum TrendDirection {
    Improving,
    Degrading,
    Stable,
    InsufficientData,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct HourlyDataPoint {
    pub hour: DateTime<Utc>,
    pub avg_response_time_ms: f64,
    pub health_rate: f64,
    pub sample_count: i64,
}

pub struct AnalyticsService {
    storage: Arc<Storage>,
}

impl AnalyticsService {
    pub fn new(storage: Arc<Storage>) -> Self {
        AnalyticsService { storage }
    }

    pub async fn calculate_sla_for_period(
        &self,
        url_target_id: i32,
        period_hours: i64,
    ) -> Result<SlaCalculation, Box<dyn std::error::Error>> {
        let now = Utc::now();
        let start = now - Duration::hours(period_hours);

        let results = self
            .storage
            .get_results_for_sla(url_target_id, start, now)
            .await?;

        let target = self
            .storage
            .get_url_target_by_id(url_target_id)
            .await?
            .ok_or("URL target not found")?;

        let total_checks = results.len() as i64;

        if total_checks == 0 {
            return Ok(SlaCalculation {
                url_target_id,
                url: target.url,
                period_start: start,
                period_end: now,
                sla_percentage: 0.0,
                total_checks: 0,
                healthy_checks: 0,
                unhealthy_checks: 0,
                avg_response_time_ms: 0.0,
                min_response_time_ms: 0,
                max_response_time_ms: 0,
                p50_response_time_ms: None,
                p95_response_time_ms: None,
                p99_response_time_ms: None,
            });
        }

        let healthy_checks = results.iter().filter(|r| r.is_healthy).count() as i64;
        let unhealthy_checks = total_checks - healthy_checks;
        let sla_percentage = (healthy_checks as f64 / total_checks as f64) * 100.0;

        let response_times: Vec<i64> = results
            .iter()
            .map(|r| r.response_time_ms)
            .collect();

        let avg_response_time_ms =
            response_times.iter().sum::<i64>() as f64 / response_times.len() as f64;
        let min_response_time_ms = *response_times.iter().min().unwrap_or(&0);
        let max_response_time_ms = *response_times.iter().max().unwrap_or(&0);

        let p50_response_time_ms = calculate_percentile(&response_times, 50.0);
        let p95_response_time_ms = calculate_percentile(&response_times, 95.0);
        let p99_response_time_ms = calculate_percentile(&response_times, 99.0);

        Ok(SlaCalculation {
            url_target_id,
            url: target.url,
            period_start: start,
            period_end: now,
            sla_percentage,
            total_checks,
            healthy_checks,
            unhealthy_checks,
            avg_response_time_ms,
            min_response_time_ms,
            max_response_time_ms,
            p50_response_time_ms,
            p95_response_time_ms,
            p99_response_time_ms,
        })
    }

    pub async fn analyze_trend(
        &self,
        url_target_id: i32,
        recent_hours: i64,
        historical_hours: i64,
    ) -> Result<TrendAnalysis, Box<dyn std::error::Error>> {
        let now = Utc::now();
        let recent_start = now - Duration::hours(recent_hours);
        let historical_start = recent_start - Duration::hours(historical_hours);

        let recent_results = self
            .storage
            .get_results_for_sla(url_target_id, recent_start, now)
            .await?;

        let historical_results = self
            .storage
            .get_results_for_sla(url_target_id, historical_start, recent_start)
            .await?;

        let target = self
            .storage
            .get_url_target_by_id(url_target_id)
            .await?
            .ok_or("URL target not found")?;

        let min_samples = 10;
        if recent_results.len() < min_samples || historical_results.len() < min_samples {
            return Ok(TrendAnalysis {
                url_target_id,
                url: target.url,
                trend_direction: TrendDirection::InsufficientData,
                response_time_change_pct: 0.0,
                health_change_pct: 0.0,
                recent_avg_response_time_ms: 0.0,
                historical_avg_response_time_ms: 0.0,
                recent_health_rate: 0.0,
                historical_health_rate: 0.0,
            });
        }

        let recent_avg_response_time_ms = calculate_avg_response_time(&recent_results);
        let historical_avg_response_time_ms = calculate_avg_response_time(&historical_results);
        let recent_health_rate = calculate_health_rate(&recent_results);
        let historical_health_rate = calculate_health_rate(&historical_results);

        let response_time_change_pct = if historical_avg_response_time_ms > 0.0 {
            ((recent_avg_response_time_ms - historical_avg_response_time_ms)
                / historical_avg_response_time_ms)
                * 100.0
        } else {
            0.0
        };

        let health_change_pct = recent_health_rate - historical_health_rate;

        let trend_direction = if response_time_change_pct < -5.0 || health_change_pct > 2.0 {
            TrendDirection::Improving
        } else if response_time_change_pct > 10.0 || health_change_pct < -5.0 {
            TrendDirection::Degrading
        } else {
            TrendDirection::Stable
        };

        Ok(TrendAnalysis {
            url_target_id,
            url: target.url,
            trend_direction,
            response_time_change_pct,
            health_change_pct,
            recent_avg_response_time_ms,
            historical_avg_response_time_ms,
            recent_health_rate,
            historical_health_rate,
        })
    }

    pub async fn get_hourly_data(
        &self,
        url_target_id: i32,
        hours: i64,
    ) -> Result<Vec<HourlyDataPoint>, Box<dyn std::error::Error>> {
        let now = Utc::now();
        let start = now - Duration::hours(hours);

        let results = self
            .storage
            .get_results_for_sla(url_target_id, start, now)
            .await?;

        let mut hourly_buckets: std::collections::HashMap<DateTime<Utc>, Vec<&CheckResult>> =
            std::collections::HashMap::new();

        for result in &results {
            let hour = result
                .checked_at
                .with_minute(0)
                .unwrap()
                .with_second(0)
                .unwrap()
                .with_nanosecond(0)
                .unwrap();

            hourly_buckets.entry(hour).or_default().push(result);
        }

        let mut data_points: Vec<HourlyDataPoint> = Vec::new();

        for (hour, bucket_results) in hourly_buckets {
            let sample_count = bucket_results.len() as i64;
            let avg_response_time_ms = calculate_avg_response_time(&bucket_results);
            let health_rate = calculate_health_rate(&bucket_results);

            data_points.push(HourlyDataPoint {
                hour,
                avg_response_time_ms,
                health_rate,
                sample_count,
            });
        }

        data_points.sort_by(|a, b| a.hour.cmp(&b.hour));
        Ok(data_points)
    }

    pub async fn aggregate_and_save_history(
        &self,
        url_target_id: i32,
        window_minutes: i64,
    ) -> Result<Option<ResponseTimeHistory>, Box<dyn std::error::Error>> {
        let now = Utc::now();
        let window_start = now - Duration::minutes(window_minutes);

        let results = self
            .storage
            .get_results_for_sla(url_target_id, window_start, now)
            .await?;

        if results.is_empty() {
            return Ok(None);
        }

        let target = self
            .storage
            .get_url_target_by_id(url_target_id)
            .await?
            .ok_or("URL target not found")?;

        let response_times: Vec<i64> = results.iter().map(|r| r.response_time_ms).collect();
        let avg_response_time_ms =
            response_times.iter().sum::<i64>() as f64 / response_times.len() as f64;
        let min_response_time_ms = *response_times.iter().min().unwrap_or(&0);
        let max_response_time_ms = *response_times.iter().max().unwrap_or(&0);

        let healthy_count = results.iter().filter(|r| r.is_healthy).count() as i64;
        let unhealthy_count = results.len() as i64 - healthy_count;

        let history = ResponseTimeHistory {
            id: None,
            url_target_id,
            url: target.url,
            avg_response_time_ms,
            min_response_time_ms,
            max_response_time_ms,
            sample_count: results.len() as i64,
            healthy_count,
            unhealthy_count,
            window_start,
            window_end: now,
        };

        self.storage.save_response_time_history(&history).await?;

        Ok(Some(history))
    }
}

fn calculate_avg_response_time(results: &[&CheckResult]) -> f64 {
    if results.is_empty() {
        return 0.0;
    }
    let sum: i64 = results.iter().map(|r| r.response_time_ms).sum();
    sum as f64 / results.len() as f64
}

fn calculate_health_rate(results: &[&CheckResult]) -> f64 {
    if results.is_empty() {
        return 0.0;
    }
    let healthy = results.iter().filter(|r| r.is_healthy).count() as f64;
    (healthy / results.len() as f64) * 100.0
}

fn calculate_percentile(sorted_values: &[i64], percentile: f64) -> Option<i64> {
    if sorted_values.is_empty() {
        return None;
    }

    let mut sorted = sorted_values.to_vec();
    sorted.sort();

    let index = ((percentile / 100.0) * (sorted.len() - 1) as f64).round() as usize;
    Some(sorted[index.min(sorted.len() - 1)])
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_calculate_health_rate() {
        let mut results: Vec<CheckResult> = Vec::new();
        for i in 0..10 {
            results.push(CheckResult {
                id: None,
                url: "https://example.com".to_string(),
                status_code: Some(if i < 8 { 200 } else { 500 }),
                response_time_ms: 100,
                is_healthy: i < 8,
                error_message: None,
                checked_at: Utc::now(),
            });
        }

        let refs: Vec<&CheckResult> = results.iter().collect();
        let health_rate = calculate_health_rate(&refs);

        assert!((health_rate - 80.0).abs() < 0.01);
    }

    #[test]
    fn test_calculate_percentile() {
        let values = vec![10, 20, 30, 40, 50, 60, 70, 80, 90, 100];

        assert_eq!(calculate_percentile(&values, 50.0), Some(50));
        assert_eq!(calculate_percentile(&values, 95.0), Some(100));
        assert_eq!(calculate_percentile(&values, 99.0), Some(100));
        assert_eq!(calculate_percentile(&[], 50.0), None);
    }
}
