mod alerter;
mod analytics;
mod checker;
mod dashboard;
mod scheduler;
mod storage;

use actix_web::{delete, get, post, web, App, HttpResponse, HttpServer, Responder};
use analytics::AnalyticsService;
use dashboard::{DashboardService, MetricsRegistry};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::Mutex;

use crate::scheduler::Scheduler;
use crate::storage::Storage;

#[derive(Debug, Serialize)]
struct ApiResponse<T> {
    success: bool,
    data: Option<T>,
    message: Option<String>,
}

impl<T> ApiResponse<T> {
    fn success(data: T) -> Self {
        ApiResponse {
            success: true,
            data: Some(data),
            message: None,
        }
    }

    fn error(message: &str) -> Self
    where
        T: Default,
    {
        ApiResponse {
            success: false,
            data: None,
            message: Some(message.to_string()),
        }
    }
}

#[derive(Debug, Deserialize)]
struct AddUrlRequest {
    url: String,
    #[serde(default = "default_interval")]
    interval_seconds: i32,
}

fn default_interval() -> i32 {
    60
}

#[derive(Debug, Deserialize)]
struct CheckUrlRequest {
    url: String,
}

#[derive(Debug, Deserialize)]
struct GetResultsQuery {
    url: Option<String>,
    #[serde(default = "default_limit")]
    limit: i64,
}

fn default_limit() -> i64 {
    50
}

#[derive(Debug, Deserialize)]
struct SlaQuery {
    url_target_id: i32,
    #[serde(default = "default_sla_hours")]
    hours: i64,
}

fn default_sla_hours() -> i64 {
    24
}

#[derive(Debug, Deserialize)]
struct TrendQuery {
    url_target_id: i32,
    #[serde(default = "default_recent_hours")]
    recent_hours: i64,
    #[serde(default = "default_historical_hours")]
    historical_hours: i64,
}

fn default_recent_hours() -> i64 {
    24
}

fn default_historical_hours() -> i64 {
    72
}

#[derive(Debug, Deserialize)]
struct AlertQuery {
    resolved: Option<bool>,
    #[serde(default = "default_limit")]
    limit: i64,
}

struct AppState {
    storage: Arc<Storage>,
    scheduler: Arc<Mutex<Scheduler>>,
    analytics: Arc<AnalyticsService>,
    dashboard: Arc<DashboardService>,
}

#[get("/health")]
async fn health() -> impl Responder {
    HttpResponse::Ok().json(ApiResponse::success(serde_json::json!({
        "status": "ok",
        "service": "url-health-checker"
    })))
}

#[get("/metrics")]
async fn prometheus_metrics() -> impl Responder {
    let metrics = dashboard::render_prometheus_metrics();
    HttpResponse::Ok()
        .content_type("text/plain; version=0.0.4; charset=utf-8")
        .body(metrics)
}

#[get("/api/urls")]
async fn list_urls(state: web::Data<AppState>) -> impl Responder {
    match state.storage.get_active_url_targets().await {
        Ok(urls) => HttpResponse::Ok().json(ApiResponse::success(urls)),
        Err(e) => HttpResponse::InternalServerError().json(ApiResponse::<()>::error(&e.to_string())),
    }
}

#[post("/api/urls")]
async fn add_url(
    state: web::Data<AppState>,
    req: web::Json<AddUrlRequest>,
) -> impl Responder {
    if req.url.is_empty() {
        return HttpResponse::BadRequest().json(ApiResponse::<()>::error("URL is required"));
    }

    if req.interval_seconds < 1 {
        return HttpResponse::BadRequest().json(ApiResponse::<()>::error(
            "Interval must be at least 1 second",
        ));
    }

    match state
        .storage
        .add_url_target(&req.url, req.interval_seconds)
        .await
    {
        Ok(target) => HttpResponse::Created().json(ApiResponse::success(target)),
        Err(e) => HttpResponse::InternalServerError().json(ApiResponse::<()>::error(&e.to_string())),
    }
}

#[delete("/api/urls")]
async fn delete_url(
    state: web::Data<AppState>,
    req: web::Query<CheckUrlRequest>,
) -> impl Responder {
    if req.url.is_empty() {
        return HttpResponse::BadRequest().json(ApiResponse::<()>::error("URL is required"));
    }

    match state.storage.delete_url_target(&req.url).await {
        Ok(_) => HttpResponse::Ok().json(ApiResponse::success(serde_json::json!({
            "deleted": true,
            "url": req.url
        }))),
        Err(e) => HttpResponse::InternalServerError().json(ApiResponse::<()>::error(&e.to_string())),
    }
}

