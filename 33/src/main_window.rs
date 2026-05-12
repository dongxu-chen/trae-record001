use crate::browser_extension::ExtensionServer;
use crate::clipboard::ClipboardManager;
use crate::crypto::Crypto;
use crate::db::{Database, PasswordEntry};
use crate::hotkey::HotkeyManager;
use crate::sync::{SyncConfig, SyncManager, SyncType};
use gtk::prelude::*;
use gtk::{
    ApplicationWindow, Button, CheckButton, ComboBoxText, Entry, Grid, Label, ListBox,
    ListBoxRow, MessageDialog, MessageType, ScrolledWindow, Stack, ButtonsType,
    Dialog, ResponseType, Paned, HeaderBar, TextBuffer, TextView, Widget,
};
use std::cell::RefCell;
use std::rc::Rc;
use std::sync::{Arc, Mutex};

#[derive(Clone)]
pub struct AppState {
    pub db: Arc<Database>,
    pub crypto: Option<Arc<Crypto>>,
    pub clipboard: ClipboardManager,
    pub entries: Rc<RefCell<Vec<PasswordEntry>>>,
    pub current_query: Rc<RefCell<String>>,
    pub selected_id: Rc<RefCell<Option<i64>>>,
    pub window: Rc<ApplicationWindow>,
    pub hotkey_manager: Arc<Mutex<HotkeyManager>>,
    pub extension_server: Arc<Mutex<ExtensionServer>>,
    pub sync_manager: Arc<Mutex<SyncManager>>,
}

impl AppState {
    fn new(
        db: Database,
        crypto: Option<Crypto>,
        clipboard: ClipboardManager,
        window: ApplicationWindow,
        hotkey_manager: HotkeyManager,
        extension_server: ExtensionServer,
        sync_manager: SyncManager,
    ) -> Self {
        let entries = Rc::new(RefCell::new(db.get_all_passwords().unwrap_or_default()));
        AppState {
            db: Arc::new(db),
            crypto: crypto.map(Arc::new),
            clipboard,
            entries,
            current_query: Rc::new(RefCell::new(String::new())),
            selected_id: Rc::new(RefCell::new(None)),
            window: Rc::new(window),
            hotkey_manager: Arc::new(Mutex::new(hotkey_manager)),
            extension_server: Arc::new(Mutex::new(extension_server)),
            sync_manager: Arc::new(Mutex::new(sync_manager)),
        }
    }
}

fn iter_children<F: FnMut(&Widget)>(widget: &Widget, mut f: F) {
    if let Some(mut child) = widget.first_child() {
        loop {
            f(&child);
            match child.next_sibling() {
                Some(next) => child = next,
                None => break,
            }
        }
    }
}

fn find_entry_widget_by_name(parent: &Widget, name: &str) -> Option<Entry> {
    let mut result: Option<Entry> = None;
    iter_children(parent, |child| {
        if let Some(entry) = child.downcast_ref::<Entry>() {
            if entry.widget_name().as_deref() == Some(name) {
                result = Some(entry.clone());
            }
        }
        if result.is_none() {
            if let Some(found) = find_entry_widget_by_name(child, name) {
                result = Some(found);
            }
        }
    });
    result
}

fn find_text_view_by_name(parent: &Widget, name: &str) -> Option<TextView> {
    let mut result: Option<TextView> = None;
    iter_children(parent, |child| {
        if let Some(tv) = child.downcast_ref::<TextView>() {
            if tv.widget_name().as_deref() == Some(name) {
                result = Some(tv.clone());
            }
        }
        if result.is_none() {
            if let Some(found) = find_text_view_by_name(child, name) {
                result = Some(found);
            }
        }
    });
    result
}

fn find_button_by_name(parent: &Widget, name: &str) -> Option<Button> {
    let mut result: Option<Button> = None;
    iter_children(parent, |child| {
        if let Some(btn) = child.downcast_ref::<Button>() {
            if btn.widget_name().as_deref() == Some(name) {
                result = Some(btn.clone());
            }
        }
        if result.is_none() {
            if let Some(found) = find_button_by_name(child, name) {
                result = Some(found);
            }
        }
    });
    result
}

pub struct MainWindow {
    state: AppState,
}

impl MainWindow {
    pub fn new(
        window: ApplicationWindow,
        db: Database,
        crypto: Option<Crypto>,
        clipboard: ClipboardManager,
        hotkey_manager: HotkeyManager,
        extension_server: ExtensionServer,
        sync_manager: SyncManager,
    ) -> Self {
        let state = AppState::new(
            db,
            crypto,
            clipboard,
            window,
            hotkey_manager,
            extension_server,
            sync_manager,
        );
        let state_clone = state.clone();
        
        Self::build_ui(&state);
        
        MainWindow { state: state_clone }
    }
    
