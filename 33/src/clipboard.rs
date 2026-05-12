use glib::ControlFlow;
use gtk::prelude::*;
use std::sync::{
    atomic::{AtomicU64, Ordering},
    Arc,
};
use std::time::Duration;

#[derive(Clone)]
pub struct ClipboardManager {
    clipboard: gtk::gdk::Clipboard,
    copy_counter: Arc<AtomicU64>,
}

impl ClipboardManager {
    pub fn new(display: &gtk::gdk::Display) -> Self {
        let clipboard = display.clipboard();
        ClipboardManager {
            clipboard,
            copy_counter: Arc::new(AtomicU64::new(0)),
        }
    }

    pub fn set_text_with_timeout(&self, text: &str, timeout_secs: u64) {
        self.clipboard.set_text(text);

        let counter_clone = self.copy_counter.clone();
        let clipboard_clone = self.clipboard.clone();
        let my_count = counter_clone.fetch_add(1, Ordering::SeqCst) + 1;

        glib::timeout_add_local(
            Duration::from_secs(timeout_secs),
            move || {
                if counter_clone.load(Ordering::SeqCst) == my_count {
                    clipboard_clone.set_text("");
                }
                ControlFlow::Break
            },
        );
    }

    pub fn set_text(&self, text: &str) {
        self.clipboard.set_text(text);
        self.copy_counter.fetch_add(1, Ordering::SeqCst);
    }

    pub fn clear(&self) {
        self.clipboard.set_text("");
        self.copy_counter.fetch_add(1, Ordering::SeqCst);
    }
}

