import React, { useState, useEffect } from 'react'
import { useApp } from '../context/AppContext'

const SettingsPage: React.FC = () => {
  const { 
    settings, 
    updateSettings, 
    generateNewKey,
    hasPassword,
    isDatabaseInitialized,
    setPassword,
    changePassword,
    migrateData,
    getDatabaseStats,
    vacuumDatabase
  } = useApp()
  const [showKey, setShowKey] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmNewPassword, setConfirmNewPassword] = useState('')
  const [showPasswordSection, setShowPasswordSection] = useState(false)
  const [showChangePasswordSection, setShowChangePasswordSection] = useState(false)
  const [passwordError, setPasswordError] = useState('')
  const [dbStats, setDbStats] = useState<{ path: string; size: number; count: number } | null>(null)
  const [migrationResult, setMigrationResult] = useState<{
    success: boolean
    migratedCount: number
    failedCount: number
    error?: string
  } | null>(null)
  const [isMigrating, setIsMigrating] = useState(false)
  const [isVacuuming, setIsVacuuming] = useState(false)
  const [turnServerUrl, setTurnServerUrl] = useState('')
  const [turnUsername, setTurnUsername] = useState('')
  const [turnPassword, setTurnPassword] = useState('')
  const [showTurnPassword, setShowTurnPassword] = useState(false)

  useEffect(() => {
    if (isDatabaseInitialized) {
      loadDbStats()
    }
  }, [isDatabaseInitialized])

  useEffect(() => {
    if (settings.turnServers && settings.turnServers.length > 0) {
      const first = settings.turnServers[0]
      setTurnServerUrl(first.url || '')
      setTurnUsername(first.username || '')
      setTurnPassword(first.credential || '')
    }
  }, [settings.turnServers])

  const loadDbStats = async () => {
    const stats = await getDatabaseStats()
    setDbStats(stats)
  }

  const handleUpdate = async (key: keyof typeof settings, value: any) => {
    await updateSettings({ [key]: value })
  }

  const handleGenerateKey = async () => {
    const confirmed = window.confirm(
      '生成新的密钥将导致与当前已连接设备断开。您需要在所有设备上更新密钥才能重新同步。确定继续吗？'
    )
    
    if (!confirmed) return
    
    setIsGenerating(true)
    try {
      const newKey = await generateNewKey()
      await updateSettings({ encryptionKey: newKey })
      setShowKey(true)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleCopyKey = async () => {
    await navigator.clipboard.writeText(settings.encryptionKey)
    alert('密钥已复制到剪贴板')
  }

  const handleSetPassword = async () => {
    setPasswordError('')
    
    if (!password) {
      setPasswordError('请输入密码')
      return
    }
    
    if (password.length < 8) {
      setPasswordError('密码长度至少为8位')
      return
    }
    
    if (password !== confirmPassword) {
      setPasswordError('两次输入的密码不一致')
      return
    }
    
    const success = await setPassword(password)
    if (success) {
      alert('密码设置成功！历史记录将使用此密码加密存储。')
      setPassword('')
      setConfirmPassword('')
      setShowPasswordSection(false)
      loadDbStats()
    } else {
      setPasswordError('密码设置失败，请重试')
    }
  }

  const handleChangePassword = async () => {
    setPasswordError('')
    
    if (!oldPassword || !newPassword) {
      setPasswordError('请填写所有密码字段')
      return
    }
    
    if (newPassword.length < 8) {
      setPasswordError('新密码长度至少为8位')
      return
    }
    
    if (newPassword !== confirmNewPassword) {
      setPasswordError('两次输入的新密码不一致')
      return
    }
    
    const success = await changePassword(oldPassword, newPassword)
    if (success) {
      alert('密码修改成功！')
      setOldPassword('')
      setNewPassword('')
      setConfirmNewPassword('')
      setShowChangePasswordSection(false)
    } else {
      setPasswordError('旧密码错误，请重试')
    }
  }

  const handleMigrate = async () => {
    const confirmed = window.confirm(
      '数据迁移将把旧版本的历史记录导入到新的加密数据库中。旧数据不会被删除。确定继续吗？'
    )
    
    if (!confirmed) return
    
    setIsMigrating(true)
    try {
      const result = await migrateData()
      setMigrationResult(result)
      if (result.success) {
        alert(`迁移成功！已迁移 ${result.migratedCount} 条记录，失败 ${result.failedCount} 条`)
        loadDbStats()
      } else {
        alert(`迁移失败：${result.error}`)
      }
    } finally {
      setIsMigrating(false)
    }
  }

  const handleVacuum = async () => {
    const confirmed = window.confirm(
      '数据库压缩将重建数据库文件，减小存储空间占用。此操作可能需要一些时间。确定继续吗？'
    )
    
    if (!confirmed) return
    
    setIsVacuuming(true)
    try {
      const success = await vacuumDatabase()
      if (success) {
        alert('数据库压缩完成！')
        loadDbStats()
      } else {
        alert('数据库压缩失败')
      }
    } finally {
      setIsVacuuming(false)
    }
  }

  const handleSaveTurnServer = async () => {
    const turnServers = turnServerUrl ? [{
      url: turnServerUrl,
      username: turnUsername,
      credential: turnPassword
    }] : []
    
    await updateSettings({ turnServers })
    alert('TURN 服务器配置已保存')
  }

  const handleAddTurnServer = () => {
    if (!turnServerUrl) {
      setTurnServerUrl('turn:')
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
  }

  const shortcutOptions = [
    'Ctrl+Shift+V',
    'Ctrl+Shift+C',
    'Alt+Shift+V',
    'Win+Shift+V',
    'Ctrl+Alt+V'
  ]

  const historyLimitOptions = [
    { value: 50, label: '50 条' },
    { value: 100, label: '100 条' },
    { value: 200, label: '200 条' },
    { value: 500, label: '500 条' },
    { value: 1000, label: '1000 条' }
  ]

  const retryAttemptsOptions = [
    { value: 1, label: '1 次' },
    { value: 3, label: '3 次' },
    { value: 5, label: '5 次' },
    { value: 10, label: '10 次' }
  ]

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold text-gray-800">设置</h2>
        <p className="text-sm text-gray-500 mt-1">
          配置剪贴板同步的各项参数
        </p>
      </div>

      <div className="card p-6 space-y-6">
        <h3 className="text-lg font-semibold text-gray-800 border-b border-gray-100 pb-3">
          🔐 安全设置
        </h3>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            设备名称
          </label>
          <input
            type="text"
            value={settings.deviceName}
            onChange={e => handleUpdate('deviceName', e.target.value)}
            placeholder="输入设备名称"
            className="input-field max-w-md"
          />
          <p className="text-xs text-gray-500 mt-1">
            此名称将显示在其他设备的设备列表中
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            加密密钥
          </label>
          <div className="flex gap-2 max-w-xl">
            <input
              type={showKey ? 'text' : 'password'}
              value={settings.encryptionKey}
              readOnly
              className="input-field flex-1 font-mono text-sm"
            />
            <button
              onClick={() => setShowKey(!showKey)}
              className="btn-secondary"
            >
              {showKey ? '🙈 隐藏' : '👁️ 显示'}
            </button>
            <button
              onClick={handleCopyKey}
              className="btn-secondary"
            >
              📋 复制
            </button>
          </div>
          <div className="mt-3">
            <button
              onClick={handleGenerateKey}
              disabled={isGenerating}
              className="btn-primary"
            >
              {isGenerating ? '生成中...' : '🔄 生成新密钥'}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            所有设备必须使用相同的密钥才能同步。请妥善保管您的密钥，丢失后将无法解密历史数据。
          </p>
        </div>

        <div className="pt-4 border-t border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h4 className="text-sm font-medium text-gray-700">数据库密码保护</h4>
              <p className="text-xs text-gray-500">
                使用密码加密存储历史记录，密钥派生自您的密码
              </p>
            </div>
            <div className="flex items-center gap-2">
              {hasPassword && (
                <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full">
                  ✓ 已启用
                </span>
              )}
            </div>
          </div>

          {!hasPassword && !showPasswordSection && (
            <button
              onClick={() => setShowPasswordSection(true)}
              className="btn-primary"
            >
              🔑 设置密码
            </button>
          )}

          {showPasswordSection && (
            <div className="space-y-4 p-4 bg-gray-50 rounded-lg">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  设置密码
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="至少8位字符"
                  className="input-field max-w-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  确认密码
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={e => setConfirmPassword(e.target.value)}
                  placeholder="再次输入密码"
                  className="input-field max-w-md"
                />
              </div>
              {passwordError && (
                <p className="text-sm text-red-500">{passwordError}</p>
              )}
              <div className="flex gap-2">
                <button onClick={handleSetPassword} className="btn-primary">
                  确认设置
                </button>
                <button
                  onClick={() => {
                    setShowPasswordSection(false)
                    setPassword('')
                    setConfirmPassword('')
                    setPasswordError('')
                  }}
                  className="btn-secondary"
                >
                  取消
                </button>
              </div>
            </div>
          )}

          {hasPassword && !showChangePasswordSection && (
            <button
              onClick={() => setShowChangePasswordSection(true)}
              className="btn-secondary mt-2"
            >
              🔄 修改密码
            </button>
          )}

          {showChangePasswordSection && (
            <div className="space-y-4 p-4 bg-gray-50 rounded-lg mt-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  旧密码
                </label>
                <input
                  type="password"
                  value={oldPassword}
                  onChange={e => setOldPassword(e.target.value)}
                  placeholder="输入旧密码"
                  className="input-field max-w-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  新密码
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={e => setNewPassword(e.target.value)}
                  placeholder="至少8位字符"
                  className="input-field max-w-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  确认新密码
                </label>
                <input
                  type="password"
                  value={confirmNewPassword}
                  onChange={e => setConfirmNewPassword(e.target.value)}
                  placeholder="再次输入新密码"
                  className="input-field max-w-md"
                />
              </div>
              {passwordError && (
                <p className="text-sm text-red-500">{passwordError}</p>
              )}
              <div className="flex gap-2">
                <button onClick={handleChangePassword} className="btn-primary">
                  确认修改
                </button>
                <button
                  onClick={() => {
                    setShowChangePasswordSection(false)
                    setOldPassword('')
                    setNewPassword('')
                    setConfirmNewPassword('')
                    setPasswordError('')
                  }}
                  className="btn-secondary"
                >
                  取消
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="card p-6 space-y-6">
        <h3 className="text-lg font-semibold text-gray-800 border-b border-gray-100 pb-3">
          📦 数据库管理
        </h3>

        {dbStats && (
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{dbStats.count}</div>
              <div className="text-xs text-gray-500 mt-1">记录数</div>
            </div>
            <div className="p-4 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">{formatFileSize(dbStats.size)}</div>
              <div className="text-xs text-gray-500 mt-1">数据库大小</div>
            </div>
            <div className="p-4 bg-purple-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">
                {hasPassword ? '加密' : '未加密'}
              </div>
              <div className="text-xs text-gray-500 mt-1">存储状态</div>
            </div>
          </div>
        )}

        <div className="flex flex-wrap gap-3">
          <button
            onClick={loadDbStats}
            className="btn-secondary"
            disabled={!isDatabaseInitialized}
          >
            📊 刷新统计
          </button>
          <button
            onClick={handleVacuum}
            disabled={!isDatabaseInitialized || isVacuuming}
            className="btn-secondary"
          >
            {isVacuuming ? '压缩中...' : '🗜️ 压缩数据库'}
          </button>
          <button
            onClick={handleMigrate}
            disabled={!isDatabaseInitialized || isMigrating}
            className="btn-primary"
          >
            {isMigrating ? '迁移中...' : '🔄 数据迁移'}
          </button>
        </div>

        {migrationResult && (
          <div className={`p-4 rounded-lg ${migrationResult.success ? 'bg-green-50' : 'bg-red-50'}`}>
            <p className="text-sm font-medium">
              {migrationResult.success ? '✅ 迁移完成' : '❌ 迁移失败'}
            </p>
            <p className="text-xs text-gray-600 mt-1">
              成功迁移：{migrationResult.migratedCount} 条 | 
              失败：{migrationResult.failedCount} 条
            </p>
            {migrationResult.error && (
              <p className="text-xs text-red-500 mt-1">错误：{migrationResult.error}</p>
            )}
          </div>
        )}

        {dbStats && (
          <div className="text-xs text-gray-500">
            数据库路径：<code className="bg-gray-100 px-1 rounded">{dbStats.path}</code>
          </div>
        )}
      </div>

      <div className="card p-6 space-y-6">
        <h3 className="text-lg font-semibold text-gray-800 border-b border-gray-100 pb-3">
          🌐 同步设置
        </h3>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            信令服务器地址
          </label>
          <input
            type="text"
            value={settings.signalingServer}
            onChange={e => handleUpdate('signalingServer', e.target.value)}
            placeholder="ws://example.com:33446"
            className="input-field max-w-md"
          />
          <p className="text-xs text-gray-500 mt-1">
            用于设备发现和 WebRTC 连接建立的服务器地址
          </p>
        </div>

        <div className="pt-4 border-t border-gray-100">
          <h4 className="text-sm font-medium text-gray-700 mb-4">TURN 中继服务器</h4>
          <p className="text-xs text-gray-500 mb-4">
            当局域网打孔和 P2P 直连失败时，将自动降级使用 TURN 中继服务器转发数据
          </p>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                服务器地址
              </label>
              <input
                type="text"
                value={turnServerUrl}
                onChange={e => setTurnServerUrl(e.target.value)}
                placeholder="turn:your-server.com:3478"
                className="input-field max-w-md"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                用户名
              </label>
              <input
                type="text"
                value={turnUsername}
                onChange={e => setTurnUsername(e.target.value)}
                placeholder="可选"
                className="input-field max-w-md"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                密码
              </label>
              <div className="flex gap-2 max-w-md">
                <input
                  type={showTurnPassword ? 'text' : 'password'}
                  value={turnPassword}
                  onChange={e => setTurnPassword(e.target.value)}
                  placeholder="可选"
                  className="input-field flex-1"
                />
                <button
                  onClick={() => setShowTurnPassword(!showTurnPassword)}
                  className="btn-secondary"
                  type="button"
                >
                  {showTurnPassword ? '🙈' : '👁️'}
                </button>
              </div>
            </div>
          </div>
          
          <div className="flex gap-2 mt-4">
            <button onClick={handleSaveTurnServer} className="btn-primary">
              💾 保存配置
            </button>
            <button onClick={handleAddTurnServer} className="btn-secondary">
              ➕ 添加服务器
            </button>
          </div>
        </div>

        <div className="pt-4 border-t border-gray-100">
          <h4 className="text-sm font-medium text-gray-700 mb-4">传输设置</h4>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              最大重试次数
            </label>
            <select
              value={settings.maxRetryAttempts}
              onChange={e => handleUpdate('maxRetryAttempts', parseInt(e.target.value))}
              className="input-field max-w-xs"
            >
              {retryAttemptsOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              分片传输失败时的最大重试次数
            </p>
          </div>
        </div>

        <div className="flex items-center justify-between max-w-md pt-4">
          <div>
            <div className="text-sm font-medium text-gray-700">自动同步</div>
            <div className="text-xs text-gray-500">
              剪贴板内容变化时自动同步到其他设备
            </div>
          </div>
          <button
            onClick={() => handleUpdate('autoSync', !settings.autoSync)}
            className={`w-12 h-6 rounded-full transition-colors ${
              settings.autoSync ? 'bg-primary-500' : 'bg-gray-300'
            }`}
          >
            <div className={`w-5 h-5 rounded-full bg-white shadow-sm transform transition-transform ${
              settings.autoSync ? 'translate-x-6' : 'translate-x-0.5'
            }`} />
          </button>
        </div>

        <div className="flex items-center justify-between max-w-md pt-4">
          <div>
            <div className="text-sm font-medium text-gray-700">仅局域网模式</div>
            <div className="text-xs text-gray-500">
              只与同一局域网内的设备同步，更安全、更快速
            </div>
          </div>
          <button
            onClick={() => handleUpdate('lanOnly', !settings.lanOnly)}
            className={`w-12 h-6 rounded-full transition-colors ${
              settings.lanOnly ? 'bg-primary-500' : 'bg-gray-300'
            }`}
          >
            <div className={`w-5 h-5 rounded-full bg-white shadow-sm transform transition-transform ${
              settings.lanOnly ? 'translate-x-6' : 'translate-x-0.5'
            }`} />
          </button>
        </div>

        <div className="flex items-center justify-between max-w-md pt-4">
          <div>
            <div className="text-sm font-medium text-gray-700">失败时使用中继</div>
            <div className="text-xs text-gray-500">
              P2P 连接失败时自动降级到 TURN 中继服务器
            </div>
          </div>
          <button
            onClick={() => handleUpdate('useRelayOnFailure', !settings.useRelayOnFailure)}
            className={`w-12 h-6 rounded-full transition-colors ${
              settings.useRelayOnFailure ? 'bg-primary-500' : 'bg-gray-300'
            }`}
          >
            <div className={`w-5 h-5 rounded-full bg-white shadow-sm transform transition-transform ${
              settings.useRelayOnFailure ? 'translate-x-6' : 'translate-x-0.5'
            }`} />
          </button>
        </div>
      </div>

      <div className="card p-6 space-y-6">
        <h3 className="text-lg font-semibold text-gray-800 border-b border-gray-100 pb-3">
          ⌨️ 快捷键设置
        </h3>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            快速粘贴快捷键
          </label>
          <select
            value={settings.quickPasteShortcut}
            onChange={e => handleUpdate('quickPasteShortcut', e.target.value)}
            className="input-field max-w-xs"
          >
            {shortcutOptions.map(shortcut => (
              <option key={shortcut} value={shortcut}>
                {shortcut}
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-500 mt-1">
            按下此快捷键可快速打开剪贴板历史选择器
          </p>
        </div>

        <div className="flex items-center justify-between max-w-md pt-4">
          <div>
            <div className="text-sm font-medium text-gray-700">开机自启动</div>
            <div className="text-xs text-gray-500">
              系统启动时自动运行剪贴板同步
            </div>
          </div>
          <button
            onClick={() => handleUpdate('autoStart', !settings.autoStart)}
            className={`w-12 h-6 rounded-full transition-colors ${
              settings.autoStart ? 'bg-primary-500' : 'bg-gray-300'
            }`}
          >
            <div className={`w-5 h-5 rounded-full bg-white shadow-sm transform transition-transform ${
              settings.autoStart ? 'translate-x-6' : 'translate-x-0.5'
            }`} />
          </button>
        </div>
      </div>

      <div className="card p-6 space-y-6">
        <h3 className="text-lg font-semibold text-gray-800 border-b border-gray-100 pb-3">
          📋 历史记录设置
        </h3>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            历史记录数量限制
          </label>
          <select
            value={settings.historyLimit}
            onChange={e => handleUpdate('historyLimit', parseInt(e.target.value))}
            className="input-field max-w-xs"
          >
            {historyLimitOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-500 mt-1">
            超出限制后最早的记录将被自动删除
          </p>
        </div>
      </div>

      <div className="card p-6 bg-gradient-to-r from-blue-50 to-indigo-50">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">
          ℹ️ 关于
        </h3>
        <div className="space-y-2 text-sm text-gray-600">
          <p><strong>Clipboard Sync</strong> v1.1.0</p>
          <p>一个安全的跨平台剪贴板同步工具</p>
          <ul className="list-disc list-inside space-y-1 mt-2">
            <li>支持文本、图片、文件同步</li>
            <li>端到端 AES-256-GCM 加密</li>
            <li>WebRTC 点对点传输</li>
            <li>局域网优先，速度更快</li>
            <li>图片校验和验证，确保完整性</li>
            <li>分片传输失败自动重传</li>
            <li>P2P 失败自动降级 TURN 中继</li>
            <li>SQLCipher 加密存储历史记录</li>
            <li>密码派生密钥保护数据安全</li>
            <li>历史记录可回溯</li>
            <li>快捷键快速粘贴</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

export default SettingsPage