    fn build_ui(state: &AppState) {
        let window = &state.window;
        window.set_title(Some("密码管理器"));
        window.set_default_size(800, 600);
        
        let vbox = gtk::Box::new(gtk::Orientation::Vertical, 0);
        
        let header_bar = HeaderBar::new();
        header_bar.set_title(Some("密码管理器"));
        header_bar.set_show_close_button(true);
        
        let search_entry = Entry::new();
        search_entry.set_placeholder_text(Some("搜索..."));
        search_entry.set_icon_from_icon_name(
            gtk::EntryIconPosition::Primary,
            Some("edit-find-symbolic"),
        );
        
        let list_box = ListBox::new();
        list_box.add_css_class("sidebar-list");
        
        let detail_stack = Stack::new();
        detail_stack.add_titled(
            &Self::create_empty_view(),
            Some("empty"),
            "空视图",
        );
        
        let state_clone = state.clone();
        let list_clone = list_box.clone();
        search_entry.connect_changed(move |entry| {
            let query = entry.text().to_string();
            *state_clone.current_query.borrow_mut() = query.clone();
            Self::refresh_list(&list_clone, &state_clone, &query);
        });
        
        header_bar.pack_start(&search_entry);
        
        let add_btn = Button::with_label("添加");
        add_btn.set_icon_name(Some("list-add-symbolic"));
        
        let state_clone = state.clone();
        let list_clone = list_box.clone();
        add_btn.connect_clicked(move |_| {
            Self::show_add_dialog(&state_clone, &list_clone);
        });
        header_bar.pack_end(&add_btn);
        
        let change_pw_btn = Button::with_label("更改密码");
        change_pw_btn.set_icon_name(Some("dialog-password-symbolic"));
        
        let state_clone = state.clone();
        change_pw_btn.connect_clicked(move |_| {
            Self::show_change_password_dialog(&state_clone);
        });
        header_bar.pack_end(&change_pw_btn);
        
        let sync_btn = Button::with_label("同步");
        sync_btn.set_icon_name(Some("view-refresh-symbolic"));
        
        let state_clone = state.clone();
        sync_btn.connect_clicked(move |_| {
            Self::sync_now(&state_clone);
        });
        header_bar.pack_end(&sync_btn);
        
        let settings_btn = Button::with_label("设置");
        settings_btn.set_icon_name(Some("preferences-system-symbolic"));
        
        let state_clone = state.clone();
        settings_btn.connect_clicked(move |_| {
            Self::show_settings_dialog(&state_clone);
        });
        header_bar.pack_end(&settings_btn);
        
        window.set_titlebar(Some(&header_bar));
        vbox.append(&header_bar);
        
        let paned = Paned::new(gtk::Orientation::Horizontal);
        
        let scrolled = ScrolledWindow::new();
        scrolled.set_min_content_width(200);
        scrolled.set_vexpand(true);
        scrolled.set_child(Some(&list_box));
        
        paned.set_start_child(Some(&scrolled));
        
        let detail_view = Self::create_detail_view();
        detail_stack.add_titled(
            &detail_view,
            Some("detail"),
            "详情",
        );
        detail_stack.set_visible_child_name("empty");
        
        paned.set_end_child(Some(&detail_stack));
        
        vbox.append(&paned);
        
        window.set_child(Some(&vbox));
        
        Self::refresh_list(&list_box, state, "");
        
        let state_clone = state.clone();
        let stack_clone = detail_stack.clone();
        let detail_view_clone = detail_view.clone();
        list_box.connect_row_activated(move |_, row| {
            if let Some(row) = row {
                if let Some(id_str) = row.widget_name() {
                    if let Ok(id) = id_str.parse::<i64>() {
                        *state_clone.selected_id.borrow_mut() = Some(id);
                        Self::show_detail(&state_clone, &stack_clone, &detail_view_clone, id);
                    }
                }
            }
        });
        
        Self::setup_detail_buttons(state, &detail_view, &detail_stack, &list_box);
    }
    
    fn create_empty_view() -> gtk::Box {
        let vbox = gtk::Box::new(gtk::Orientation::Vertical, 12);
        vbox.set_halign(gtk::Align::Center);
        vbox.set_valign(gtk::Align::Center);
        vbox.set_margin_top(48);
        vbox.set_margin_bottom(48);
        vbox.set_margin_start(24);
        vbox.set_margin_end(24);
        
        let icon = gtk::Image::from_icon_name(Some("dialog-password-symbolic"));
        icon.set_pixel_size(64);
        icon.add_css_class("dim-label");
        
        let title = Label::new(Some("选择或添加密码"));
        title.add_css_class("title-2");
        
        let subtitle = Label::new(Some("从左侧选择一条记录，或点击添加按钮创建新记录"));
        subtitle.add_css_class("dim-label");
        subtitle.set_wrap(true);
        subtitle.set_justify(gtk::Justification::Center);
        
        vbox.append(&icon);
        vbox.append(&title);
        vbox.append(&subtitle);
        
        vbox
    }
    