#[post("/api/check")]
async fn check_url(
    state: web::Data<AppState>,
    req: web::Json<CheckUrlRequest>,
) -> impl Responder {
    if req.url.is_empty() {
        return HttpResponse::BadRequest().json(ApiResponse::<()>::error("URL is required"));
    }

    let scheduler = state.scheduler.lock().await;
    match scheduler.run_manual_check(&req.url).await {
        Ok(result) => HttpResponse::Ok().json(ApiResponse::success(result)),
        Err(e) => HttpResponse::InternalServerError().json(ApiResponse::<()>::error(&e.to_string())),
    }
}

#[get("/api/results")]
async fn get_results(
    state: web::Data<AppState>,
    query: web::Query<GetResultsQuery>,
) -> impl Responder {
    let limit = query.limit.clamp(1, 1000);

    let results = if let Some(url) = &query.url {
        state.storage.get_results_by_url(url, limit).await
    } else {
        state.storage.get_recent_results(limit).await
    };

    match results {
        Ok(results) => HttpResponse::Ok().json(ApiResponse::success(results)),
        Err(e) => HttpResponse::InternalServerError().json(ApiResponse::<()>::error(&e.to_string())),
    }
}

#[get("/api/sla")]
async fn get_sla(
    state: web::Data<AppState>,
    query: web::Query<SlaQuery>,
) -> impl Responder {
    let hours = query.hours.clamp(1, 720);

    match state
        .analytics
        .calculate_sla_for_period(query.url_target_id, hours)
        .await
    {
        Ok(sla) => HttpResponse::Ok().json(ApiResponse::success(sla)),
        Err(e) => HttpResponse::InternalServerError().json(ApiResponse::<()>::error(&e.to_string())),
    }
}

#[get("/api/trend")]
async fn get_trend(
    state: web::Data<AppState>,
    query: web::Query<TrendQuery>,
) -> impl Responder {
    let recent_hours = query.recent_hours.clamp(1, 168);
    let historical_hours = query.historical_hours.clamp(1, 720);

    match state
        .analytics
        .analyze_trend(query.url_target_id, recent_hours, historical_hours)
        .await
    {
        Ok(trend) => HttpResponse::Ok().json(ApiResponse::success(trend)),
        Err(e) => HttpResponse::InternalServerError().json(ApiResponse::<()>::error(&e.to_string())),
    }
}

#[get("/api/hourly")]
async fn get_hourly_data(
    state: web::Data<AppState>,
    query: web::Query<SlaQuery>,
) -> impl Responder {
    let hours = query.hours.clamp(1, 168);

    match state
        .analytics
        .get_hourly_data(query.url_target_id, hours)
        .await
    {
        Ok(data) => HttpResponse::Ok().json(ApiResponse::success(data)),
        Err(e) => HttpResponse::InternalServerError().json(ApiResponse::<()>::error(&e.to_string())),
    }
}

#[get("/api/history")]
async fn get_response_time_history(
    state: web::Data<AppState>,
    query: web::Query<GetResultsQuery>,
) -> impl Responder {
    let limit = query.limit.clamp(1, 1000);

    let results = match &query.url {
        Some(url) => {
            let targets = match state.storage.get_active_url_targets().await {
                Ok(t) => t,
                Err(e) => {
                    return HttpResponse::InternalServerError()
                        .json(ApiResponse::<()>::error(&e.to_string()));
                }
            };

            if let Some(target) = targets.iter().find(|t| t.url == *url) {
                if let Some(target_id) = target.id {
                    state.storage.get_response_time_history(target_id, limit).await
                } else {
                    Ok(Vec::new())
                }
            } else {
                Ok(Vec::new())
            }
        }
        None => {
            let targets = match state.storage.get_active_url_targets().await {
                Ok(t) => t,
                Err(e) => {
                    return HttpResponse::InternalServerError()
                        .json(ApiResponse::<()>::error(&e.to_string()));
                }
            };

            let mut all_history = Vec::new();
            for target in targets {
                if let Some(target_id) = target.id {
                    if let Ok(history) = state
                        .storage
                        .get_response_time_history(target_id, limit / 10 + 1)
                        .await
                    {
                        all_history.extend(history);
                    }
                }
            }
            Ok(all_history)
        }
    };

    match results {
        Ok(history) => HttpResponse::Ok().json(ApiResponse::success(history)),
        Err(e) => HttpResponse::InternalServerError().json(ApiResponse::<()>::error(&e.to_string())),
    }
}

