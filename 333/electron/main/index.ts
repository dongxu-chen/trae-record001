import { app, BrowserWindow, ipcMain, clipboard, globalShortcut, Notification, shell, dialog } from 'electron'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import * as os from 'os'
import Store from 'electron-store'
import { ClipboardMonitor } from './clipboard-monitor'
import { WebRTCManager } from './webrtc-manager'
import { HistoryManager } from './history-manager-sqlite'
import { DevicePairingManager } from './device-pairing-manager'
import { TransferStatsManager } from './transfer-stats-manager'
import type { 
  AppSettings, 
  ClipboardContent, 
  HistoryItem, 
  DataMigrationResult,
  PairingSession,
  PairedDevice,
  FilterRule,
  FilterResult,
  DashboardData
} from '@shared/types'
import { DEFAULT_SETTINGS, DEFAULT_KDF_ITERATIONS, SensitivePatternType } from '@shared/types'
import { 
  generateDeviceId, 
  generateEncryptionKey, 
  generateId, 
  deriveKeyFromPassword, 
  verifyPassword,
  applyAllFilterRules,
  detectSensitiveContent,
  getSensitivePatterns
} from '@shared/utils'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

process.env.APP_ROOT = path.join(__dirname, '../..')

export const VITE_DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL
export const MAIN_DIST = path.join(process.env.APP_ROOT, 'dist-electron')
export const RENDERER_DIST = path.join(process.env.APP_ROOT, 'dist')

process.env.VITE_PUBLIC = VITE_DEV_SERVER_URL
  ? path.join(process.env.APP_ROOT, 'public')
  : RENDERER_DIST

let win: BrowserWindow | null
let settingsStore: Store<AppSettings>
let clipboardMonitor: ClipboardMonitor
let webrtcManager: WebRTCManager
let historyManager: HistoryManager
let pairingManager: DevicePairingManager
let transferStatsManager: TransferStatsManager
let deviceId: string
let isDatabaseInitialized: boolean = false

function createWindow() {
  win = new BrowserWindow({
    icon: path.join(process.env.VITE_PUBLIC, 'favicon.ico'),
    width: 900,
    height: 650,
    minWidth: 700,
    minHeight: 500,
    frame: true,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(MAIN_DIST, 'preload/index.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false
    }
  })

  if (VITE_DEV_SERVER_URL) {
    win.loadURL(VITE_DEV_SERVER_URL)
  } else {
    win.loadFile(path.join(RENDERER_DIST, 'index.html'))
  }

  win.on('closed', () => {
    win = null
  })
}

function initializeSettings() {
  settingsStore = new Store<AppSettings>({
    name: 'settings',
    defaults: DEFAULT_SETTINGS
  })

  if (!settingsStore.get('deviceName')) {
    settingsStore.set('deviceName', `${os.hostname()}-${app.name}`)
  }

  if (!settingsStore.get('encryptionKey')) {
    settingsStore.set('encryptionKey', generateEncryptionKey())
  }

  deviceId = settingsStore.get('deviceId') || generateDeviceId()
  if (!settingsStore.get('deviceId')) {
    settingsStore.set('deviceId', deviceId)
  }
}

async function initializeDatabase(password?: string, existingKey?: string): Promise<boolean> {
  try {
    historyManager = new HistoryManager(settingsStore.get('historyLimit', 100))
    const success = await historyManager.initialize(password, existingKey)
    
    if (success) {
      isDatabaseInitialized = true
      
      if (password) {
        const derived = await deriveKeyFromPassword(password)
        settingsStore.set({
          passwordHash: derived.hash,
          passwordSalt: derived.salt,
          databaseKey: derived.key
        })
      }
    }
    
    return success
  } catch (e) {
    console.error('初始化数据库失败:', e)
    return false
  }
}