    fn create_detail_view() -> gtk::Box {
        let vbox = gtk::Box::new(gtk::Orientation::Vertical, 12);
        vbox.set_margin_top(24);
        vbox.set_margin_bottom(24);
        vbox.set_margin_start(24);
        vbox.set_margin_end(24);
        
        let grid = Grid::new();
        grid.set_row_spacing(12);
        grid.set_column_spacing(12);
        
        let service_label = Label::new(Some("服务:"));
        service_label.set_halign(gtk::Align::Start);
        grid.attach(&service_label, 0, 0, 1, 1);
        
        let service_entry = Entry::new();
        service_entry.set_widget_name("detail-service");
        service_entry.set_hexpand(true);
        grid.attach(&service_entry, 1, 0, 2, 1);
        
        let username_label = Label::new(Some("用户名:"));
        username_label.set_halign(gtk::Align::Start);
        grid.attach(&username_label, 0, 1, 1, 1);
        
        let username_entry = Entry::new();
        username_entry.set_widget_name("detail-username");
        username_entry.set_hexpand(true);
        grid.attach(&username_entry, 1, 1, 1, 1);
        
        let copy_username_btn = Button::with_label("复制");
        copy_username_btn.set_widget_name("copy-username-btn");
        grid.attach(&copy_username_btn, 2, 1, 1, 1);
        
        let password_label = Label::new(Some("密码:"));
        password_label.set_halign(gtk::Align::Start);
        grid.attach(&password_label, 0, 2, 1, 1);
        
        let password_entry = Entry::new();
        password_entry.set_widget_name("detail-password");
        password_entry.set_visibility(false);
        password_entry.set_hexpand(true);
        grid.attach(&password_entry, 1, 2, 1, 1);
        
        let password_actions = gtk::Box::new(gtk::Orientation::Horizontal, 6);
        
        let reveal_btn = Button::with_label("显示");
        reveal_btn.set_widget_name("reveal-password-btn");
        password_actions.append(&reveal_btn);
        
        let copy_password_btn = Button::with_label("复制");
        copy_password_btn.set_widget_name("copy-password-btn");
        password_actions.append(&copy_password_btn);
        
        let generate_btn = Button::with_label("生成");
        generate_btn.set_widget_name("generate-password-btn");
        password_actions.append(&generate_btn);
        
        grid.attach(&password_actions, 2, 2, 1, 1);
        
        let notes_label = Label::new(Some("备注:"));
        notes_label.set_halign(gtk::Align::Start);
        notes_label.set_valign(gtk::Align::Start);
        grid.attach(&notes_label, 0, 3, 1, 1);
        
        let notes_buffer = TextBuffer::new(None);
        let notes_view = TextView::with_buffer(&notes_buffer);
        notes_view.set_widget_name("detail-notes");
        notes_view.set_wrap_mode(gtk::WrapMode::Word);
        notes_view.set_size_request(-1, 100);
        
        let notes_scrolled = ScrolledWindow::new();
        notes_scrolled.set_child(Some(&notes_view));
        notes_scrolled.set_hexpand(true);
        notes_scrolled.set_vexpand(true);
        grid.attach(&notes_scrolled, 1, 3, 2, 1);
        
        vbox.append(&grid);
        
        let action_box = gtk::Box::new(gtk::Orientation::Horizontal, 12);
        action_box.set_halign(gtk::Align::End);
        action_box.set_margin_top(12);
        
        let delete_btn = Button::with_label("删除");
        delete_btn.set_widget_name("delete-btn");
        delete_btn.add_css_class("destructive-action");
        action_box.append(&delete_btn);
        
        let save_btn = Button::with_label("保存");
        save_btn.set_widget_name("save-btn");
        save_btn.add_css_class("suggested-action");
        action_box.append(&save_btn);
        
        vbox.append(&action_box);
        
        vbox
    }
    
    fn refresh_list(list_box: &ListBox, state: &AppState, query: &str) {
        let entries = if query.is_empty() {
            state.db.get_all_passwords().unwrap_or_default()
        } else {
            state.db.search_passwords(query).unwrap_or_default()
        };
        
        *state.entries.borrow_mut() = entries.clone();
        
        while let Some(row) = list_box.first_child() {
            list_box.remove(&row);
        }
        
        for entry in &entries {
            let row = ListBoxRow::new();
            row.set_widget_name(Some(&entry.id.to_string()));
            
            let row_vbox = gtk::Box::new(gtk::Orientation::Vertical, 4);
            row_vbox.set_margin_top(6);
            row_vbox.set_margin_bottom(6);
            row_vbox.set_margin_start(12);
            row_vbox.set_margin_end(12);
            
            let service_label = Label::new(Some(&entry.service));
            service_label.set_halign(gtk::Align::Start);
            service_label.add_css_class("caption-heading");
            
            let username_label = Label::new(Some(&entry.username));
            username_label.set_halign(gtk::Align::Start);
            username_label.add_css_class("caption");
            username_label.add_css_class("dim-label");
            
            row_vbox.append(&service_label);
            row_vbox.append(&username_label);
            
            row.set_child(Some(&row_vbox));
            list_box.append(&row);
        }
    }
    
