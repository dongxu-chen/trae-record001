mod browser_extension;
mod clipboard;
mod crypto;
mod db;
mod hotkey;
mod main_window;
mod sync;

use browser_extension::ExtensionServer;
use clipboard::ClipboardManager;
use crypto::Crypto;
use db::Database;
use hotkey::HotkeyManager;
use sync::SyncManager;
use gtk::prelude::*;
use gtk::{
    Application, ApplicationWindow, Button, Dialog, Entry, Label, MessageDialog,
    MessageType, ButtonsType, ResponseType,
};
use std::path::PathBuf;

const APP_ID: &str = "com.example.PasswordManager";

fn main() {
    let app = Application::builder()
        .application_id(APP_ID)
        .build();

    app.connect_activate(|app| {
        let display = match gtk::gdk::Display::default() {
            Some(d) => d,
            None => {
                let dialog = MessageDialog::new(
                    None::<&ApplicationWindow>,
                    gtk::DialogFlags::MODAL,
                    MessageType::Error,
                    ButtonsType::Ok,
                    "无法获取显示设备",
                );
                dialog.run();
                dialog.close();
                return;
            }
        };
        
        let clipboard = ClipboardManager::new(&display);
        
        let db_path = get_db_path();
        let db = match Database::new(db_path) {
            Ok(db) => db,
            Err(e) => {
                let dialog = MessageDialog::new(
                    None::<&ApplicationWindow>,
                    gtk::DialogFlags::MODAL,
                    MessageType::Error,
                    ButtonsType::Ok,
                    &format!("无法打开数据库: {:?}", e),
                );
                dialog.run();
                dialog.close();
                return;
            }
        };

        let hotkey_manager = HotkeyManager::new();
        let extension_server = ExtensionServer::new(browser_extension::DEFAULT_PORT);
        let sync_manager = SyncManager::new();
        
        show_auth_dialog(app, db, clipboard, hotkey_manager, extension_server, sync_manager);
    });

    app.run();
}

fn get_db_path() -> PathBuf {
    if let Some(data_dir) = dirs::data_dir() {
        data_dir.join("password_manager").join("passwords.db")
    } else {
        PathBuf::from("passwords.db")
    }
}