#[get("/api/alerts")]
async fn get_alerts(
    state: web::Data<AppState>,
    query: web::Query<AlertQuery>,
) -> impl Responder {
    let limit = query.limit.clamp(1, 1000);

    match state.storage.get_alerts(query.resolved, limit).await {
        Ok(alerts) => HttpResponse::Ok().json(ApiResponse::success(alerts)),
        Err(e) => HttpResponse::InternalServerError().json(ApiResponse::<()>::error(&e.to_string())),
    }
}

#[get("/api/dashboard")]
async fn get_dashboard(state: web::Data<AppState>) -> impl Responder {
    match state.dashboard.get_summary().await {
        Ok(summary) => HttpResponse::Ok().json(ApiResponse::success(summary)),
        Err(e) => HttpResponse::InternalServerError().json(ApiResponse::<()>::error(&e.to_string())),
    }
}

#[get("/api/scheduler/status")]
async fn scheduler_status(state: web::Data<AppState>) -> impl Responder {
    let scheduler = state.scheduler.lock().await;
    let is_running = scheduler.is_running().await;
    let config = scheduler.get_config();

    HttpResponse::Ok().json(ApiResponse::success(serde_json::json!({
        "running": is_running,
        "config": config
    })))
}

#[post("/api/scheduler/start")]
async fn scheduler_start(state: web::Data<AppState>) -> impl Responder {
    let mut scheduler = state.scheduler.lock().await;

    if scheduler.is_running().await {
        return HttpResponse::Ok().json(ApiResponse::success(serde_json::json!({
            "started": false,
            "message": "Scheduler is already running"
        })));
    }

    match scheduler.start().await {
        Ok(_) => HttpResponse::Ok().json(ApiResponse::success(serde_json::json!({
            "started": true,
            "message": "Scheduler started successfully"
        }))),
        Err(e) => HttpResponse::InternalServerError().json(ApiResponse::<()>::error(&e.to_string())),
    }
}

#[post("/api/scheduler/stop")]
async fn scheduler_stop(state: web::Data<AppState>) -> impl Responder {
    let mut scheduler = state.scheduler.lock().await;

    if !scheduler.is_running().await {
        return HttpResponse::Ok().json(ApiResponse::success(serde_json::json!({
            "stopped": false,
            "message": "Scheduler is not running"
        })));
    }

    match scheduler.stop().await {
        Ok(_) => HttpResponse::Ok().json(ApiResponse::success(serde_json::json!({
            "stopped": true,
            "message": "Scheduler stopped successfully"
        }))),
        Err(e) => HttpResponse::InternalServerError().json(ApiResponse::<()>::error(&e.to_string())),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    dotenv::dotenv().ok();

    println!("Initializing URL Health Checker Service...");

    let storage = Arc::new(Storage::new().expect("Failed to initialize storage"));

    println!("Storage initialized, setting up database schema...");

    storage
        .init_schema()
        .await
        .expect("Failed to initialize database schema");

    println!("Database schema initialized.");

    let scheduler = Arc::new(Mutex::new(
        Scheduler::new(storage.clone(), None).expect("Failed to initialize scheduler"),
    ));

    let analytics = Arc::new(AnalyticsService::new(storage.clone()));

    let metrics = Arc::new(MetricsRegistry::new());
    let dashboard = Arc::new(DashboardService::new(storage.clone(), metrics.clone()));

    let app_state = web::Data::new(AppState {
        storage: storage.clone(),
        scheduler: scheduler.clone(),
        analytics: analytics.clone(),
        dashboard: dashboard.clone(),
    });

    let host = std::env::var("HOST").unwrap_or_else(|_| "127.0.0.1".to_string());
    let port = std::env::var("PORT")
        .unwrap_or_else(|_| "8080".to_string())
        .parse::<u16>()
        .unwrap_or(8080);

    println!("Starting server on {}:{}", host, port);

    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(health)
            .service(prometheus_metrics)
            .service(list_urls)
            .service(add_url)
            .service(delete_url)
            .service(check_url)
            .service(get_results)
            .service(get_sla)
            .service(get_trend)
            .service(get_hourly_data)
            .service(get_response_time_history)
            .service(get_alerts)
            .service(get_dashboard)
            .service(scheduler_status)
            .service(scheduler_start)
            .service(scheduler_stop)
    })
    .bind((host.as_str(), port))?
    .run()
    .await
}