    fn setup_detail_buttons(
        state: &AppState,
        detail_view: &gtk::Box,
        detail_stack: &Stack,
        list_box: &ListBox,
    ) {
        let state_clone = state.clone();
        let detail_view_clone = detail_view.clone();
        let stack_clone = detail_stack.clone();
        let list_clone = list_box.clone();
        
        if let Some(btn) = find_button_by_name(detail_view, "copy-username-btn") {
            let dv = detail_view_clone.clone();
            let s = state_clone.clone();
            btn.connect_clicked(move |_| {
                if let Some(entry) = find_entry_widget_by_name(&dv, "detail-username") {
                    s.clipboard.set_text_with_timeout(&entry.text(), 30);
                }
            });
        }
        
        if let Some(btn) = find_button_by_name(detail_view, "reveal-password-btn") {
            let dv = detail_view_clone.clone();
            btn.connect_clicked(move |b| {
                if let Some(entry) = find_entry_widget_by_name(&dv, "detail-password") {
                    let visible = entry.is_visible();
                    entry.set_visibility(!visible);
                    b.set_label(if visible { "显示" } else { "隐藏" });
                }
            });
        }
        
        if let Some(btn) = find_button_by_name(detail_view, "copy-password-btn") {
            let dv = detail_view_clone.clone();
            let s = state_clone.clone();
            btn.connect_clicked(move |_| {
                if let Some(entry) = find_entry_widget_by_name(&dv, "detail-password") {
                    s.clipboard.set_text_with_timeout(&entry.text(), 30);
                }
            });
        }
        
        if let Some(btn) = find_button_by_name(detail_view, "generate-password-btn") {
            let dv = detail_view_clone.clone();
            btn.connect_clicked(move |_| {
                if let Some(entry) = find_entry_widget_by_name(&dv, "detail-password") {
                    entry.set_text(&generate_password(16));
                }
            });
        }
        
        if let Some(btn) = find_button_by_name(detail_view, "save-btn") {
            let dv = detail_view_clone.clone();
            let s = state_clone.clone();
            let st = stack_clone.clone();
            let lb = list_clone.clone();
            btn.connect_clicked(move |_| {
                Self::save_current_entry(&s, &dv, &st, &lb);
            });
        }
        
        if let Some(btn) = find_button_by_name(detail_view, "delete-btn") {
            let s = state_clone.clone();
            let st = stack_clone.clone();
            let lb = list_clone.clone();
            btn.connect_clicked(move |_| {
                Self::delete_current_entry(&s, &st, &lb);
            });
        }
    }
    
    fn show_detail(state: &AppState, stack: &Stack, detail_view: &gtk::Box, id: i64) {
        let entry = {
            let entries = state.entries.borrow();
            entries.iter().find(|e| e.id == id).cloned()
        };
        
        if entry.is_none() {
            stack.set_visible_child_name("empty");
            return;
        }
        
        let entry = entry.unwrap();
        stack.set_visible_child_name("detail");
        
        if let Some(e) = find_entry_widget_by_name(detail_view, "detail-service") {
            e.set_text(&entry.service);
        }
        if let Some(e) = find_entry_widget_by_name(detail_view, "detail-username") {
            e.set_text(&entry.username);
        }
        if let Some(e) = find_entry_widget_by_name(detail_view, "detail-password") {
            if let Some(crypto) = &state.crypto {
                if let Ok(password) = crypto.decrypt(&entry.encrypted_password) {
                    e.set_text(&password);
                    e.set_visibility(false);
                }
            }
        }
        if let Some(tv) = find_text_view_by_name(detail_view, "detail-notes") {
            if let Some(buffer) = tv.buffer() {
                buffer.set_text(entry.notes.as_deref().unwrap_or(""));
            }
        }
        
        if let Some(btn) = find_button_by_name(detail_view, "reveal-password-btn") {
            btn.set_label("显示");
        }
    }
    
    fn show_add_dialog(state: &AppState, list_box: &ListBox) {
        let dialog = Dialog::new();
        dialog.set_transient_for(Some(&*state.window));
        dialog.set_title(Some("添加密码"));
        dialog.set_modal(true);
        dialog.add_button("取消", ResponseType::Cancel);
        dialog.add_button("保存", ResponseType::Ok);
        
        let content_area = dialog.content_area();
        content_area.set_margin_top(12);
        content_area.set_margin_bottom(12);
        content_area.set_margin_start(12);
        content_area.set_margin_end(12);
        content_area.set_spacing(12);
        
        let grid = Grid::new();
        grid.set_row_spacing(12);
        grid.set_column_spacing(12);
        
        let service_label = Label::new(Some("服务:"));
        service_label.set_halign(gtk::Align::Start);
        grid.attach(&service_label, 0, 0, 1, 1);
        
        let service_entry = Entry::new();
        service_entry.set_widget_name("add-service");
        service_entry.set_hexpand(true);
        grid.attach(&service_entry, 1, 0, 1, 1);
        
        let username_label = Label::new(Some("用户名:"));
        username_label.set_halign(gtk::Align::Start);
        grid.attach(&username_label, 0, 1, 1, 1);
        
        let username_entry = Entry::new();
        username_entry.set_widget_name("add-username");
        username_entry.set_hexpand(true);
        grid.attach(&username_entry, 1, 1, 1, 1);
        
        let password_label = Label::new(Some("密码:"));
        password_label.set_halign(gtk::Align::Start);
        grid.attach(&password_label, 0, 2, 1, 1);
        
        let password_entry = Entry::new();
        password_entry.set_widget_name("add-password");
        password_entry.set_visibility(false);
        password_entry.set_hexpand(true);
        grid.attach(&password_entry, 1, 2, 1, 1);
        
        let generate_btn = Button::with_label("生成");
        let password_entry_clone = password_entry.clone();
        generate_btn.connect_clicked(move |_| {
            password_entry_clone.set_text(&generate_password(16));
        });
        grid.attach(&generate_btn, 2, 2, 1, 1);
        
        let notes_label = Label::new(Some("备注:"));
        notes_label.set_halign(gtk::Align::Start);
        notes_label.set_valign(gtk::Align::Start);
        grid.attach(&notes_label, 0, 3, 1, 1);
        
        let notes_buffer = TextBuffer::new(None);
        let notes_view = TextView::with_buffer(&notes_buffer);
        notes_view.set_wrap_mode(gtk::WrapMode::Word);
        notes_view.set_size_request(-1, 80);
        
        let notes_scrolled = ScrolledWindow::new();
        notes_scrolled.set_child(Some(&notes_view));
        notes_scrolled.set_hexpand(true);
        grid.attach(&notes_scrolled, 1, 3, 2, 1);
        
        content_area.append(&grid);
        
        let state_clone = state.clone();
        let list_clone = list_box.clone();
        dialog.connect_response(move |dialog, response| {
            if response == ResponseType::Ok {
                let service = service_entry.text().to_string();
                let username = username_entry.text().to_string();
                let password = password_entry.text().to_string();
                
                let notes = {
                    let start = notes_buffer.start_iter();
                    let end = notes_buffer.end_iter();
                    let text = notes_buffer.text(&start, &end, false);
                    if text.is_empty() { None } else { Some(text.to_string()) }
                };
                
                if service.is_empty() || username.is_empty() || password.is_empty() {
                    let error_dialog = MessageDialog::new(
                        Some(dialog),
                        gtk::DialogFlags::MODAL,
                        MessageType::Error,
                        ButtonsType::Ok,
                        "请填写所有必填字段",
                    );
                    error_dialog.run();
                    error_dialog.close();
                } else {
                    if let Some(crypto) = &state_clone.crypto {
                        if let Ok(encrypted) = crypto.encrypt(&password) {
                            if state_clone.db.add_password(&service, &username, &encrypted, notes.as_deref()).is_ok() {
                                let query = state_clone.current_query.borrow().clone();
                                Self::refresh_list(&list_clone, &state_clone, &query);
                            }
                        }
                    }
                }
            }
            dialog.close();
        });
        
        dialog.show();
    }
    
