use crate::alerter::{AlerterService, AlertContext, AlertConfig};
use crate::checker::{CheckerConfig, HealthChecker};
use crate::dashboard::MetricsRegistry;
use crate::storage::{CheckResult, Storage, UrlTarget};
use chrono::{DateTime, Duration as ChronoDuration, Utc};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::{mpsc, RwLock};
use tokio::time::{self, Duration, Instant};

#[derive(Debug, Clone)]
pub struct SchedulerConfig {
    pub default_interval_seconds: u64,
    pub request_timeout_seconds: u64,
    pub tick_interval_seconds: u64,
    pub max_concurrent_checks: usize,
    pub batch_size: usize,
    pub history_aggregation_minutes: i64,
}

impl Default for SchedulerConfig {
    fn default() -> Self {
        SchedulerConfig {
            default_interval_seconds: 60,
            request_timeout_seconds: 10,
            tick_interval_seconds: 5,
            max_concurrent_checks: 32,
            batch_size: 100,
            history_aggregation_minutes: 60,
        }
    }
}

pub struct Scheduler {
    storage: Arc<Storage>,
    checker: Arc<HealthChecker>,
    alerter: Arc<AlerterService>,
    metrics: Arc<MetricsRegistry>,
    config: SchedulerConfig,
    last_check_times: Arc<RwLock<HashMap<i32, DateTime<Utc>>>>,
    last_history_aggregation: Arc<RwLock<DateTime<Utc>>>,
    is_running: Arc<RwLock<bool>>,
    shutdown_tx: Option<mpsc::Sender<()>>,
}

impl Scheduler {
    pub fn new(
        storage: Arc<Storage>,
        config: Option<SchedulerConfig>,
    ) -> Result<Self, Box<dyn std::error::Error>> {
        let config = config.unwrap_or_default();
        
        let checker_config = CheckerConfig {
            timeout_seconds: config.request_timeout_seconds,
            max_concurrent_requests: config.max_concurrent_checks,
            connect_timeout_seconds: 5,
        };
        let checker = Arc::new(HealthChecker::with_config(checker_config)?);
        let alerter = Arc::new(AlerterService::new(storage.clone(), None));
        let metrics = Arc::new(MetricsRegistry::new());

        Ok(Scheduler {
            storage,
            checker,
            alerter,
            metrics,
            config,
            last_check_times: Arc::new(RwLock::new(HashMap::new())),
            last_history_aggregation: Arc::new(RwLock::new(Utc::now())),
            is_running: Arc::new(RwLock::new(false)),
            shutdown_tx: None,
        })
    }

    pub fn with_alert_config(
        storage: Arc<Storage>,
        scheduler_config: Option<SchedulerConfig>,
        alert_config: Option<AlertConfig>,
    ) -> Result<Self, Box<dyn std::error::Error>> {
        let config = scheduler_config.unwrap_or_default();
        
        let checker_config = CheckerConfig {
            timeout_seconds: config.request_timeout_seconds,
            max_concurrent_requests: config.max_concurrent_checks,
            connect_timeout_seconds: 5,
        };
        let checker = Arc::new(HealthChecker::with_config(checker_config)?);
        let alerter = Arc::new(AlerterService::new(storage.clone(), alert_config));
        let metrics = Arc::new(MetricsRegistry::new());

        Ok(Scheduler {
            storage,
            checker,
            alerter,
            metrics,
            config,
            last_check_times: Arc::new(RwLock::new(HashMap::new())),
            last_history_aggregation: Arc::new(RwLock::new(Utc::now())),
            is_running: Arc::new(RwLock::new(false)),
            shutdown_tx: None,
        })
    }

