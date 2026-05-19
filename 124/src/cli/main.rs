use clap::Parser;
use clipboard_sync::{
    DiscoveryService, DeviceManager, HistoryManager, 
    TransferManager, AppConfig,
};
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(clap::Subcommand, Debug)]
enum Commands {
    /// 启动后台服务
    Serve,
    
    /// 列出发现的设备
    Devices,
    
    /// 列出信任设备
    Whitelist,
    
    /// 扫描IP范围
    Scan {
        #[arg(short, long)]
        start: String,
        #[arg(short, long)]
        end: String,
    },
    
    /// 显示历史记录
    History,
    
    /// 搜索历史记录
    Search {
        #[arg(short, long)]
        keyword: Option<String>,
        #[arg(short, long)]
        r#type: Option<String>,
    },
    
    /// 生成配对二维码
    Qrcode,
    
    /// 发送剪贴板内容到设备
    Send {
        #[arg(short, long)]
        device_id: String,
        #[arg(short, long)]
        text: Option<String>,
        #[arg(short, long)]
        file: Option<String>,
    },
}

#[tokio::main]
async fn main() {
    let cli = Cli::parse();
    
    let config = Arc::new(RwLock::new(AppConfig::load().await));
    let discovery = Arc::new(RwLock::new(DiscoveryService::new()));
    let device_manager = Arc::new(RwLock::new(DeviceManager::new().await));
    let history_manager = Arc::new(RwLock::new(HistoryManager::new().await));
    let transfer_manager = Arc::new(RwLock::new(TransferManager::new()));
    
    match cli.command {
        Commands::Serve => {
            println!("启动剪贴板同步服务...");
            discovery.write().await.start().await.ok();
            println!("服务已启动，按Ctrl+C停止");
            
            tokio::signal::ctrl_c().await.ok();
            println!("正在停止服务...");
            discovery.write().await.stop().await;
        }
        
        Commands::Devices => {
            let devices = discovery.read().await.get_devices().await;
            if devices.is_empty() {
                println!("未发现设备");
            } else {
                println!("发现的设备:");
                for device in devices {
                    println!("  - {} ({}) [{}] {}", 
                        device.name, device.id, device.address,
                        if device.trusted { "✓ 已信任" } else { "" }
                    );
                }
            }
        }
        
        Commands::Whitelist => {
            let devices = device_manager.read().await.get_whitelist().await;
            if devices.is_empty() {
                println!("白名单为空");
            } else {
                println!("信任设备:");
                for device in devices {
                    println!("  - {} ({}) {}", device.name, device.id, device.address);
                }
            }
        }
        
        Commands::Scan { start, end } => {
            println!("扫描IP范围 {} - {}", start, end);
            match discovery.write().await.scan_ip_range(&start, &end).await {
                Ok(devices) => {
                    println!("发现 {} 个设备:", devices.len());
                    for device in devices {
                        println!("  - {} ({}) {}", device.name, device.id, device.address);
                    }
                }
                Err(e) => println!("扫描失败: {}", e),
            }
        }
        
        Commands::History => {
            let history = history_manager.read().await.get_all().await;
            if history.is_empty() {
                println!("历史记录为空");
            } else {
                println!("历史记录:");
                for item in history {
                    println!("  [{}] {} -> {}: {} {}", 
                        item.timestamp.format("%Y-%m-%d %H:%M"),
                        if matches!(item.direction, clipboard_sync::TransferDirection::Send) { "发送" } else { "接收" },
                        item.peer_device_name,
                        item.content_preview,
                        if item.encrypted { "🔒" } else { "" }
                    );
                }
            }
        }
        
        Commands::Search { keyword, r#type } => {
            let results = history_manager.read().await.search(
                keyword.as_deref(),
                r#type.as_deref(),
                None,
                None,
            ).await;
            
            if results.is_empty() {
                println!("未找到匹配的记录");
            } else {
                println!("找到 {} 条记录:", results.len());
                for item in results {
                    println!("  [{}] {}: {}", 
                        item.timestamp.format("%Y-%m-%d %H:%M"),
                        item.peer_device_name,
                        item.content_preview
                    );
                }
            }
        }
        
        Commands::Qrcode => {
            discovery.write().await.init_local_device().await;
            match discovery.read().await.generate_pairing_qrcode().await {
                Ok(qr) => {
                    println!("配对二维码:");
                    println!("{}", qr);
                    let device = discovery.read().await.get_local_device().await;
                    println!("\n设备信息:");
                    println!("  名称: {}", device.name);
                    println!("  ID: {}", device.id);
                    println!("  地址: {}:{}", device.address, device.port);
                }
                Err(e) => println!("生成二维码失败: {}", e),
            }
        }
        
        Commands::Send { device_id, text, file } => {
            if let Some(text_content) = text {
                let content = clipboard_sync::ClipboardContent {
                    content_type: clipboard_sync::ContentType::Text,
                    data: text_content.as_bytes().to_vec(),
                    text_preview: Some(text_content.chars().take(50).collect()),
                    file_name: None,
                    file_size: None,
                };
                match transfer_manager.write().await.send_content(&device_id, content).await {
                    Ok(_) => println!("发送成功"),
                    Err(e) => println!("发送失败: {}", e),
                }
            } else if let Some(file_path) = file {
                match transfer_manager.write().await.send_file(&device_id, &file_path).await {
                    Ok(_) => println!("发送成功"),
                    Err(e) => println!("发送失败: {}", e),
                }
            } else {
                println!("请指定 --text 或 --file 参数");
            }
        }
    }
}