    fn show_change_password_dialog(state: &AppState) {
        if state.crypto.is_none() {
            return;
        }
        
        let dialog = Dialog::new();
        dialog.set_transient_for(Some(&*state.window));
        dialog.set_title(Some("更改主密码"));
        dialog.set_modal(true);
        dialog.set_default_size(400, -1);
        dialog.set_resizable(false);
        
        let content_area = dialog.content_area();
        content_area.set_margin_top(24);
        content_area.set_margin_bottom(24);
        content_area.set_margin_start(24);
        content_area.set_margin_end(24);
        content_area.set_spacing(12);
        
        let title_label = Label::new(Some("更改主密码"));
        title_label.add_css_class("title-2");
        content_area.append(&title_label);
        
        let hint_label = Label::new(Some("输入当前密码和新密码以更改主密钥。所有密码将使用新密钥重新加密。"));
        hint_label.add_css_class("dim-label");
        hint_label.set_wrap(true);
        content_area.append(&hint_label);
        
        let old_password_entry = Entry::new();
        old_password_entry.set_placeholder_text(Some("当前密码"));
        old_password_entry.set_visibility(false);
        old_password_entry.set_input_purpose(gtk::InputPurpose::Password);
        content_area.append(&old_password_entry);
        
        let new_password_entry = Entry::new();
        new_password_entry.set_placeholder_text(Some("新密码"));
        new_password_entry.set_visibility(false);
        new_password_entry.set_input_purpose(gtk::InputPurpose::Password);
        content_area.append(&new_password_entry);
        
        let confirm_password_entry = Entry::new();
        confirm_password_entry.set_placeholder_text(Some("确认新密码"));
        confirm_password_entry.set_visibility(false);
        confirm_password_entry.set_input_purpose(gtk::InputPurpose::Password);
        content_area.append(&confirm_password_entry);
        
        let error_label = Label::new(None);
        error_label.add_css_class("error");
        content_area.append(&error_label);
        
        dialog.add_button("取消", ResponseType::Cancel);
        let ok_btn = dialog.add_button("确认更改", ResponseType::Ok);
        ok_btn.add_css_class("suggested-action");
        
        let old_password_clone = old_password_entry.clone();
        let new_password_clone = new_password_entry.clone();
        let confirm_clone = confirm_password_entry.clone();
        let dialog_clone = dialog.clone();
        
        old_password_entry.connect_activate(move |_| {
            new_password_clone.grab_focus();
        });
        
        let new_password_clone2 = new_password_entry.clone();
        let confirm_clone2 = confirm_password_entry.clone();
        new_password_entry.connect_activate(move |_| {
            confirm_clone2.grab_focus();
        });
        
        confirm_password_entry.connect_activate(move |_| {
            dialog_clone.response(ResponseType::Ok);
        });
        
        let state_clone = state.clone();
        dialog.connect_response(move |dialog, response| {
            if response == ResponseType::Ok {
                let old_password = old_password_clone.text().to_string();
                let new_password = new_password_clone.text().to_string();
                let confirm_pw = confirm_clone.text().to_string();
                
                if old_password.is_empty() || new_password.is_empty() || confirm_pw.is_empty() {
                    error_label.set_text("请填写所有字段");
                    return;
                }
                
                if new_password != confirm_pw {
                    error_label.set_text("新密码不匹配");
                    return;
                }
                
                if new_password.len() < 6 {
                    error_label.set_text("新密码至少需要6个字符");
                    return;
                }
                
                let current_salt = match state_clone.db.get_salt() {
                    Ok(Some(s)) => s,
                    _ => {
                        error_label.set_text("读取设置失败");
                        return;
                    }
                };
                
                let old_crypto = match Crypto::new(&old_password, &current_salt) {
                    Ok(c) => c,
                    Err(_) => {
                        error_label.set_text("当前密码错误");
                        return;
                    }
                };
                
                let test_entries = state_clone.db.get_all_passwords().unwrap_or_default();
                if let Some(entry) = test_entries.first() {
                    if old_crypto.decrypt(&entry.encrypted_password).is_err() {
                        error_label.set_text("当前密码错误");
                        return;
                    }
                }
                
                let new_salt = match Crypto::generate_salt() {
                    Ok(s) => s,
                    Err(_) => {
                        error_label.set_text("生成加密盐失败");
                        return;
                    }
                };
                
                let new_crypto = match Crypto::new(&new_password, &new_salt) {
                    Ok(c) => c,
                    Err(_) => {
                        error_label.set_text("初始化新密钥失败");
                        return;
                    }
                };
                
                let all_entries = match state_clone.db.get_all_passwords() {
                    Ok(e) => e,
                    Err(_) => {
                        error_label.set_text("读取密码失败");
                        return;
                    }
                };
                
                let mut reencrypted = Vec::new();
                for entry in &all_entries {
                    let plaintext = match old_crypto.decrypt(&entry.encrypted_password) {
                        Ok(p) => p,
                        Err(_) => {
                            error_label.set_text("解密密码失败，主密码可能错误");
                            return;
                        }
                    };
                    let encrypted = match new_crypto.encrypt(&plaintext) {
                        Ok(e) => e,
                        Err(_) => {
                            error_label.set_text("加密密码失败");
                            return;
                        }
                    };
                    reencrypted.push((entry.id, encrypted));
                }
                
                for (id, encrypted) in &reencrypted {
                    if state_clone.db.update_encrypted_password(*id, encrypted).is_err() {
                        error_label.set_text("更新数据库失败");
                        return;
                    }
                }
                
                if state_clone.db.set_salt(&new_salt).is_err() {
                    error_label.set_text("保存新盐值失败");
                    return;
                }
                
                if let Some(cell) = &state_clone.crypto {
                    let mut crypto_mut = (*cell).clone();
                    drop(crypto_mut);
                }
                
                let success_dialog = MessageDialog::new(
                    Some(dialog),
                    gtk::DialogFlags::MODAL,
                    MessageType::Info,
                    ButtonsType::Ok,
                    "主密码已成功更改",
                );
                success_dialog.run();
                success_dialog.close();
                
                dialog.close();
                
                let quit_dialog = MessageDialog::new(
                    Some(&*state_clone.window),
                    gtk::DialogFlags::MODAL,
                    MessageType::Info,
                    ButtonsType::Ok,
                    "为了安全起见，程序将退出。请使用新密码重新登录。",
                );
                quit_dialog.run();
                quit_dialog.close();
                
                if let Some(app) = state_clone.window.application() {
                    app.quit();
                }
            } else {
                dialog.close();
            }
        });
        
        dialog.show();
        old_password_entry.grab_focus();
    }
    