    pub async fn start(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        {
            let mut running = self.is_running.write().await;
            if *running {
                return Ok(());
            }
            *running = true;
        }

        let (shutdown_tx, mut shutdown_rx) = mpsc::channel(1);
        self.shutdown_tx = Some(shutdown_tx);

        let storage = self.storage.clone();
        let checker = self.checker.clone();
        let alerter = self.alerter.clone();
        let metrics = self.metrics.clone();
        let config = self.config.clone();
        let last_check_times = self.last_check_times.clone();
        let last_history_aggregation = self.last_history_aggregation.clone();
        let is_running = self.is_running.clone();

        tokio::spawn(async move {
            let mut tick_interval = time::interval(Duration::from_secs(config.tick_interval_seconds));

            loop {
                tokio::select! {
                    _ = tick_interval.tick() => {
                        if !*is_running.read().await {
                            break;
                        }

                        if let Err(e) = Self::run_check_cycle(
                            &storage,
                            &checker,
                            &alerter,
                            &metrics,
                            &config,
                            &last_check_times,
                            &last_history_aggregation,
                        )
                        .await
                        {
                            eprintln!("Check cycle error: {}", e);
                        }
                    }
                    _ = shutdown_rx.recv() => {
                        break;
                    }
                }
            }

            let mut running = is_running.write().await;
            *running = false;
        });

        Ok(())
    }

    pub async fn stop(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        if let Some(tx) = self.shutdown_tx.take() {
            let _ = tx.send(()).await;
        }
        Ok(())
    }

    pub async fn is_running(&self) -> bool {
        *self.is_running.read().await
    }

    async fn run_check_cycle(
        storage: &Arc<Storage>,
        checker: &Arc<HealthChecker>,
        alerter: &Arc<AlerterService>,
        metrics: &Arc<MetricsRegistry>,
        config: &SchedulerConfig,
        last_check_times: &Arc<RwLock<HashMap<i32, DateTime<Utc>>>>,
        last_history_aggregation: &Arc<RwLock<DateTime<Utc>>>,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let targets = storage.get_active_url_targets().await?;
        let now_utc = Utc::now();

        let mut targets_to_check: Vec<UrlTarget> = Vec::new();

        {
            let last_checks = last_check_times.read().await;
            for target in targets {
                let target_id = target.id.unwrap_or(0);
                let chrono_interval = ChronoDuration::seconds(target.interval_seconds as i64);

                let should_check = match last_checks.get(&target_id) {
                    Some(last_time_utc) => {
                        let elapsed = now_utc.signed_duration_since(*last_time_utc);
                        elapsed >= chrono_interval
                    }
                    None => true,
                };

                if should_check {
                    targets_to_check.push(target);
                }
            }
        }

        if targets_to_check.is_empty() {
            let should_aggregate = {
                let last_agg = last_history_aggregation.read().await;
                now_utc.signed_duration_since(*last_agg)
                    >= ChronoDuration::minutes(config.history_aggregation_minutes)
            };

            if should_aggregate {
                Self::aggregate_history(storage, last_history_aggregation, config.history_aggregation_minutes).await;
            }
            return Ok(());
        }

        let target_map: HashMap<i32, UrlTarget> = targets_to_check
            .iter()
            .map(|t| (t.id.unwrap_or(0), t.clone()))
            .collect();

        let check_futures: Vec<_> = targets_to_check
            .into_iter()
            .map(|target| {
                let checker_clone = checker.clone();
                tokio::spawn(async move {
                    let target_id = target.id.unwrap_or(0);
                    let result = checker_clone.check_url(&target.url).await;
                    (target_id, result)
                })
            })
            .collect();

        let mut all_results: Vec<(i32, CheckResult)> = Vec::new();
        let mut checked_targets: Vec<(i32, DateTime<Utc>)> = Vec::new();
        let check_time = Utc::now();

        for future in check_futures {
            match future.await {
                Ok((target_id, result)) => {
                    metrics.record_check(result.is_healthy, result.response_time_ms, &result.url);

                    if let Some(target) = target_map.get(&target_id) {
                        let ctx = AlertContext {
                            url_target_id: target_id,
                            url: target.url.clone(),
                            consecutive_failures: if result.is_healthy { 0 } else { 1 },
                            last_response_time_ms: Some(result.response_time_ms),
                            sla_percentage: None,
                        };

                        if let Err(e) = alerter.check_and_alert(&ctx).await {
                            eprintln!("Alert check failed for {}: {}", target.url, e);
                        }
                    }

                    all_results.push((target_id, result));
                    checked_targets.push((target_id, check_time));
                }
                Err(e) => {
                    eprintln!("Check task panicked: {}", e);
                }
            }
        }

        if !all_results.is_empty() {
            let result_batch: Vec<(i32, CheckResult)> = all_results
                .into_iter()
                .map(|(id, r)| (id, r))
                .collect();

            let batch_size = config.batch_size;
            for chunk in result_batch.chunks(batch_size) {
                let chunk_vec: Vec<(i32, CheckResult)> = chunk.to_vec();
                if let Err(e) = storage.save_check_results_batch(&chunk_vec).await {
                    eprintln!("Failed to save batch: {}", e);
                }
            }
        }

        if !checked_targets.is_empty() {
            let mut last_checks = last_check_times.write().await;
            for (target_id, check_time) in checked_targets {
                last_checks.insert(target_id, check_time);
            }
        }

        let should_aggregate = {
            let last_agg = last_history_aggregation.read().await;
            now_utc.signed_duration_since(*last_agg)
                >= ChronoDuration::minutes(config.history_aggregation_minutes)
        };

        if should_aggregate {
            Self::aggregate_history(storage, last_history_aggregation, config.history_aggregation_minutes).await;
        }

        Ok(())
    }

