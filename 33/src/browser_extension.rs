use crate::crypto::Crypto;
use crate::db::{Database, PasswordEntry};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::thread;
use tokio::net::{TcpListener, TcpStream};
use tokio::sync::{broadcast, mpsc};
use tungstenite::protocol::Message;

pub const DEFAULT_PORT: u16 = 48765;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ExtensionMessage {
    Ping { id: u64 },
    Pong { id: u64 },
    ListServices { id: u64 },
    ListServicesResponse { id: u64, services: Vec<String> },
    GetPassword { id: u64, service: String },
    GetPasswordResponse { id: u64, username: String, password: String },
    Search { id: u64, query: String },
    SearchResponse { id: u64, results: Vec<SearchResult> },
    AutofillRequest { id: u64, url: String },
    AutofillApproval { id: u64, entry_id: i64 },
    Error { id: u64, message: String },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub id: i64,
    pub service: String,
    pub username: String,
}

#[derive(Debug, Clone)]
pub enum ServerCommand {
    Stop,
    ApproveAutofill { request_id: u64, entry_id: i64 },
    DenyAutofill { request_id: u64 },
}

#[derive(Debug, Clone)]
pub enum ServerEvent {
    AutofillRequested {
        request_id: u64,
        url: String,
        suggested_entries: Vec<SearchResult>,
        sender: String,
    },
    ClientConnected {
        sender_id: String,
    },
    ClientDisconnected {
        sender_id: String,
    },
}

pub struct ExtensionServer {
    db: Option<Arc<Database>>,
    crypto: Option<Arc<Crypto>>,
    running: Arc<Mutex<bool>>,
    command_tx: Option<mpsc::Sender<ServerCommand>>,
    event_rx: Option<broadcast::Receiver<ServerEvent>>,
    port: u16,
}

impl ExtensionServer {
    pub fn new(port: u16) -> Self {
        ExtensionServer {
            db: None,
            crypto: None,
            running: Arc::new(Mutex::new(false)),
            command_tx: None,
            event_rx: None,
            port,
        }
    }

    pub fn set_db(&mut self, db: Arc<Database>) {
        self.db = Some(db);
    }

    pub fn set_crypto(&mut self, crypto: Arc<Crypto>) {
        self.crypto = Some(crypto);
    }

    pub fn start(&mut self) -> Result<(), ServerError> {
        if *self.running.lock().unwrap() {
            return Err(ServerError::AlreadyRunning);
        }

        let (command_tx, command_rx) = mpsc::channel(32);
        let (event_tx, event_rx) = broadcast::channel(32);

        *self.running.lock().unwrap() = true;
        self.command_tx = Some(command_tx);
        self.event_rx = Some(event_rx);

        let db = self.db.clone();
        let crypto = self.crypto.clone();
        let running = self.running.clone();
        let port = self.port;

        thread::spawn(move || {
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(async move {
                Self::run_server(port, db, crypto, running, command_rx, event_tx).await;
            });
        });

        Ok(())
    }

    pub fn stop(&mut self) {
        if let Some(tx) = &self.command_tx {
            let _ = tx.blocking_send(ServerCommand::Stop);
        }
        *self.running.lock().unwrap() = false;
    }

    pub fn is_running(&self) -> bool {
        *self.running.lock().unwrap()
    }

    pub fn receive_event(&mut self) -> Option<ServerEvent> {
        if let Some(rx) = &mut self.event_rx {
            rx.try_recv().ok()
        } else {
            None
        }
    }

    pub fn approve_autofill(&mut self, request_id: u64, entry_id: i64) {
        if let Some(tx) = &self.command_tx {
            let _ = tx.blocking_send(ServerCommand::ApproveAutofill {
                request_id,
                entry_id,
            });
        }
    }

    pub fn deny_autofill(&mut self, request_id: u64) {
        if let Some(tx) = &self.command_tx {
            let _ = tx.blocking_send(ServerCommand::DenyAutofill { request_id });
        }
    }