    fn get_detail_values(detail_view: &gtk::Box) -> (String, String, String, String) {
        let service = find_entry_widget_by_name(detail_view, "detail-service")
            .map(|e| e.text().to_string())
            .unwrap_or_default();
        let username = find_entry_widget_by_name(detail_view, "detail-username")
            .map(|e| e.text().to_string())
            .unwrap_or_default();
        let password = find_entry_widget_by_name(detail_view, "detail-password")
            .map(|e| e.text().to_string())
            .unwrap_or_default();
        let notes = find_text_view_by_name(detail_view, "detail-notes")
            .and_then(|tv| tv.buffer())
            .map(|buf| {
                let start = buf.start_iter();
                let end = buf.end_iter();
                buf.text(&start, &end, false).to_string()
            })
            .unwrap_or_default();
        
        (service, username, password, notes)
    }
    
    fn save_current_entry(state: &AppState, detail_view: &gtk::Box, stack: &Stack, list_box: &ListBox) {
        let (service, username, password, notes) = Self::get_detail_values(detail_view);
        
        if service.is_empty() || username.is_empty() || password.is_empty() {
            let error_dialog = MessageDialog::new(
                Some(&*state.window),
                gtk::DialogFlags::MODAL,
                MessageType::Error,
                ButtonsType::Ok,
                "请填写所有必填字段",
            );
            error_dialog.run();
            error_dialog.close();
            return;
        }
        
        let selected_id = *state.selected_id.borrow();
        if let Some(id) = selected_id {
            if let Some(crypto) = &state.crypto {
                if let Ok(encrypted) = crypto.encrypt(&password) {
                    let notes_opt = if notes.is_empty() { None } else { Some(notes.as_str()) };
                    if state.db.update_password(id, &service, &username, &encrypted, notes_opt).is_ok() {
                        let query = state.current_query.borrow().clone();
                        Self::refresh_list(list_box, state, &query);
                        
                        let success_dialog = MessageDialog::new(
                            Some(&*state.window),
                            gtk::DialogFlags::MODAL,
                            MessageType::Info,
                            ButtonsType::Ok,
                            "密码已保存",
                        );
                        success_dialog.run();
                        success_dialog.close();
                    }
                }
            }
        }
    }
    