fn show_auth_dialog(
    app: &Application,
    db: Database,
    clipboard: ClipboardManager,
    hotkey_manager: HotkeyManager,
    extension_server: ExtensionServer,
    sync_manager: SyncManager,
) {
    let is_first_run = db.get_salt().unwrap_or(None).is_none();
    
    let dialog = Dialog::new();
    dialog.set_application(Some(app));
    dialog.set_title(Some("密码管理器"));
    dialog.set_modal(true);
    dialog.set_default_size(400, -1);
    dialog.set_resizable(false);
    
    let content_area = dialog.content_area();
    content_area.set_margin_top(24);
    content_area.set_margin_bottom(24);
    content_area.set_margin_start(24);
    content_area.set_margin_end(24);
    content_area.set_spacing(12);
    
    let title_label = Label::new(Some(
        if is_first_run {
            "设置主密码"
        } else {
            "输入主密码"
        }
    ));
    title_label.add_css_class("title-2");
    content_area.append(&title_label);
    
    let hint_label = Label::new(Some(
        if is_first_run {
            "请设置一个安全的主密码，这将用于加密您的所有密码"
        } else {
            "请输入您的主密码以解锁密码管理器"
        }
    ));
    hint_label.add_css_class("dim-label");
    hint_label.set_wrap(true);
    content_area.append(&hint_label);
    
    let password_entry = Entry::new();
    password_entry.set_placeholder_text(Some("主密码"));
    password_entry.set_visibility(false);
    password_entry.set_input_purpose(gtk::InputPurpose::Password);
    content_area.append(&password_entry);
    
    let confirm_entry = if is_first_run {
        let entry = Entry::new();
        entry.set_placeholder_text(Some("确认主密码"));
        entry.set_visibility(false);
        entry.set_input_purpose(gtk::InputPurpose::Password);
        content_area.append(&entry);
        Some(entry)
    } else {
        None
    };
    
    let error_label = Label::new(None);
    error_label.add_css_class("error");
    content_area.append(&error_label);
    
    dialog.add_button("取消", ResponseType::Cancel);
    let ok_btn = if is_first_run {
        dialog.add_button("创建", ResponseType::Ok)
    } else {
        dialog.add_button("解锁", ResponseType::Ok)
    };
    ok_btn.add_css_class("suggested-action");
    
    let password_entry_clone = password_entry.clone();
    let confirm_entry_clone = confirm_entry.clone();
    let dialog_clone = dialog.clone();
    password_entry.connect_activate(move |_| {
        if let Some(ref confirm) = confirm_entry_clone {
            if confirm.text().is_empty() {
                confirm.grab_focus();
            } else {
                dialog_clone.response(ResponseType::Ok);
            }
        } else {
            dialog_clone.response(ResponseType::Ok);
        }
    });
    
    if let Some(ref confirm) = confirm_entry {
        let dialog_clone = dialog.clone();
        confirm.connect_activate(move |_| {
            dialog_clone.response(ResponseType::Ok);
        });
    }
    
    let app_clone = app.clone();
    dialog.connect_response(move |dialog, response| {
        if response == ResponseType::Ok {
            let password = password_entry_clone.text().to_string();
            
            if password.is_empty() {
                error_label.set_text("请输入主密码");
                return;
            }
            
            if is_first_run {
                if let Some(ref confirm) = confirm_entry_clone {
                    let confirm_pw = confirm.text().to_string();
                    if password != confirm_pw {
                        error_label.set_text("两次输入的密码不一致");
                        return;
                    }
                    
                    let salt = match Crypto::generate_salt() {
                        Ok(s) => s,
                        Err(_) => {
                            error_label.set_text("生成加密盐失败");
                            return;
                        }
                    };
                    if db.set_salt(&salt).is_err() {
                        error_label.set_text("保存设置失败");
                        return;
                    }
                    
                    let crypto = match Crypto::new(&password, &salt) {
                        Ok(c) => c,
                        Err(_) => {
                            error_label.set_text("密码初始化失败");
                            return;
                        }
                    };
                    
                    dialog.close();
                    build_main_window(
                        &app_clone,
                        db,
                        Some(crypto),
                        clipboard,
                        hotkey_manager,
                        extension_server,
                        sync_manager,
                    );
                }
            } else {
                let salt = match db.get_salt() {
                    Ok(Some(s)) => s,
                    _ => {
                        error_label.set_text("读取设置失败");
                        return;
                    }
                };
                
                let crypto = match Crypto::new(&password, &salt) {
                    Ok(c) => c,
                    Err(_) => {
                        error_label.set_text("密码验证失败");
                        return;
                    }
                };
                
                let test_entry = db.get_all_passwords().ok().and_then(|v| v.first().cloned());
                if let Some(entry) = test_entry {
                    if crypto.decrypt(&entry.encrypted_password).is_err() {
                        error_label.set_text("主密码错误");
                        return;
                    }
                }
                
                dialog.close();
                build_main_window(
                    &app_clone,
                    db,
                    Some(crypto),
                    clipboard,
                    hotkey_manager,
                    extension_server,
                    sync_manager,
                );
            }
        } else {
            dialog.close();
        }
    });
    
    dialog.show();
    password_entry.grab_focus();
}

fn build_main_window(
    app: &Application,
    db: Database,
    crypto: Option<Crypto>,
    clipboard: ClipboardManager,
    hotkey_manager: HotkeyManager,
    extension_server: ExtensionServer,
    sync_manager: SyncManager,
) {
    let window = ApplicationWindow::builder()
        .application(app)
        .title("密码管理器")
        .default_size(800, 600)
        .build();
    
    let main_win = main_window::MainWindow::new(
        window,
        db,
        crypto,
        clipboard,
        hotkey_manager,
        extension_server,
        sync_manager,
    );
    main_win.show();
}

