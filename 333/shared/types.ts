export enum ClipboardDataType {
  TEXT = 'text',
  IMAGE = 'image',
  FILE = 'file',
  FILES = 'files'
}

export enum ConnectionMode {
  DIRECT = 'direct',
  LAN = 'lan',
  RELAY = 'relay'
}

export enum TransferStatus {
  PENDING = 'pending',
  TRANSFERRING = 'transferring',
  VERIFYING = 'verifying',
  COMPLETED = 'completed',
  FAILED = 'failed',
  RETRYING = 'retrying'
}

export enum PairingStatus {
  IDLE = 'idle',
  WAITING = 'waiting',
  VERIFYING = 'verifying',
  PAIRED = 'paired',
  FAILED = 'failed',
  EXPIRED = 'expired'
}

export enum FilterAction {
  ALLOW = 'allow',
  BLOCK = 'block',
  ASK = 'ask'
}

export enum FilterType {
  KEYWORD = 'keyword',
  REGEX = 'regex',
  FILE_TYPE = 'file_type',
  FILE_SIZE = 'file_size',
  CONTENT_TYPE = 'content_type',
  SENSITIVE_PATTERN = 'sensitive_pattern'
}

export enum SensitivePatternType {
  EMAIL = 'email',
  PHONE = 'phone',
  ID_CARD = 'id_card',
  BANK_CARD = 'bank_card',
  PASSWORD = 'password',
  URL = 'url',
  IP_ADDRESS = 'ip_address',
  CUSTOM = 'custom'
}

export interface ClipboardContent {
  id: string
  type: ClipboardDataType
  data: string | FileData | FileData[]
  timestamp: number
  deviceId: string
  deviceName: string
  hash: string
  checksum?: string
}

export interface FileData {
  name: string
  size: number
  type: string
  data: string
  checksum?: string
}

export interface Device {
  id: string
  name: string
  type: 'desktop' | 'mobile'
  isOnline: boolean
  isLocal: boolean
  lastSeen: number
  connectionMode?: ConnectionMode
}

export interface EncryptedData {
  iv: string
  encrypted: string
  tag?: string
}

export interface SignalingMessage {
  type: 'offer' | 'answer' | 'candidate' | 'join' | 'leave' | 'devices' | 'ping' | 'relay-config'
  from: string
  to?: string
  payload?: any
  timestamp: number
}

export interface AppSettings {
  deviceName: string
  encryptionKey: string
  signalingServer: string
  turnServers: TurnServerConfig[]
  autoSync: boolean
  historyLimit: number
  lanOnly: boolean
  quickPasteShortcut: string
  autoStart: boolean
  useRelayOnFailure: boolean
  maxRetryAttempts: number
  passwordHash?: string
  passwordSalt?: string
  databaseKey?: string
  filterRules: FilterRule[]
  enableContentFilter: boolean
  enableSensitivePatternDetection: boolean
  enabledSensitivePatterns: SensitivePatternType[]
  showDashboard: boolean
  dashboardRefreshInterval: number
  pairedDevices: PairedDevice[]
  pairingEnabled: boolean
}

export interface PairedDevice {
  deviceId: string
  deviceName: string
  deviceType: string
  pairedAt: number
  lastConnected: number
  isTrusted: boolean
}

export interface TurnServerConfig {
  urls: string | string[]
  username?: string
  credential?: string
}

export interface WebRTCConnection {
  peerId: string
  peer: any
  channel: any
  isConnected: boolean
  isLocal: boolean
  connectionMode: ConnectionMode
  lastConnectionAttempt: number
  relayFallbackAttempted: boolean
}

export interface HistoryItem {
  id: string
  content: ClipboardContent
  createdAt: number
  favorite: boolean
  synced: boolean
}

export interface ChunkData {
  transferId: string
  chunkIndex: number
  totalChunks: number
  data: string
  checksum: string
  timestamp: number
}