    fn delete_current_entry(state: &AppState, stack: &Stack, list_box: &ListBox) {
        let selected_id = *state.selected_id.borrow();
        if let Some(id) = selected_id {
            let confirm_dialog = MessageDialog::new(
                Some(&*state.window),
                gtk::DialogFlags::MODAL,
                MessageType::Question,
                ButtonsType::YesNo,
                "确定要删除这条密码记录吗？",
            );
            
            let response = confirm_dialog.run();
            confirm_dialog.close();
            
            if response == ResponseType::Yes {
                if state.db.delete_password(id).is_ok() {
                    let query = state.current_query.borrow().clone();
                    *state.selected_id.borrow_mut() = None;
                    stack.set_visible_child_name("empty");
                    Self::refresh_list(list_box, state, &query);
                }
            }
        }
    }
    
    pub fn show(&self) {
        self.state.window.show();
    }

    fn sync_now(state: &AppState) {
        let mut sync_manager = state.sync_manager.lock().unwrap();
        
        if state.crypto.is_none() {
            let dialog = MessageDialog::new(
                Some(&*state.window),
                gtk::DialogFlags::MODAL,
                MessageType::Error,
                ButtonsType::Ok,
                "密码库未解锁",
            );
            dialog.run();
            dialog.close();
            return;
        }

        let crypto = state.crypto.clone().unwrap();
        sync_manager.set_crypto(crypto);
        sync_manager.set_db(state.db.clone());

        match sync_manager.sync_now() {
            Ok(_) => {
                let dialog = MessageDialog::new(
                    Some(&*state.window),
                    gtk::DialogFlags::MODAL,
                    MessageType::Info,
                    ButtonsType::Ok,
                    "同步成功",
                );
                dialog.run();
                dialog.close();
            }
            Err(e) => {
                let dialog = MessageDialog::new(
                    Some(&*state.window),
                    gtk::DialogFlags::MODAL,
                    MessageType::Error,
                    ButtonsType::Ok,
                    &format!("同步失败: {}", e),
                );
                dialog.run();
                dialog.close();
            }
        }
    }

    fn show_settings_dialog(state: &AppState) {
        let dialog = Dialog::new();
        dialog.set_transient_for(Some(&*state.window));
        dialog.set_title(Some("设置"));
        dialog.set_modal(true);
        dialog.set_default_size(500, 400);

        let content_area = dialog.content_area();
        content_area.set_margin_top(12);
        content_area.set_margin_bottom(12);
        content_area.set_margin_start(12);
        content_area.set_margin_end(12);
        content_area.set_spacing(12);

        let stack = Stack::new();
        let sidebar = gtk::StackSidebar::new();
        sidebar.set_stack(&stack);

        let hbox = gtk::Box::new(gtk::Orientation::Horizontal, 0);
        hbox.append(&sidebar);
        hbox.append(&stack);
        hbox.set_hexpand(true);
        hbox.set_vexpand(true);
        content_area.append(&hbox);

        stack.add_titled(
            &Self::create_sync_settings_page(state),
            Some("sync"),
            "同步设置",
        );
        stack.add_titled(
            &Self::create_hotkey_settings_page(state),
            Some("hotkey"),
            "快捷键",
        );
        stack.add_titled(
            &Self::create_extension_settings_page(state),
            Some("extension"),
            "浏览器扩展",
        );

        dialog.add_button("关闭", ResponseType::Close);

        dialog.connect_response(|dialog, _| {
            dialog.close();
        });

        dialog.show();
    }

    fn create_sync_settings_page(state: &AppState) -> gtk::Box {
        let vbox = gtk::Box::new(gtk::Orientation::Vertical, 12);
        vbox.set_margin_top(12);
        vbox.set_margin_bottom(12);
        vbox.set_margin_start(12);
        vbox.set_margin_end(12);

        let config = state.sync_manager.lock().unwrap().get_config();

        let enabled_check = CheckButton::with_label("启用同步");
        enabled_check.set_active(config.enabled);

        let type_label = Label::new(Some("同步类型:"));
        let type_combo = ComboBoxText::new();
        type_combo.append_text("本地文件");
        type_combo.append_text("WebDAV");
        type_combo.append_text("自定义 HTTP");
        type_combo.set_active(match config.sync_type {
            SyncType::LocalFile => Some(0),
            SyncType::WebDav => Some(1),
            SyncType::CustomHttp => Some(2),
        });

        let path_label = Label::new(Some("本地路径:"));
        let path_entry = Entry::new();
        path_entry.set_text(config.local_path.as_deref().unwrap_or(""));
        path_entry.set_placeholder_text(Some("例如: C:\\Users\\...\\sync.pm-sync"));

        let auto_check = CheckButton::with_label("自动同步");
        auto_check.set_active(config.auto_sync);

        let interval_label = Label::new(Some("同步间隔 (秒):"));
        let interval_entry = Entry::new();
        interval_entry.set_text(&config.sync_interval_secs.to_string());

        let sync_now_btn = Button::with_label("立即同步");

        vbox.append(&enabled_check);
        vbox.append(&type_label);
        vbox.append(&type_combo);
        vbox.append(&path_label);
        vbox.append(&path_entry);
        vbox.append(&auto_check);
        vbox.append(&interval_label);
        vbox.append(&sync_now_btn);

        let state_clone = state.clone();
        sync_now_btn.connect_clicked(move |_| {
            Self::sync_now(&state_clone);
        });

        vbox
    }

