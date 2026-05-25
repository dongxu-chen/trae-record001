import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
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
import { DEFAULT_SETTINGS } from '@shared/types'

interface TransferStatus {
  transferId: string
  status: string
  progress: number
}

interface AppContextType {
  settings: AppSettings
  updateSettings: (settings: Partial<AppSettings>) => Promise<void>
  history: HistoryItem[]
  devices: Device[]
  connectionStatus: { isConnected: boolean; connectedDevices: number }
  isSyncing: boolean
  searchQuery: string
  setSearchQuery: (query: string) => void
  selectedFilter: 'all' | 'text' | 'image' | 'file' | 'favorites'
  setSelectedFilter: (filter: 'all' | 'text' | 'image' | 'file' | 'favorites') => void
  showQuickPaste: boolean
  setShowQuickPaste: (show: boolean) => void
  copyToClipboard: (content: ClipboardContent) => Promise<void>
  deleteHistoryItem: (id: string) => Promise<boolean>
  clearHistory: () => Promise<boolean>
  toggleFavorite: (id: string) => Promise<boolean>
  restoreHistoryItem: (id: string) => Promise<boolean>
  sendToDevice: (deviceId: string, content: ClipboardContent) => Promise<boolean>
  connect: () => Promise<boolean>
  disconnect: () => Promise<boolean>
  generateNewKey: () => Promise<string>
  hasPassword: boolean
  isDatabaseInitialized: boolean
  setPassword: (password: string) => Promise<boolean>
  changePassword: (oldPassword: string, newPassword: string) => Promise<boolean>
  verifyPassword: (password: string) => Promise<boolean>
  migrateData: () => Promise<DataMigrationResult>
  getDatabaseStats: () => Promise<{ path: string; size: number; count: number } | null>
  vacuumDatabase: () => Promise<boolean>
  transferStatus: TransferStatus | null
  createPairingSession: () => Promise<PairingSession>
  verifyPairingCode: (sessionId: string, code: string) => Promise<boolean>
  completePairing: (sessionId: string, remoteDeviceId: string, remoteDeviceName: string, remoteDeviceType: string) => Promise<PairedDevice>
  getPairedDevices: () => Promise<PairedDevice[]>
  removePairedDevice: (deviceId: string) => Promise<boolean>
  pairedDevices: PairedDevice[]
  getFilterRules: () => Promise<FilterRule[]>
  addFilterRule: (rule: Omit<FilterRule, 'id' | 'createdAt' | 'updatedAt'>) => Promise<FilterRule>
  updateFilterRule: (ruleId: string, updates: Partial<FilterRule>) => Promise<FilterRule | null>
  deleteFilterRule: (ruleId: string) => Promise<boolean>
  checkContentFilter: (content: ClipboardContent) => Promise<FilterResult>
  filterRules: FilterRule[]
  getDashboardData: () => Promise<DashboardData>
  getFormattedStats: () => Promise<any>
  dashboardData: DashboardData | null
}

const AppContext = createContext<AppContextType | null>(null)