    async fn run_server(
        port: u16,
        db: Option<Arc<Database>>,
        crypto: Option<Arc<Crypto>>,
        running: Arc<Mutex<bool>>,
        mut command_rx: mpsc::Receiver<ServerCommand>,
        event_tx: broadcast::Sender<ServerEvent>,
    ) {
        let addr = format!("127.0.0.1:{}", port);
        let listener = match TcpListener::bind(&addr).await {
            Ok(l) => l,
            Err(_) => return,
        };

        let clients = Arc::new(Mutex::new(HashMap::new()));
        let autofill_requests = Arc::new(Mutex::new(HashMap::new()));

        loop {
            tokio::select! {
                maybe_stream = listener.accept() => {
                    if let Ok((stream, addr)) = maybe_stream {
                        if addr.ip().to_string() != "127.0.0.1" {
                            continue;
                        }

                        let db_clone = db.clone();
                        let crypto_clone = crypto.clone();
                        let clients_clone = clients.clone();
                        let autofill_clone = autofill_requests.clone();
                        let event_tx_clone = event_tx.clone();
                        let sender_id = uuid::Uuid::new_v4().to_string();

                        let _ = event_tx_clone.send(ServerEvent::ClientConnected {
                            sender_id: sender_id.clone(),
                        });

                        tokio::spawn(async move {
                            Self::handle_connection(
                                stream,
                                db_clone,
                                crypto_clone,
                                clients_clone,
                                autofill_clone,
                                event_tx_clone,
                                sender_id,
                            ).await;
                        });
                    }
                }
                cmd = command_rx.recv() => {
                    if let Some(cmd) = cmd {
                        match cmd {
                            ServerCommand::Stop => {
                                break;
                            }
                            ServerCommand::ApproveAutofill { request_id, entry_id } => {
                                Self::process_autofill_approval(
                                    &clients,
                                    &autofill_requests,
                                    request_id,
                                    entry_id,
                                    &db,
                                    &crypto,
                                ).await;
                            }
                            ServerCommand::DenyAutofill { request_id } => {
                                Self::process_autofill_denial(
                                    &clients,
                                    &autofill_requests,
                                    request_id,
                                ).await;
                            }
                        }
                    }
                }
                _ = async {
                    loop {
                        if !*running.lock().unwrap() {
                            break;
                        }
                        tokio::time::sleep(tokio::time::Duration::from_millis(200)).await;
                    }
                } => {
                    break;
                }
            }
        }
    }

    async fn handle_connection(
        stream: TcpStream,
        db: Option<Arc<Database>>,
        crypto: Option<Arc<Crypto>>,
        clients: Arc<Mutex<HashMap<String, mpsc::Sender<Message>>>>,
        _autofill_requests: Arc<Mutex<HashMap<u64, String>>>,
        event_tx: broadcast::Sender<ServerEvent>,
        sender_id: String,
    ) {
        let ws_stream = match tokio_tungstenite::accept_async(stream).await {
            Ok(ws) => ws,
            Err(_) => return,
        };

        let (writer_tx, mut writer_rx) = mpsc::channel::<Message>(32);
        clients.lock().unwrap().insert(sender_id.clone(), writer_tx);

        let (mut ws_sender, mut ws_receiver) = ws_stream.split();

        let sender_id_clone = sender_id.clone();
        let event_tx_clone = event_tx.clone();
        let db_clone = db.clone();
        let crypto_clone = crypto.clone();

        let read_task = tokio::spawn(async move {
            while let Some(msg) = ws_receiver.next().await {
                if let Ok(msg) = msg {
                    if let Message::Text(text) = msg {
                        let response = Self::process_message(&text, &db_clone, &crypto_clone);
                        if let Some(resp) = response {
                            if let Ok(json) = serde_json::to_string(&resp) {
                                let _ = clients
                                    .lock()
                                    .unwrap()
                                    .get(&sender_id_clone)
                                    .unwrap()
                                    .send(Message::Text(json))
                                    .await;
                            }
                        }
                    }
                }
            }
        });

        let write_task = tokio::spawn(async move {
            use futures_util::SinkExt;
            while let Some(msg) = writer_rx.recv().await {
                let _ = ws_sender.send(msg).await;
            }
        });

        let _ = tokio::join!(read_task, write_task);

        clients.lock().unwrap().remove(&sender_id);
        let _ = event_tx_clone.send(ServerEvent::ClientDisconnected {
            sender_id: sender_id.clone(),
        });
    }