export interface ChunkAck {
  transferId: string
  chunkIndex: number
  success: boolean
  receivedChecksum: string
}

export interface TransferSession {
  id: string
  contentId: string
  peerId: string
  status: TransferStatus
  totalChunks: number
  receivedChunks: Map<number, ChunkData>
  failedChunks: Set<number>
  retryCount: number
  startTime: number
  lastActivity: number
}

export interface DatabaseConfig {
  path: string
  key: string
  cipher: string
  kdfIterations: number
}

export interface PasswordDerivedKey {
  key: string
  salt: string
  iterations: number
  hash: string
}

export interface DataMigrationResult {
  success: boolean
  migratedCount: number
  failedCount: number
  error?: string
}

export interface DevicePairing {
  id: string
  deviceId: string
  deviceName: string
  verificationCode: string
  qrCodeData: string
  status: PairingStatus
  createdAt: number
  expiresAt: number
  pairedDeviceId?: string
  pairedDeviceName?: string
}

export interface PairingSession {
  sessionId: string
  verificationCode: string
  qrCodeData: string
  status: PairingStatus
  expiresAt: number
  deviceInfo: {
    deviceId: string
    deviceName: string
    deviceType: string
  }
}

export interface FilterRule {
  id: string
  name: string
  type: FilterType
  pattern: string
  action: FilterAction
  enabled: boolean
  caseSensitive: boolean
  description?: string
  createdAt: number
  updatedAt: number
}

export interface FilterResult {
  matched: boolean
  ruleId?: string
  ruleName?: string
  action: FilterAction
  matchedContent?: string
}

export interface SensitivePattern {
  type: SensitivePatternType
  name: string
  pattern: string
  description: string
  enabled: boolean
}

export interface TransferSpeedStats {
  transferId: string
  peerId: string
  peerName: string
  startTime: number
  endTime?: number
  totalBytes: number
  transferredBytes: number
  currentSpeed: number
  averageSpeed: number
  peakSpeed: number
  latency: number
  chunkSize: number
  totalChunks: number
  transferredChunks: number
  failedChunks: number
  retriedChunks: number
  connectionMode: ConnectionMode
  status: TransferStatus
}

export interface NetworkStats {
  timestamp: number
  uploadSpeed: number
  downloadSpeed: number
  totalUploaded: number
  totalDownloaded: number
  activeTransfers: number
  connectedPeers: number
  averageLatency: number
}

export interface DashboardData {
  currentTransfers: TransferSpeedStats[]
  networkStats: NetworkStats
  transferHistory: TransferSpeedStats[]
}

export const DEFAULT_SETTINGS: AppSettings = {
  deviceName: '',
  encryptionKey: '',
  signalingServer: 'ws://localhost:33446',
  turnServers: [
    {
      urls: 'turn:turn.example.com:3478',
      username: 'clipboard-sync',
      credential: 'change-me'
    }
  ],
  autoSync: true,
  historyLimit: 100,
  lanOnly: false,
  quickPasteShortcut: 'Ctrl+Shift+V',
  autoStart: true,
  useRelayOnFailure: true,
  maxRetryAttempts: 3,
  passwordHash: '',
  passwordSalt: '',
  databaseKey: '',
  filterRules: [],
  enableContentFilter: false,
  enableSensitivePatternDetection: false,
  enabledSensitivePatterns: [
    SensitivePatternType.EMAIL,
    SensitivePatternType.PHONE,
    SensitivePatternType.ID_CARD,
    SensitivePatternType.BANK_CARD
  ],
  showDashboard: true,
  dashboardRefreshInterval: 1000,
  pairedDevices: [],
  pairingEnabled: true
}

export const DEFAULT_KDF_ITERATIONS = 100000
export const DEFAULT_CHUNK_SIZE = 32768
export const DEFAULT_MAX_RETRY_DELAY = 5000
export const DATABASE_CIPHER = 'aes-256-cbc'
