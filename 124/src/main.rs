#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod crypto;
mod device;
mod transfer;
mod history;
mod discovery;
mod server;
mod clipboard;
mod models;
mod config;

pub use crypto::*;
pub use device::*;
pub use transfer::*;
pub use history::*;
pub use discovery::*;
pub use server::*;
pub use clipboard::*;
pub use models::*;
pub use config::*;

use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Clone)]
struct AppState {
    device_manager: Arc<RwLock<DeviceManager>>,
    transfer_manager: Arc<RwLock<TransferManager>>,
    history_manager: Arc<RwLock<HistoryManager>>,
    discovery: Arc<RwLock<DiscoveryService>>,
    http_server: Arc<RwLock<HttpServer>>,
    config: Arc<RwLock<AppConfig>>,
}

impl AppState {
    async fn new() -> Self {
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
async fn get_devices(state: tauri::State<'_, AppState>) -> Result<Vec<DeviceInfo>, String> {
    let devices = state.discovery.read().await.get_devices().await;
    Ok(devices)
}

#[tauri::command]
async fn get_history(state: tauri::State<'_, AppState>) -> Result<Vec<HistoryItem>, String> {
    let history = state.history_manager.read().await.get_all().await;
    Ok(history)
}

#[tauri::command]
async fn search_history(
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
async fn clear_history(state: tauri::State<'_, AppState>) -> Result<(), String> {
    state.history_manager.write().await.clear().await;
    Ok(())
}

#[tauri::command]
async fn read_clipboard_content(_state: tauri::State<'_, AppState>) -> Result<ClipboardContent, String> {
    read_clipboard().await
}

#[tauri::command]
async fn write_clipboard_content(
    _state: tauri::State<'_, AppState>,
    content: ClipboardContent,
) -> Result<(), String> {
    write_clipboard(content).await
}

#[tauri::command]
async fn send_clipboard_content(
    state: tauri::State<'_, AppState>,
    device_id: String,
    content: ClipboardContent,
) -> Result<(), String> {
    state.transfer_manager.write().await.send_content(&device_id, content).await?;
    Ok(())
}

#[tauri::command]
async fn send_file_path(
    state: tauri::State<'_, AppState>,
    device_id: String,
    file_path: String,
) -> Result<(), String> {
    state.transfer_manager.write().await.send_file(&device_id, &file_path).await?;
    Ok(())
}

#[tauri::command]
async fn add_to_whitelist(
    state: tauri::State<'_, AppState>,
    device: DeviceInfo,
) -> Result<(), String> {
    state.device_manager.write().await.add_to_whitelist(device).await;
    Ok(())
}

#[tauri::command]
async fn remove_from_whitelist(
    state: tauri::State<'_, AppState>,
    device_id: String,
) -> Result<(), String> {
    state.device_manager.write().await.remove_from_whitelist(&device_id).await;
    Ok(())
}

#[tauri::command]
async fn get_whitelist_devices(state: tauri::State<'_, AppState>) -> Result<Vec<DeviceInfo>, String> {
    let whitelist = state.device_manager.read().await.get_whitelist().await;
    Ok(whitelist)
}

#[tauri::command]
async fn scan_ip_range(
    state: tauri::State<'_, AppState>,
    start: String,
    end: String,
) -> Result<Vec<DeviceInfo>, String> {
    let devices = state.discovery.write().await.scan_ip_range(&start, &end).await?;
    Ok(devices)
}

#[tauri::command]
async fn generate_pairing_qrcode(state: tauri::State<'_, AppState>) -> Result<String, String> {
    state.discovery.write().await.init_local_device().await;
    let qr_data = state.discovery.read().await.generate_pairing_qrcode().await?;
    Ok(qr_data)
}

#[tauri::command]
async fn parse_qrcode_data(
    state: tauri::State<'_, AppState>,
    data: String,
) -> Result<DeviceInfo, String> {
    let device = state.discovery.write().await.parse_pairing_qrcode(&data).await?;
    Ok(device)
}

#[tauri::command]
async fn get_local_device_info(state: tauri::State<'_, AppState>) -> Result<DeviceInfo, String> {
    let device = state.discovery.read().await.get_local_device().await;
    Ok(device)
}

#[tauri::command]
async fn start_discovery_service(state: tauri::State<'_, AppState>) -> Result<(), String> {
    state.discovery.write().await.start().await.map_err(|e| e.to_string())?;
    state.http_server.write().await.start().await.map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
async fn respond_transfer(
    state: tauri::State<'_, AppState>,
    request_id: String,
    accepted: bool,
) -> Result<(), String> {
    state.transfer_manager.write().await.respond_request(&request_id, accepted).await?;
    Ok(())
}

#[tauri::command]
async fn get_transfer_status(
    state: tauri::State<'_, AppState>,
    transfer_id: String,
) -> Result<TransferProgress, String> {
    let progress = state.transfer_manager.read().await.get_progress(&transfer_id).await?;
    Ok(progress)
}

fn main() {
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
            read_clipboard_content,
            write_clipboard_content,
            send_clipboard_content,
            send_file_path,
            add_to_whitelist,
            remove_from_whitelist,
            get_whitelist_devices,
            scan_ip_range,
            generate_pairing_qrcode,
            parse_qrcode_data,
            get_local_device_info,
            start_discovery_service,
            respond_transfer,
            get_transfer_status,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