    fn process_message(
        text: &str,
        db: &Option<Arc<Database>>,
        crypto: &Option<Arc<Crypto>>,
    ) -> Option<ExtensionMessage> {
        let msg: ExtensionMessage = match serde_json::from_str(text) {
            Ok(m) => m,
            Err(_) => return None,
        };

        match msg {
            ExtensionMessage::Ping { id } => Some(ExtensionMessage::Pong { id }),
            ExtensionMessage::ListServices { id } => {
                if let Some(db_ref) = db {
                    if let Ok(entries) = db_ref.get_all_passwords() {
                        let services: Vec<String> = entries.into_iter().map(|e| e.service).collect();
                        Some(ExtensionMessage::ListServicesResponse { id, services })
                    } else {
                        Some(ExtensionMessage::Error {
                            id,
                            message: "Failed to get passwords".to_string(),
                        })
                    }
                } else {
                    Some(ExtensionMessage::Error {
                        id,
                        message: "Vault locked".to_string(),
                    })
                }
            }
            ExtensionMessage::GetPassword { id, service } => {
                if let (Some(db_ref), Some(crypto_ref)) = (db, crypto) {
                    if let Ok(entries) = db_ref.search_passwords(&service) {
                        if let Some(entry) = entries.first() {
                            if let Ok(password) = crypto_ref.decrypt(&entry.encrypted_password) {
                                return Some(ExtensionMessage::GetPasswordResponse {
                                    id,
                                    username: entry.username.clone(),
                                    password,
                                });
                            }
                        }
                    }
                    Some(ExtensionMessage::Error {
                        id,
                        message: "Password not found".to_string(),
                    })
                } else {
                    Some(ExtensionMessage::Error {
                        id,
                        message: "Vault locked".to_string(),
                    })
                }
            }
            ExtensionMessage::Search { id, query } => {
                if let Some(db_ref) = db {
                    if let Ok(entries) = db_ref.search_passwords(&query) {
                        let results: Vec<SearchResult> = entries
                            .into_iter()
                            .map(|e| SearchResult {
                                id: e.id,
                                service: e.service,
                                username: e.username,
                            })
                            .collect();
                        Some(ExtensionMessage::SearchResponse { id, results })
                    } else {
                        Some(ExtensionMessage::Error {
                            id,
                            message: "Search failed".to_string(),
                        })
                    }
                } else {
                    Some(ExtensionMessage::Error {
                        id,
                        message: "Vault locked".to_string(),
                    })
                }
            }
            _ => None,
        }
    }

    async fn process_autofill_approval(
        _clients: &Arc<Mutex<HashMap<String, mpsc::Sender<Message>>>>,
        _autofill: &Arc<Mutex<HashMap<u64, String>>>,
        _request_id: u64,
        _entry_id: i64,
        _db: &Option<Arc<Database>>,
        _crypto: &Option<Arc<Crypto>>,
    ) {
    }

    async fn process_autofill_denial(
        _clients: &Arc<Mutex<HashMap<String, mpsc::Sender<Message>>>>,
        _autofill: &Arc<Mutex<HashMap<u64, String>>>,
        _request_id: u64,
    ) {
    }
}

#[derive(Debug)]
pub enum ServerError {
    AlreadyRunning,
    BindFailed,
}

impl std::fmt::Display for ServerError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ServerError::AlreadyRunning => write!(f, "Server already running"),
            ServerError::BindFailed => write!(f, "Failed to bind to port"),
        }
    }
}

impl std::error::Error for ServerError {}