function initializeManagers() {
  const settings = settingsStore.store
  
  clipboardMonitor = new ClipboardMonitor(clipboard, {
    onClipboardChange: handleClipboardChange
  })
  
  webrtcManager = new WebRTCManager({
    deviceId,
    deviceName: settings.deviceName,
    signalingServer: settings.signalingServer,
    encryptionKey: settings.encryptionKey,
    lanOnly: settings.lanOnly,
    useRelayOnFailure: settings.useRelayOnFailure,
    maxRetryAttempts: settings.maxRetryAttempts,
    turnServers: settings.turnServers,
    onMessage: handleIncomingMessage,
    onDeviceListChange: handleDeviceListChange,
    onConnectionChange: handleConnectionChange,
    onTransferStatus: handleTransferStatus
  })

  pairingManager = new DevicePairingManager({
    deviceId,
    deviceName: settings.deviceName,
    onPairingComplete: handlePairingComplete
  })

  transferStatsManager = new TransferStatsManager()

  webrtcManager.on('transfer:start', (stats: any) => {
    transferStatsManager.startTransfer(
      stats.transferId,
      stats.peerId,
      stats.peerName,
      stats.totalBytes,
      stats.connectionMode,
      stats.direction
    )
  })

  webrtcManager.on('transfer:progress', (stats: any) => {
    transferStatsManager.updateTransferProgress(
      stats.transferId,
      stats.bytesTransferred,
      stats.latency
    )
  })

  webrtcManager.on('transfer:complete', (transferId: string) => {
    transferStatsManager.completeTransfer(transferId)
    sendDashboardUpdate()
  })

  webrtcManager.on('transfer:failed', (transferId: string) => {
    transferStatsManager.failTransfer(transferId)
    sendDashboardUpdate()
  })

  webrtcManager.on('network:update', (stats: any) => {
    transferStatsManager.updateConnectedPeers(stats.connectedPeers)
    sendDashboardUpdate()
  })

  pairingManager.on('pairing:complete', () => {
    sendPairedDevicesUpdate()
  })

  pairingManager.on('device:removed', () => {
    sendPairedDevicesUpdate()
  })
}

function handlePairingComplete(pairedDevice: PairedDevice) {
  const settings = settingsStore.store
  const pairedDevices = settings.pairedDevices || []
  if (!pairedDevices.find(d => d.deviceId === pairedDevice.deviceId)) {
    pairedDevices.push(pairedDevice)
    settingsStore.set({ pairedDevices })
  }
  sendPairedDevicesUpdate()
}

function sendPairedDevicesUpdate() {
  win?.webContents.send('paired-devices:updated', pairingManager.getPairedDevices())
}

function sendDashboardUpdate() {
  const data = transferStatsManager.getDashboardData()
  win?.webContents.send('dashboard:update', data)
}

async function handleClipboardChange(content: ClipboardContent) {
  const settings = settingsStore.store
  if (!settings.autoSync) return

  if (isDatabaseInitialized) {
    await historyManager.addItem({
      id: generateId(),
      content,
      createdAt: Date.now(),
      favorite: false,
      synced: true
    })
  }

  if (webrtcManager.isConnected()) {
    webrtcManager.broadcast(content)
  }

  win?.webContents.send('clipboard:changed', content)
  if (isDatabaseInitialized) {
    win?.webContents.send('history:updated', historyManager.getHistory())
  }
}

async function handleIncomingMessage(content: ClipboardContent) {
  const localHash = clipboardMonitor.getCurrentHash()
  if (content.hash === localHash) return

  if (isDatabaseInitialized) {
    await historyManager.addItem({
      id: generateId(),
      content,
      createdAt: Date.now(),
      favorite: false,
      synced: true
    })
  }

  clipboardMonitor.writeToClipboard(content)

  new Notification({
    title: '剪贴板已同步',
    body: `来自 ${content.deviceName} 的${content.type === 'text' ? '文本' : content.type === 'image' ? '图片' : '文件'}`,
    silent: true
  }).show()

  win?.webContents.send('clipboard:received', content)
  if (isDatabaseInitialized) {
    win?.webContents.send('history:updated', historyManager.getHistory())
  }
}