    fn create_hotkey_settings_page(state: &AppState) -> gtk::Box {
        let vbox = gtk::Box::new(gtk::Orientation::Vertical, 12);
        vbox.set_margin_top(12);
        vbox.set_margin_bottom(12);
        vbox.set_margin_start(12);
        vbox.set_margin_end(12);

        let title = Label::new(Some("全局快捷键"));
        title.add_css_class("title-2");
        vbox.append(&title);

        let desc = Label::new(Some("使用快捷键 (Ctrl+Shift+L 可以显示/隐藏窗口"));
        desc.add_css_class("dim-label");
        vbox.append(&desc);

        let status_label = Label::new(Some("状态: 未注册"));
        status_label.add_css_class("dim-label");
        vbox.append(&status_label);

        let register_btn = Button::with_label("启用快捷键");
        let unregister_btn = Button::with_label("禁用快捷键");

        {
            let is_registered = state.hotkey_manager.lock().unwrap().is_registered();
            if is_registered {
                status_label.set_text("状态: 已注册");
            } else {
                status_label.set_text("状态: 未注册");
            }
        }

        let state_clone = state.clone();
        let status_clone = status_label.clone();
        let register_clicked = move |_| {
            let mut hotkey = state_clone.hotkey_manager.lock().unwrap();
            let window_clone = state_clone.window.clone();

            hotkey.set_callback(move || {
                if window_clone.is_visible() {
                    window_clone.hide();
                } else {
                    window_clone.present();
                }
            });

            match hotkey.register_show_window_hotkey() {
                Ok(_) => {
                    status_clone.set_text("状态: 已注册");
                }
                Err(_) => {
                    status_clone.set_text("状态: 注册失败");
                }
            }
        };
        register_btn.connect_clicked(register_clicked);

        let state_clone = state.clone();
        let status_clone = status_label.clone();
        unregister_btn.connect_clicked(move |_| {
            let mut hotkey = state_clone.hotkey_manager.lock().unwrap();
            let _ = hotkey.unregister_all();
            status_clone.set_text("状态: 未注册");
        });

        vbox.append(&register_btn);
        vbox.append(&unregister_btn);

        vbox
    }

    fn create_extension_settings_page(state: &AppState) -> gtk::Box {
        use crate::browser_extension::DEFAULT_PORT;

        let vbox = gtk::Box::new(gtk::Orientation::Vertical, 12);
        vbox.set_margin_top(12);
        vbox.set_margin_bottom(12);
        vbox.set_margin_start(12);
        vbox.set_margin_end(12);

        let title = Label::new(Some("浏览器扩展"));
        title.add_css_class("title-2");
        vbox.append(&title);

        let desc = Label::new(Some("浏览器扩展需要连接到本地 WebSocket 服务器进行密码自动填充。"));
        desc.add_css_class("dim-label");
        desc.set_wrap(true);
        vbox.append(&desc);

        let port_label = Label::new(&format!("监听端口: {}", DEFAULT_PORT));
        vbox.append(&port_label);

        let status_label = Label::new(Some("状态: 未运行"));
        status_label.add_css_class("dim-label");
        vbox.append(&status_label);

        let start_btn = Button::with_label("启动服务器");
        let stop_btn = Button::with_label("停止服务器");

        {
            let is_running = state.extension_server.lock().unwrap().is_running();
            if is_running {
                status_label.set_text("状态: 运行中");
            } else {
                status_label.set_text("状态: 未运行");
            }
        }

        let state_clone = state.clone();
        let status_clone = status_label.clone();
        start_btn.connect_clicked(move |_| {
            let mut server = state_clone.extension_server.lock().unwrap();

            if state_clone.crypto.is_some() {
                server.set_db(state_clone.db.clone());
                server.set_crypto(state_clone.crypto.clone().unwrap());
            }

            match server.start() {
                Ok(_) => {
                    status_clone.set_text("状态: 运行中");
                }
                Err(_) => {
                    status_clone.set_text("状态: 启动失败");
                }
            }
        });

        let state_clone = state.clone();
        let status_clone = status_label.clone();
        stop_btn.connect_clicked(move |_| {
            let mut server = state_clone.extension_server.lock().unwrap();
            server.stop();
            status_clone.set_text("状态: 未运行");
        });

        vbox.append(&start_btn);
        vbox.append(&stop_btn);

        vbox
    }
}

fn generate_password(length: usize) -> String {
    use rand::Rng;
    let chars = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=";
    let mut rng = rand::thread_rng();
    
    (0..length)
        .map(|_| {
            let idx = rng.gen_range(0..chars.len());
            chars[idx] as char
        })
        .collect()
}

