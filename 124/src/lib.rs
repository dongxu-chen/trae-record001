pub mod crypto;
pub mod device;
pub mod transfer;
pub mod history;
pub mod discovery;
pub mod server;
pub mod clipboard;
pub mod models;
pub mod config;

pub use crypto::*;
pub use device::*;
pub use transfer::*;
pub use history::*;
pub use discovery::*;
pub use server::*;
pub use clipboard::*;
pub use models::*;
pub use config::*;

use tauri::Manager;
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Clone)]
pub struct AppState {
    pub device_manager: Arc<RwLock<DeviceManager>>,
    pub transfer_manager: Arc<RwLock<TransferManager>>,
    pub history_manager: Arc<RwLock<HistoryManager>>,
    pub discovery: Arc<RwLock<DiscoveryService>>,
    pub http_server: Arc<RwLock<HttpServer>>,
    pub config: Arc<RwLock<AppConfig>>,
}

impl AppState {
    pub async fn new() -> Self {
        let config = Arc::new(RwLock::new(AppConfig::load().await));
        let device_manager = Arc::new(RwLock::new(DeviceManager::new().await));
        let transfer_manager = Arc::new(RwLock::new(TransferManager::new()));
        let history_manager = Arc::new(RwLock::new(HistoryManager::new().await));
        let discovery = Arc::new(RwLock::new(DiscoveryService::new()));
        let http_server = Arc::new(RwLock::new(HttpServer::new()));
        
        Self {
            device_manager,
            transfer_manager,
            history_manager,
            discovery,
            http_server,
            config,
        }
    }
}

#[tauri::command]
pub async fn get_devices(state: tauri::State<'_, AppState>) -> Result<Vec<DeviceInfo>, String> {
    let devices = state.discovery.read().await.get_devices().await;
    Ok(devices)
}

#[tauri::command]
pub async fn get_history(state: tauri::State<'_, AppState>) -> Result<Vec<HistoryItem>, String> {
    let history = state.history_manager.read().await.get_all().await;
    Ok(history)
}

#[tauri::command]
pub async fn search_history(
    state: tauri::State<'_, AppState>,
    keyword: Option<String>,
    item_type: Option<String>,
    start_date: Option<String>,
    end_date: Option<String>,
) -> Result<Vec<HistoryItem>, String> {
    let results = state.history_manager.read().await.search(
        keyword.as_deref(),
        item_type.as_deref(),
        start_date.as_deref(),
        end_date.as_deref(),
    ).await;
    Ok(results)
}

#[tauri::command]
pub async fn clear_history(state: tauri::State<'_, AppState>) -> Result<(), String> {
    state.history_manager.write().await.clear().await;
    Ok(())
}

#[tauri::command]
pub async fn read_clipboard(state: tauri::State<'_, AppState>) -> Result<ClipboardContent, String> {
    clipboard::read_clipboard().await
}

#[tauri::command]
pub async fn write_clipboard(state: tauri::State<'_, AppState>, content: ClipboardContent) -> Result<(), String> {
    clipboard::write_clipboard(content).await
}

#[tauri::command]
pub async fn send_clipboard(
    state: tauri::State<'_, AppState>,
    device_id: String,
    content: ClipboardContent,
) -> Result<(), String> {
    state.transfer_manager.write().await.send_content(&device_id, content).await?;
    Ok(())
}

#[tauri::command]
pub async fn send_file(
    state: tauri::State<'_, AppState>,
    device_id: String,
    file_path: String,
) -> Result<(), String> {
    state.transfer_manager.write().await.send_file(&device_id, &file_path).await?;
    Ok(())
}

#[tauri::command]
pub async fn add_to_whitelist(
    state: tauri::State<'_, AppState>,
    device: DeviceInfo,
) -> Result<(), String> {
    state.device_manager.write().await.add_to_whitelist(device).await;
    Ok(())
}

#[tauri::command]
pub async fn remove_from_whitelist(
    state: tauri::State<'_, AppState>,
    device_id: String,
) -> Result<(), String> {
    state.device_manager.write().await.remove_from_whitelist(&device_id).await;
    Ok(())
}

#[tauri::command]
pub async fn get_whitelist(state: tauri::State<'_, AppState>) -> Result<Vec<DeviceInfo>, String> {
    let whitelist = state.device_manager.read().await.get_whitelist().await;
    Ok(whitelist)
}

#[tauri::command]
pub async fn start_ip_scan(
    state: tauri::State<'_, AppState>,
    start_ip: String,
    end_ip: String,
) -> Result<Vec<DeviceInfo>, String> {
    let devices = state.discovery.write().await.scan_ip_range(&start_ip, &end_ip).await?;
    Ok(devices)
}

#[tauri::command]
pub async fn generate_qrcode(state: tauri::State<'_, AppState>) -> Result<String, String> {
    let qr_data = state.discovery.read().await.generate_pairing_qrcode().await?;
    Ok(qr_data)
}

#[tauri::command]
pub async fn scan_qrcode_data(state: tauri::State<'_, AppState>, data: String) -> Result<DeviceInfo, String> {
    let device = state.discovery.write().await.parse_pairing_qrcode(&data).await?;
    Ok(device)
}

#[tauri::command]
pub async fn get_local_device(state: tauri::State<'_, AppState>) -> Result<DeviceInfo, String> {
    let device = state.discovery.read().await.get_local_device().await;
    Ok(device)
}

#[tauri::command]
pub async fn start_discovery(state: tauri::State<'_, AppState>) -> Result<(), String> {
    state.discovery.write().await.start().await?;
    Ok(())
}

#[tauri::command]
pub async fn stop_discovery(state: tauri::State<'_, AppState>) -> Result<(), String> {
    state.discovery.write().await.stop().await;
    Ok(())
}

#[tauri::command]
pub async fn respond_transfer_request(
    state: tauri::State<'_, AppState>,
    request_id: String,
    accepted: bool,
) -> Result<(), String> {
    state.transfer_manager.write().await.respond_request(&request_id, accepted).await?;
    Ok(())
}

#[tauri::command]
pub async fn get_transfer_progress(state: tauri::State<'_, AppState>, transfer_id: String) -> Result<TransferProgress, String> {
    let progress = state.transfer_manager.read().await.get_progress(&transfer_id).await?;
    Ok(progress)
}

pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let app_handle = app.handle();
            tauri::async_runtime::spawn(async move {
                let state = AppState::new().await;
                
                state.discovery.write().await.start().await.ok();
                state.http_server.write().await.start().await.ok();
                
                app_handle.manage(state);
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_devices,
            get_history,
            search_history,
            clear_history,
            read_clipboard,
            write_clipboard,
            send_clipboard,
            send_file,
            add_to_whitelist,
            remove_from_whitelist,
            get_whitelist,
            start_ip_scan,
            generate_qrcode,
            scan_qrcode_data,
            get_local_device,
            start_discovery,
            stop_discovery,
            respond_transfer_request,
            get_transfer_progress,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