function handleDeviceListChange(devices: any[]) {
  win?.webContents.send('devices:updated', devices)
}

function handleConnectionChange(isConnected: boolean) {
  win?.webContents.send('connection:changed', isConnected)
}

function handleTransferStatus(transferId: string, status: string, progress: number) {
  win?.webContents.send('transfer:status', { transferId, status, progress })
}

function registerShortcuts() {
  const settings = settingsStore.store
  const shortcut = settings.quickPasteShortcut || 'Ctrl+Shift+V'

  const ret = globalShortcut.register(shortcut, () => {
    if (win) {
      if (win.isMinimized()) win.restore()
      win.show()
      win.focus()
      win.webContents.send('quick-paste:show')
    }
  })

  if (!ret) {
    console.log('快捷键注册失败')
  }
}

function setupIpcHandlers() {
  ipcMain.handle('settings:get', () => {
    return settingsStore.store
  })

  ipcMain.handle('settings:update', (_event, newSettings: Partial<AppSettings>) => {
    settingsStore.set(newSettings)
    if (newSettings.quickPasteShortcut) {
      globalShortcut.unregisterAll()
      registerShortcuts()
    }
    if (webrtcManager) {
      webrtcManager.updateSettings(settingsStore.store)
    }
    if (historyManager && newSettings.historyLimit) {
      historyManager.setMaxItems(newSettings.historyLimit)
    }
    return settingsStore.store
  })

  ipcMain.handle('auth:setPassword', async (_event, password: string) => {
    if (!isDatabaseInitialized) {
      const success = await initializeDatabase(password)
      if (success) {
        const legacyData = loadLegacyHistory()
        if (legacyData.length > 0) {
          await historyManager.migrateFromLegacy(legacyData)
        }
        win?.webContents.send('history:updated', historyManager.getHistory())
      }
      return success
    }
    return false
  })

  ipcMain.handle('auth:changePassword', async (_event, oldPassword: string, newPassword: string) => {
    if (!isDatabaseInitialized) return false
    
    const settings = settingsStore.store
    if (settings.passwordHash && settings.passwordSalt) {
      const isValid = await verifyPassword(
        oldPassword, 
        settings.passwordHash, 
        settings.passwordSalt,
        DEFAULT_KDF_ITERATIONS
      )
      if (!isValid) return false
    }
    
    return await historyManager.changePassword(oldPassword, newPassword)
  })

  ipcMain.handle('auth:verifyPassword', async (_event, password: string) => {
    const settings = settingsStore.store
    if (!settings.passwordHash || !settings.passwordSalt) {
      return true
    }
    
    const isValid = await verifyPassword(
      password,
      settings.passwordHash,
      settings.passwordSalt,
      DEFAULT_KDF_ITERATIONS
    )
    
    if (isValid && !isDatabaseInitialized) {
      await initializeDatabase(password)
      win?.webContents.send('history:updated', historyManager.getHistory())
    }
    
    return isValid
  })

  ipcMain.handle('auth:hasPassword', () => {
    const settings = settingsStore.store
    return !!settings.passwordHash
  })

  ipcMain.handle('auth:isInitialized', () => {
    return isDatabaseInitialized
  })

  ipcMain.handle('database:migrate', async (): Promise<DataMigrationResult> => {
    if (!isDatabaseInitialized) {
      return {
        success: false,
        migratedCount: 0,
        failedCount: 0,
        error: '数据库未初始化'
      }
    }
    
    const legacyData = loadLegacyHistory()
    const result = await historyManager.migrateFromLegacy(legacyData)
    
    if (result.success) {
      win?.webContents.send('history:updated', historyManager.getHistory())
    }
    
    return result
  })

  ipcMain.handle('database:getStats', () => {
    if (!isDatabaseInitialized) return null
    return {
      path: historyManager.getDatabasePath(),
      size: historyManager.getDatabaseSize(),
      count: historyManager.getHistory().length
    }
  })

  ipcMain.handle('database:vacuum', () => {
    if (!isDatabaseInitialized) return false
    historyManager.vacuum()
    return true
  })

  ipcMain.handle('clipboard:getCurrent', () => {
    return clipboardMonitor.getCurrentContent()
  })

  ipcMain.handle('clipboard:write', (_event, content: ClipboardContent) => {
    clipboardMonitor.writeToClipboard(content)
    handleClipboardChange(content)
  })

  ipcMain.handle('history:get', () => {
    if (!isDatabaseInitialized) return []
    return historyManager.getHistory()
  })

  ipcMain.handle('history:search', (_event, query: string) => {
    if (!isDatabaseInitialized) return []
    return historyManager.search(query)
  })

  ipcMain.handle('history:delete', (_event, id: string) => {
    if (!isDatabaseInitialized) return false
    return historyManager.deleteItem(id)
  })

  ipcMain.handle('history:clear', () => {
    if (!isDatabaseInitialized) return false
    return historyManager.clear()
  })

  ipcMain.handle('history:toggleFavorite', (_event, id: string) => {
    if (!isDatabaseInitialized) return false
    return historyManager.toggleFavorite(id)
  })

  ipcMain.handle('history:restore', async (_event, id: string) => {
    if (!isDatabaseInitialized) return false
    const item = historyManager.getItem(id)
    if (item) {
      clipboardMonitor.writeToClipboard(item.content)
      return true
    }
    return false
  })

  ipcMain.handle('devices:get', () => {
    return webrtcManager.getDevices()
  })

  ipcMain.handle('connection:connect', async () => {
    await webrtcManager.connect()
    return webrtcManager.isConnected()
  })

  ipcMain.handle('connection:disconnect', () => {
    webrtcManager.disconnect()
    return true
  })

  ipcMain.handle('connection:status', () => {
    return {
      isConnected: webrtcManager.isConnected(),
      connectedDevices: webrtcManager.getConnectedCount()
    }
  })

  ipcMain.handle('sync:sendToDevice', (_event, deviceId: string, content: ClipboardContent) => {
    return webrtcManager.sendTo(deviceId, content)
  })

  ipcMain.handle('app:generateKey', () => {
    return generateEncryptionKey()
  })

  ipcMain.handle('app:openExternal', (_event, url: string) => {
    shell.openExternal(url)
  })

  ipcMain.handle('app:showDialog', (_event, options: any) => {
    return dialog.showMessageBox(win!, options)
  })

  ipcMain.handle('pairing:createSession', (): PairingSession => {
    return pairingManager.createPairingSession()
  })

  ipcMain.handle('pairing:verifyCode', (_event, sessionId: string, code: string): boolean => {
    return pairingManager.verifyPairingCode(sessionId, code)
  })

  ipcMain.handle('pairing:complete', (_event, sessionId: string, remoteDeviceId: string, remoteDeviceName: string, remoteDeviceType: string): PairedDevice => {
    return pairingManager.completePairing(sessionId, remoteDeviceId, remoteDeviceName, remoteDeviceType)
  })

  ipcMain.handle('pairing:getPairedDevices', (): PairedDevice[] => {
    const settings = settingsStore.store
    return settings.pairedDevices || pairingManager.getPairedDevices()
  })

  ipcMain.handle('pairing:removeDevice', (_event, deviceId: string): boolean => {
    const result = pairingManager.removePairedDevice(deviceId)
    if (result) {
      const settings = settingsStore.store
      const pairedDevices = (settings.pairedDevices || []).filter(d => d.deviceId !== deviceId)
      settingsStore.set({ pairedDevices })
    }
    return result
  })

  ipcMain.handle('pairing:parseQRCode', (_event, qrData: string) => {
    return pairingManager.parseQRCode(qrData)
  })

  ipcMain.handle('pairing:cancelSession', (_event, sessionId: string): void => {
    pairingManager.cancelPairingSession(sessionId)
  })

  ipcMain.handle('filter:checkContent', (_event, content: ClipboardContent): FilterResult => {
    const settings = settingsStore.store
    const rules = settings.filterRules || []
    const enabledPatterns = settings.enabledSensitivePatterns || []
    const enableDetection = settings.enableSensitivePatternDetection || false
    
    return applyAllFilterRules(content, rules, enabledPatterns, enableDetection)
  })

  ipcMain.handle('filter:getRules', (): FilterRule[] => {
    const settings = settingsStore.store
    return settings.filterRules || []
  })

  ipcMain.handle('filter:addRule', (_event, rule: Omit<FilterRule, 'id' | 'createdAt' | 'updatedAt'>): FilterRule => {
    const settings = settingsStore.store
    const rules = settings.filterRules || []
    const newRule: FilterRule = {
      ...rule,
      id: generateId(),
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
    rules.push(newRule)
    settingsStore.set({ filterRules: rules })
    return newRule
  })

  ipcMain.handle('filter:updateRule', (_event, ruleId: string, updates: Partial<FilterRule>): FilterRule | null => {
    const settings = settingsStore.store
    const rules = settings.filterRules || []
    const index = rules.findIndex(r => r.id === ruleId)
    if (index === -1) return null
    
    rules[index] = {
      ...rules[index],
      ...updates,
      updatedAt: Date.now()
    }
    settingsStore.set({ filterRules: rules })
    return rules[index]
  })

  ipcMain.handle('filter:deleteRule', (_event, ruleId: string): boolean => {
    const settings = settingsStore.store
    const rules = settings.filterRules || []
    const filtered = rules.filter(r => r.id !== ruleId)
    settingsStore.set({ filterRules: filtered })
    return filtered.length < rules.length
  })

  ipcMain.handle('filter:getSensitivePatterns', () => {
    return getSensitivePatterns()
  })

  ipcMain.handle('filter:detectSensitive', (_event, text: string) => {
    const settings = settingsStore.store
    const enabledPatterns = settings.enabledSensitivePatterns || []
    return detectSensitiveContent(text, enabledPatterns)
  })

  ipcMain.handle('dashboard:getData', (): DashboardData => {
    return transferStatsManager.getDashboardData()
  })

  ipcMain.handle('dashboard:getFormattedStats', () => {
    return transferStatsManager.getFormattedStats()
  })

  ipcMain.handle('dashboard:getNetworkStats', () => {
    return transferStatsManager.getNetworkStats()
  })
}

function loadLegacyHistory(): HistoryItem[] {
  try {
    const legacyStore = new Store({ name: 'clipboard-history' })
    const legacyData = legacyStore.get('history', []) as HistoryItem[]
    return legacyData.map(item => ({
      ...item,
      synced: item.synced !== undefined ? item.synced : true
    }))
  } catch (e) {
    console.warn('加载旧版历史记录失败:', e)
    return []
  }
}

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})

app.whenReady().then(async () => {
  initializeSettings()
  initializeManagers()
  setupIpcHandlers()
  createWindow()
  registerShortcuts()
  clipboardMonitor.start()
  
  const settings = settingsStore.store
  
  if (!settings.passwordHash) {
    const success = await initializeDatabase()
    if (success) {
      const legacyData = loadLegacyHistory()
      if (legacyData.length > 0) {
        await historyManager.migrateFromLegacy(legacyData)
      }
      win?.webContents.send('history:updated', historyManager.getHistory())
    }
  }
  
  if (settings.autoSync) {
    await webrtcManager.connect()
  }
})

app.on('will-quit', () => {
  globalShortcut.unregisterAll()
  clipboardMonitor.stop()
  webrtcManager.disconnect()
  if (historyManager) {
    historyManager.close()
  }
})

app.on('web-contents-created', (_event, contents) => {
  contents.on('will-navigate', (event, navigationUrl) => {
    const parsedUrl = new URL(navigationUrl)
    if (parsedUrl.origin !== 'http://localhost:33445' && parsedUrl.protocol !== 'file:') {
      event.preventDefault()
      shell.openExternal(navigationUrl)
    }
  })
})