export const useApp = () => {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useApp must be used within AppProvider')
  }
  return context
}

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [devices, setDevices] = useState<Device[]>([])
  const [connectionStatus, setConnectionStatus] = useState({ isConnected: false, connectedDevices: 0 })
  const [isSyncing, setIsSyncing] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedFilter, setSelectedFilter] = useState<'all' | 'text' | 'image' | 'file' | 'favorites'>('all')
  const [showQuickPaste, setShowQuickPaste] = useState(false)
  const [hasPassword, setHasPassword] = useState(false)
  const [isDatabaseInitialized, setIsDatabaseInitialized] = useState(false)
  const [transferStatus, setTransferStatus] = useState<TransferStatus | null>(null)
  const [pairedDevices, setPairedDevices] = useState<PairedDevice[]>([])
  const [filterRules, setFilterRules] = useState<FilterRule[]>([])
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null)
  const initialized = useRef(false)

  useEffect(() => {
    if (initialized.current) return
    initialized.current = true

    const init = async () => {
      try {
        const [loadedSettings, loadedHistory, loadedDevices, status, hasPwd, dbInitialized, loadedPairedDevices, loadedFilterRules] = await Promise.all([
          window.electronAPI.settings.get(),
          window.electronAPI.history.get(),
          window.electronAPI.devices.get(),
          window.electronAPI.connection.status(),
          window.electronAPI.auth.hasPassword(),
          window.electronAPI.auth.isInitialized(),
          window.electronAPI.pairing.getPairedDevices(),
          window.electronAPI.filter.getRules()
        ])
        
        setSettings(loadedSettings)
        setHistory(loadedHistory)
        setDevices(loadedDevices)
        setConnectionStatus(status)
        setHasPassword(hasPwd)
        setIsDatabaseInitialized(dbInitialized)
        setPairedDevices(loadedPairedDevices)
        setFilterRules(loadedFilterRules)
      } catch (e) {
        console.error('初始化失败:', e)
      }
    }

    init()

    const unsub1 = window.electronAPI.on('history:updated', (newHistory: HistoryItem[]) => {
      setHistory(newHistory)
    })

    const unsub2 = window.electronAPI.on('devices:updated', (newDevices: Device[]) => {
      setDevices(newDevices)
    })

    const unsub3 = window.electronAPI.on('connection:changed', (isConnected: boolean) => {
      setConnectionStatus(prev => ({ ...prev, isConnected }))
    })

    const unsub4 = window.electronAPI.on('clipboard:changed', () => {
      setIsSyncing(true)
      setTimeout(() => setIsSyncing(false), 1000)
    })

    const unsub5 = window.electronAPI.on('clipboard:received', () => {
      setIsSyncing(true)
      setTimeout(() => setIsSyncing(false), 1000)
    })

    const unsub6 = window.electronAPI.on('quick-paste:show', () => {
      setShowQuickPaste(true)
    })

    const unsub7 = window.electronAPI.on('transfer:status', (status: TransferStatus) => {
      setTransferStatus(status)
      if (status.status === 'completed' || status.status === 'failed') {
        setTimeout(() => setTransferStatus(null), 3000)
      }
    })

    const unsub8 = window.electronAPI.on('paired-devices:updated', (devices: PairedDevice[]) => {
      setPairedDevices(devices)
    })

    const unsub9 = window.electronAPI.on('dashboard:update', (data: DashboardData) => {
      setDashboardData(data)
    })

    return () => {
      unsub1()
      unsub2()
      unsub3()
      unsub4()
      unsub5()
      unsub6()
      unsub7()
      unsub8()
      unsub9()
    }
  }, [])

  const updateSettings = useCallback(async (newSettings: Partial<AppSettings>) => {
    try {
      const updated = await window.electronAPI.settings.update(newSettings)
      setSettings(updated)
    } catch (e) {
      console.error('更新设置失败:', e)
      throw e
    }
  }, [])

  const copyToClipboard = useCallback(async (content: ClipboardContent) => {
    try {
      await window.electronAPI.clipboard.write(content)
    } catch (e) {
      console.error('复制到剪贴板失败:', e)
      throw e
    }
  }, [])

  const deleteHistoryItem = useCallback(async (id: string) => {
    try {
      const success = await window.electronAPI.history.delete(id)
      if (success) {
        setHistory(prev => prev.filter(item => item.id !== id))
      }
      return success
    } catch (e) {
      console.error('删除历史记录失败:', e)
      return false
    }
  }, [])

  const clearHistory = useCallback(async () => {
    try {
      const success = await window.electronAPI.history.clear()
      if (success) {
        setHistory([])
      }
      return success
    } catch (e) {
      console.error('清空历史记录失败:', e)
      return false
    }
  }, [])

  const toggleFavorite = useCallback(async (id: string) => {
    try {
      const success = await window.electronAPI.history.toggleFavorite(id)
      if (success) {
        setHistory(prev => prev.map(item => 
          item.id === id ? { ...item, favorite: !item.favorite } : item
        ))
      }
      return success
    } catch (e) {
      console.error('切换收藏失败:', e)
      return false
    }
  }, [])

  const restoreHistoryItem = useCallback(async (id: string) => {
    try {
      return await window.electronAPI.history.restore(id)
    } catch (e) {
      console.error('恢复历史记录失败:', e)
      return false
    }
  }, [])

  const sendToDevice = useCallback(async (deviceId: string, content: ClipboardContent) => {
    try {
      return await window.electronAPI.sync.sendToDevice(deviceId, content)
    } catch (e) {
      console.error('发送到设备失败:', e)
      return false
    }
  }, [])

  const connect = useCallback(async () => {
    try {
      const connected = await window.electronAPI.connection.connect()
      setConnectionStatus(prev => ({ ...prev, isConnected: connected }))
      return connected
    } catch (e) {
      console.error('连接失败:', e)
      return false
    }
  }, [])

  const disconnect = useCallback(async () => {
    try {
      await window.electronAPI.connection.disconnect()
      setConnectionStatus({ isConnected: false, connectedDevices: 0 })
      return true
    } catch (e) {
      console.error('断开连接失败:', e)
      return false
    }
  }, [])

  const generateNewKey = useCallback(async () => {
    try {
      return await window.electronAPI.app.generateKey()
    } catch (e) {
      console.error('生成密钥失败:', e)
      throw e
    }
  }, [])

  const setPassword = useCallback(async (password: string): Promise<boolean> => {
    try {
      const success = await window.electronAPI.auth.setPassword(password)
      if (success) {
        setHasPassword(true)
        setIsDatabaseInitialized(true)
        const loadedHistory = await window.electronAPI.history.get()
        setHistory(loadedHistory)
      }
      return success
    } catch (e) {
      console.error('设置密码失败:', e)
      return false
    }
  }, [])

  const changePassword = useCallback(async (oldPassword: string, newPassword: string): Promise<boolean> => {
    try {
      return await window.electronAPI.auth.changePassword(oldPassword, newPassword)
    } catch (e) {
      console.error('修改密码失败:', e)
      return false
    }
  }, [])

  const verifyPassword = useCallback(async (password: string): Promise<boolean> => {
    try {
      const success = await window.electronAPI.auth.verifyPassword(password)
      if (success) {
        setIsDatabaseInitialized(true)
        const loadedHistory = await window.electronAPI.history.get()
        setHistory(loadedHistory)
      }
      return success
    } catch (e) {
      console.error('验证密码失败:', e)
      return false
    }
  }, [])

  const migrateData = useCallback(async (): Promise<DataMigrationResult> => {
    try {
      const result = await window.electronAPI.database.migrate()
      if (result.success) {
        const loadedHistory = await window.electronAPI.history.get()
        setHistory(loadedHistory)
      }
      return result
    } catch (e) {
      console.error('数据迁移失败:', e)
      return {
        success: false,
        migratedCount: 0,
        failedCount: 0,
        error: (e as Error).message
      }
    }
  }, [])

  const getDatabaseStats = useCallback(async () => {
    try {
      return await window.electronAPI.database.getStats()
    } catch (e) {
      console.error('获取数据库统计失败:', e)
      return null
    }
  }, [])

  const vacuumDatabase = useCallback(async () => {
    try {
      return await window.electronAPI.database.vacuum()
    } catch (e) {
      console.error('压缩数据库失败:', e)
      return false
    }
  }, [])

  const createPairingSession = useCallback(async (): Promise<PairingSession> => {
    try {
      return await window.electronAPI.pairing.createSession()
    } catch (e) {
      console.error('创建设备配对会话失败:', e)
      throw e
    }
  }, [])

  const verifyPairingCode = useCallback(async (sessionId: string, code: string): Promise<boolean> => {
    try {
      return await window.electronAPI.pairing.verifyCode(sessionId, code)
    } catch (e) {
      console.error('验证配对码失败:', e)
      return false
    }
  }, [])

  const completePairing = useCallback(async (sessionId: string, remoteDeviceId: string, remoteDeviceName: string, remoteDeviceType: string): Promise<PairedDevice> => {
    try {
      const device = await window.electronAPI.pairing.complete(sessionId, remoteDeviceId, remoteDeviceName, remoteDeviceType)
      const devices = await window.electronAPI.pairing.getPairedDevices()
      setPairedDevices(devices)
      return device
    } catch (e) {
      console.error('完成配对失败:', e)
      throw e
    }
  }, [])

  const getPairedDevices = useCallback(async (): Promise<PairedDevice[]> => {
    try {
      const devices = await window.electronAPI.pairing.getPairedDevices()
      setPairedDevices(devices)
      return devices
    } catch (e) {
      console.error('获取已配对设备失败:', e)
      return []
    }
  }, [])

  const removePairedDevice = useCallback(async (deviceId: string): Promise<boolean> => {
    try {
      const success = await window.electronAPI.pairing.removeDevice(deviceId)
      if (success) {
        setPairedDevices(prev => prev.filter(d => d.deviceId !== deviceId))
      }
      return success
    } catch (e) {
      console.error('移除已配对设备失败:', e)
      return false
    }
  }, [])

  const getFilterRules = useCallback(async (): Promise<FilterRule[]> => {
    try {
      const rules = await window.electronAPI.filter.getRules()
      setFilterRules(rules)
      return rules
    } catch (e) {
      console.error('获取过滤规则失败:', e)
      return []
    }
  }, [])

  const addFilterRule = useCallback(async (rule: Omit<FilterRule, 'id' | 'createdAt' | 'updatedAt'>): Promise<FilterRule> => {
    try {
      const newRule = await window.electronAPI.filter.addRule(rule)
      setFilterRules(prev => [...prev, newRule])
      return newRule
    } catch (e) {
      console.error('添加过滤规则失败:', e)
      throw e
    }
  }, [])

  const updateFilterRule = useCallback(async (ruleId: string, updates: Partial<FilterRule>): Promise<FilterRule | null> => {
    try {
      const updated = await window.electronAPI.filter.updateRule(ruleId, updates)
      if (updated) {
        setFilterRules(prev => prev.map(r => r.id === ruleId ? updated : r))
      }
      return updated
    } catch (e) {
      console.error('更新过滤规则失败:', e)
      return null
    }
  }, [])

  const deleteFilterRule = useCallback(async (ruleId: string): Promise<boolean> => {
    try {
      const success = await window.electronAPI.filter.deleteRule(ruleId)
      if (success) {
        setFilterRules(prev => prev.filter(r => r.id !== ruleId))
      }
      return success
    } catch (e) {
      console.error('删除过滤规则失败:', e)
      return false
    }
  }, [])

  const checkContentFilter = useCallback(async (content: ClipboardContent): Promise<FilterResult> => {
    try {
      return await window.electronAPI.filter.checkContent(content)
    } catch (e) {
      console.error('检查内容过滤失败:', e)
      return { matched: false, action: 'allow' }
    }
  }, [])

  const getDashboardData = useCallback(async (): Promise<DashboardData> => {
    try {
      return await window.electronAPI.dashboard.getData()
    } catch (e) {
      console.error('获取仪表盘数据失败:', e)
      return {
        currentTransfers: [],
        networkStats: {
          timestamp: Date.now(),
          uploadSpeed: 0,
          downloadSpeed: 0,
          totalUploaded: 0,
          totalDownloaded: 0,
          activeTransfers: 0,
          connectedPeers: 0,
          averageLatency: 0
        },
        transferHistory: []
      }
    }
  }, [])

  const getFormattedStats = useCallback(async () => {
    try {
      return await window.electronAPI.dashboard.getFormattedStats()
    } catch (e) {
      console.error('获取格式化统计失败:', e)
      return null
    }
  }, [])

  const value: AppContextType = {
    settings,
    updateSettings,
    history,
    devices,
    connectionStatus,
    isSyncing,
    searchQuery,
    setSearchQuery,
    selectedFilter,
    setSelectedFilter,
    showQuickPaste,
    setShowQuickPaste,
    copyToClipboard,
    deleteHistoryItem,
    clearHistory,
    toggleFavorite,
    restoreHistoryItem,
    sendToDevice,
    connect,
    disconnect,
    generateNewKey,
    hasPassword,
    isDatabaseInitialized,
    setPassword,
    changePassword,
    verifyPassword,
    migrateData,
    getDatabaseStats,
    vacuumDatabase,
    transferStatus,
    createPairingSession,
    verifyPairingCode,
    completePairing,
    getPairedDevices,
    removePairedDevice,
    pairedDevices,
    getFilterRules,
    addFilterRule,
    updateFilterRule,
    deleteFilterRule,
    checkContentFilter,
    filterRules,
    getDashboardData,
    getFormattedStats,
    dashboardData
  }

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  )
}
