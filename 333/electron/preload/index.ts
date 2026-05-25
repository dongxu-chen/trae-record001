import { contextBridge, ipcRenderer } from 'electron'
import type { 
  AppSettings, 
  ClipboardContent, 
  Device, 
  HistoryItem, 
  DataMigrationResult,
  PairingSession,
  PairedDevice,
  FilterRule,
  FilterResult,
  DashboardData
} from '@shared/types'

const api = {
  settings: {
    get: (): Promise<AppSettings> => ipcRenderer.invoke('settings:get'),
    update: (settings: Partial<AppSettings>): Promise<AppSettings> => 
      ipcRenderer.invoke('settings:update', settings)
  },
  
  auth: {
    setPassword: (password: string): Promise<boolean> => 
      ipcRenderer.invoke('auth:setPassword', password),
    changePassword: (oldPassword: string, newPassword: string): Promise<boolean> => 
      ipcRenderer.invoke('auth:changePassword', oldPassword, newPassword),
    verifyPassword: (password: string): Promise<boolean> => 
      ipcRenderer.invoke('auth:verifyPassword', password),
    hasPassword: (): Promise<boolean> => 
      ipcRenderer.invoke('auth:hasPassword'),
    isInitialized: (): Promise<boolean> => 
      ipcRenderer.invoke('auth:isInitialized')
  },
  
  database: {
    migrate: (): Promise<DataMigrationResult> => 
      ipcRenderer.invoke('database:migrate'),
    getStats: (): Promise<{ path: string; size: number; count: number } | null> => 
      ipcRenderer.invoke('database:getStats'),
    vacuum: (): Promise<boolean> => 
      ipcRenderer.invoke('database:vacuum')
  },
  
  clipboard: {
    getCurrent: (): Promise<ClipboardContent | null> => 
      ipcRenderer.invoke('clipboard:getCurrent'),
    write: (content: ClipboardContent): Promise<void> => 
      ipcRenderer.invoke('clipboard:write', content)
  },
  
  history: {
    get: (): Promise<HistoryItem[]> => ipcRenderer.invoke('history:get'),
    search: (query: string): Promise<HistoryItem[]> => 
      ipcRenderer.invoke('history:search', query),
    delete: (id: string): Promise<boolean> => 
      ipcRenderer.invoke('history:delete', id),
    clear: (): Promise<boolean> => ipcRenderer.invoke('history:clear'),
    toggleFavorite: (id: string): Promise<boolean> => 
      ipcRenderer.invoke('history:toggleFavorite', id),
    restore: (id: string): Promise<boolean> => 
      ipcRenderer.invoke('history:restore', id)
  },
  
  devices: {
    get: (): Promise<Device[]> => ipcRenderer.invoke('devices:get')
  },
  
  connection: {
    connect: (): Promise<boolean> => ipcRenderer.invoke('connection:connect'),
    disconnect: (): Promise<boolean> => ipcRenderer.invoke('connection:disconnect'),
    status: (): Promise<{ isConnected: boolean; connectedDevices: number }> => 
      ipcRenderer.invoke('connection:status')
  },
  
  sync: {
    sendToDevice: (deviceId: string, content: ClipboardContent): Promise<boolean> => 
      ipcRenderer.invoke('sync:sendToDevice', deviceId, content)
  },
  
  pairing: {
    createSession: (): Promise<PairingSession> => 
      ipcRenderer.invoke('pairing:createSession'),
    verifyCode: (sessionId: string, code: string): Promise<boolean> => 
      ipcRenderer.invoke('pairing:verifyCode', sessionId, code),
    complete: (sessionId: string, remoteDeviceId: string, remoteDeviceName: string, remoteDeviceType: string): Promise<PairedDevice> => 
      ipcRenderer.invoke('pairing:complete', sessionId, remoteDeviceId, remoteDeviceName, remoteDeviceType),
    getPairedDevices: (): Promise<PairedDevice[]> => 
      ipcRenderer.invoke('pairing:getPairedDevices'),
    removeDevice: (deviceId: string): Promise<boolean> => 
      ipcRenderer.invoke('pairing:removeDevice', deviceId),
    parseQRCode: (qrData: string): Promise<any> => 
      ipcRenderer.invoke('pairing:parseQRCode', qrData),
    cancelSession: (sessionId: string): Promise<void> => 
      ipcRenderer.invoke('pairing:cancelSession', sessionId)
  },
  
  filter: {
    checkContent: (content: ClipboardContent): Promise<FilterResult> => 
      ipcRenderer.invoke('filter:checkContent', content),
    getRules: (): Promise<FilterRule[]> => 
      ipcRenderer.invoke('filter:getRules'),
    addRule: (rule: Omit<FilterRule, 'id' | 'createdAt' | 'updatedAt'>): Promise<FilterRule> => 
      ipcRenderer.invoke('filter:addRule', rule),
    updateRule: (ruleId: string, updates: Partial<FilterRule>): Promise<FilterRule | null> => 
      ipcRenderer.invoke('filter:updateRule', ruleId, updates),
    deleteRule: (ruleId: string): Promise<boolean> => 
      ipcRenderer.invoke('filter:deleteRule', ruleId),
    getSensitivePatterns: (): Promise<any[]> => 
      ipcRenderer.invoke('filter:getSensitivePatterns'),
    detectSensitive: (text: string): Promise<any[]> => 
      ipcRenderer.invoke('filter:detectSensitive', text)
  },
  
  dashboard: {
    getData: (): Promise<DashboardData> => 
      ipcRenderer.invoke('dashboard:getData'),
    getFormattedStats: (): Promise<any> => 
      ipcRenderer.invoke('dashboard:getFormattedStats'),
    getNetworkStats: (): Promise<any> => 
      ipcRenderer.invoke('dashboard:getNetworkStats')
  },
  
  app: {
    generateKey: (): Promise<string> => ipcRenderer.invoke('app:generateKey'),
    openExternal: (url: string): Promise<void> => 
      ipcRenderer.invoke('app:openExternal', url),
    showDialog: (options: any): Promise<any> => 
      ipcRenderer.invoke('app:showDialog', options)
  },
  
  on: (channel: string, callback: (...args: any[]) => void) => {
    const validChannels = [
      'clipboard:changed',
      'clipboard:received',
      'history:updated',
      'devices:updated',
      'connection:changed',
      'quick-paste:show',
      'transfer:status',
      'paired-devices:updated',
      'dashboard:update',
      'filter:triggered'
    ]
    
    if (validChannels.includes(channel)) {
      const subscription = (_event: any, ...args: any[]) => callback(...args)
      ipcRenderer.on(channel, subscription)
      return () => ipcRenderer.removeListener(channel, subscription)
    }
    return () => {}
  },
  
  off: (channel: string, callback: (...args: any[]) => void) => {
    ipcRenderer.removeListener(channel, callback)
  }
}

contextBridge.exposeInMainWorld('electronAPI', api)

export type ElectronAPI = typeof api