    async fn aggregate_history(
        storage: &Arc<Storage>,
        last_history_aggregation: &Arc<RwLock<DateTime<Utc>>>,
        window_minutes: i64,
    ) {
        let targets = match storage.get_active_url_targets().await {
            Ok(t) => t,
            Err(e) => {
                eprintln!("Failed to get targets for aggregation: {}", e);
                return;
            }
        };

        for target in targets {
            let target_id = target.id.unwrap_or(0);
            let now = Utc::now();
            let window_start = now - ChronoDuration::minutes(window_minutes);

            let results = match storage
                .get_results_for_sla(target_id, window_start, now)
                .await
            {
                Ok(r) => r,
                Err(e) => {
                    eprintln!("Failed to get results for aggregation: {}", e);
                    continue;
                }
            };

            if results.is_empty() {
                continue;
            }

            let response_times: Vec<i64> = results.iter().map(|r| r.response_time_ms).collect();
            let avg_response_time_ms =
                response_times.iter().sum::<i64>() as f64 / response_times.len() as f64;
            let min_response_time_ms = *response_times.iter().min().unwrap_or(&0);
            let max_response_time_ms = *response_times.iter().max().unwrap_or(&0);

            let healthy_count = results.iter().filter(|r| r.is_healthy).count() as i64;
            let unhealthy_count = results.len() as i64 - healthy_count;

            let history = crate::storage::ResponseTimeHistory {
                id: None,
                url_target_id: target_id,
                url: target.url.clone(),
                avg_response_time_ms,
                min_response_time_ms,
                max_response_time_ms,
                sample_count: results.len() as i64,
                healthy_count,
                unhealthy_count,
                window_start,
                window_end: now,
            };

            if let Err(e) = storage.save_response_time_history(&history).await {
                eprintln!("Failed to save history for {}: {}", target.url, e);
            }
        }

        let mut last_agg = last_history_aggregation.write().await;
        *last_agg = Utc::now();
    }

    pub async fn run_manual_check(
        &self,
        url: &str,
    ) -> Result<crate::storage::CheckResult, Box<dyn std::error::Error>> {
        let result = self.checker.check_url(url).await;

        let targets = self.storage.get_active_url_targets().await?;
        if let Some(target) = targets.iter().find(|t| t.url == url) {
            if let Some(target_id) = target.id {
                self.storage
                    .save_check_results_batch(&[(target_id, result.clone())])
                    .await?;

                let mut last_checks = self.last_check_times.write().await;
                last_checks.insert(target_id, Utc::now());
            }
        }

        Ok(result)
    }

    pub fn get_config(&self) -> &SchedulerConfig {
        &self.config
    }

    pub fn get_alerter(&self) -> &Arc<AlerterService> {
        &self.alerter
    }

    pub fn get_metrics(&self) -> &Arc<MetricsRegistry> {
        &self.metrics
    }

    pub fn get_storage(&self) -> &Arc<Storage> {
        &self.storage
    }
}
