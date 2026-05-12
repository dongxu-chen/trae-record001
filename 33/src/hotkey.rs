use global_hotkey::{
    hotkey::{Code, HotKey, Modifiers},
    GlobalHotKeyManager, HotKeyEvent,
};
use std::sync::{
    atomic::{AtomicBool, Ordering},
    mpsc, Arc, Mutex,
};
use std::thread;

pub type HotKeyCallback = Box<dyn Fn() + Send + Sync + 'static>;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ActionType {
    ShowWindow,
    SearchPassword,
    QuickFill,
}

pub struct HotkeyManager {
    manager: Option<Arc<Mutex<GlobalHotKeyManager>>>,
    callback: Arc<Mutex<Option<HotKeyCallback>>>,
    registered: Arc<AtomicBool>,
    sender: Option<mpsc::Sender<()>>,
}

impl HotkeyManager {
    pub fn new() -> Self {
        HotkeyManager {
            manager: None,
            callback: Arc::new(Mutex::new(None)),
            registered: Arc::new(AtomicBool::new(false)),
            sender: None,
        }
    }

    pub fn set_callback<F>(&mut self, callback: F)
    where
        F: Fn() + Send + Sync + 'static,
    {
        *self.callback.lock().unwrap() = Some(Box::new(callback));
    }

    pub fn register_show_window_hotkey(&mut self) -> Result<(), HotKeyError> {
        let hotkey = HotKey::new(Some(Modifiers::CONTROL | Modifiers::SHIFT), Code::KeyL);
        self.register_hotkey(hotkey)
    }

    pub fn register_custom_hotkey(
        &mut self,
        modifiers: Modifiers,
        code: Code,
    ) -> Result<(), HotKeyError> {
        let hotkey = HotKey::new(Some(modifiers), code);
        self.register_hotkey(hotkey)
    }

    fn register_hotkey(&mut self, hotkey: HotKey) -> Result<(), HotKeyError> {
        self.unregister_all()?;

        let manager = GlobalHotKeyManager::new().map_err(|_| HotKeyError::InitFailed)?;
        manager.register(hotkey).map_err(|_| HotKeyError::RegisterFailed)?;

        let (sender, receiver) = mpsc::channel();
        let callback_clone = self.callback.clone();
        let registered_clone = self.registered.clone();
        registered_clone.store(true, Ordering::SeqCst);

        let manager_arc = Arc::new(Mutex::new(manager));
        self.manager = Some(manager_arc.clone());
        self.sender = Some(sender);

        thread::spawn(move || {
            while registered_clone.load(Ordering::SeqCst) {
                if let Ok(event) = receiver.try_recv() {
                    let _ = event;
                    break;
                }

                if let Ok(event) = HotKeyEvent::recv_timeout(std::time::Duration::from_millis(100))
                {
                    if event.state == global_hotkey::HotKeyState::Pressed {
                        if let Some(ref cb) = *callback_clone.lock().unwrap() {
                            cb();
                        }
                    }
                }
            }

            if let Ok(mgr) = manager_arc.lock() {
                let _ = mgr.unregister(hotkey);
            }
        });

        Ok(())
    }

    pub fn unregister_all(&mut self) -> Result<(), HotKeyError> {
        self.registered.store(false, Ordering::SeqCst);

        if let Some(sender) = self.sender.take() {
            let _ = sender.send(());
        }

        if let Some(ref manager) = self.manager {
            if let Ok(mgr) = manager.lock() {
                for hotkey in mgr.list() {
                    let _ = mgr.unregister(hotkey);
                }
            }
        }

        self.manager = None;
        Ok(())
    }

    pub fn is_registered(&self) -> bool {
        self.registered.load(Ordering::SeqCst)
    }
}

impl Default for HotkeyManager {
    fn default() -> Self {
        Self::new()
    }
}

impl Drop for HotkeyManager {
    fn drop(&mut self) {
        let _ = self.unregister_all();
    }
}

#[derive(Debug)]
pub enum HotKeyError {
    InitFailed,
    RegisterFailed,
    UnregisterFailed,
}

impl std::fmt::Display for HotKeyError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            HotKeyError::InitFailed => write!(f, "Failed to initialize hotkey manager"),
            HotKeyError::RegisterFailed => write!(f, "Failed to register hotkey"),
            HotKeyError::UnregisterFailed => write!(f, "Failed to unregister hotkey"),
        }
    }
}

impl std::error::Error for HotKeyError {}

