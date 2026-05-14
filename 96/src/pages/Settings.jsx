import { useState, useEffect } from 'react'
import useLocalStorage from '../hooks/useLocalStorage'
import { 
  configureFirebase, 
  signIn, 
  signUp, 
  signInWithGoogle, 
  signOut, 
  getCurrentUser, 
  onAuthChange,
  syncToCloud,
  syncFromCloud,
  isFirebaseConfigured,
  getFirebaseConfigFromStorage
} from '../utils/sync'
import { getNotificationPermission, requestNotificationPermission } from '../utils/notify'

function Settings() {
  const [settings, setSettings] = useLocalStorage('pomodoro_settings', {
    workDuration: 25,
    shortBreakDuration: 5,
    longBreakDuration: 15,
    longBreakInterval: 4,
    autoStartBreaks: true,
    autoStartPomodoros: false,
    notificationsEnabled: true,
    soundEnabled: true
  })

  const [user, setUser] = useState(null)
  const [loginMode, setLoginMode] = useState('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [syncing, setSyncing] = useState(false)

  const [firebaseConfig, setFirebaseConfig] = useState(() => {
    const saved = getFirebaseConfigFromStorage()
    return saved || {
      apiKey: '',
      authDomain: '',
      projectId: '',
      storageBucket: '',
      messagingSenderId: '',
      appId: ''
    }
  })
  const [showFirebaseConfig, setShowFirebaseConfig] = useState(!isFirebaseConfigured())
  const [notificationPermission, setNotificationPermission] = useState('default')

  useEffect(() => {
    const unsubscribe = onAuthChange((authUser) => {
      setUser(authUser)
    })
    return () => unsubscribe()
  }, [])

  useEffect(() => {
    setNotificationPermission(getNotificationPermission())
  }, [])

  const handleSettingChange = (key, value) => {
    setSettings({ ...settings, [key]: value })
  }

  const handleFirebaseConfigChange = (key, value) => {
    setFirebaseConfig(prev => ({ ...prev, [key]: value }))
  }

  const handleSaveFirebaseConfig = () => {
    if (firebaseConfig.apiKey && firebaseConfig.projectId) {
      configureFirebase(firebaseConfig)
      setShowFirebaseConfig(false)
    }
  }

  const handleSignIn = async () => {
    setError('')
    try {
      await signIn(email, password)
      await syncFromCloud()
      window.location.reload()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleSignUp = async () => {
    setError('')
    try {
      await signUp(email, password)
      await syncToCloud()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleGoogleSignIn = async () => {
    setError('')
    try {
      await signInWithGoogle()
      await syncFromCloud()
      window.location.reload()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleSignOut = async () => {
    await signOut()
    setUser(null)
  }

  const handleManualSync = async () => {
    setSyncing(true)
    try {
      await syncToCloud()
      await syncFromCloud()
    } finally {
      setSyncing(false)
    }
  }

  const handleRequestNotificationPermission = async () => {
    const result = await requestNotificationPermission()
    setNotificationPermission(result)
  }

  const formatDuration = (minutes) => {
    return `${minutes} 分钟`
  }

  return (
    <div className="settings-page">
      <h1 className="settings-title">⚙️ 设置</h1>

      <div className="settings-section">
        <h2 className="section-title">⏱️ 番茄时间设置</h2>
        
        <div className="setting-item">
          <label className="setting-label">
            专注时长（分钟）
            <span className="setting-value">{formatDuration(settings.workDuration)}</span>
          </label>
          <input
            type="range"
            min="1"
            max="60"
            value={settings.workDuration}
            onChange={(e) => handleSettingChange('workDuration', parseInt(e.target.value))}
            className="setting-slider"
          />
        </div>

        <div className="setting-item">
          <label className="setting-label">
            短休息时长（分钟）
            <span className="setting-value">{formatDuration(settings.shortBreakDuration)}</span>
          </label>
          <input
            type="range"
            min="1"
            max="30"
            value={settings.shortBreakDuration}
            onChange={(e) => handleSettingChange('shortBreakDuration', parseInt(e.target.value))}
            className="setting-slider"
          />
        </div>

        <div className="setting-item">
          <label className="setting-label">
            长休息时长（分钟）
            <span className="setting-value">{formatDuration(settings.longBreakDuration)}</span>
          </label>
          <input
            type="range"
            min="5"
            max="60"
            value={settings.longBreakDuration}
            onChange={(e) => handleSettingChange('longBreakDuration', parseInt(e.target.value))}
            className="setting-slider"
          />
        </div>

        <div className="setting-item">
          <label className="setting-label">
            长休息间隔（番茄数）
            <span className="setting-value">每 {settings.longBreakInterval} 个番茄</span>
          </label>
          <input
            type="range"
            min="2"
            max="8"
            value={settings.longBreakInterval}
            onChange={(e) => handleSettingChange('longBreakInterval', parseInt(e.target.value))}
            className="setting-slider"
          />
        </div>

        <div className="setting-item checkbox">
          <label className="setting-label">
            <input
              type="checkbox"
              checked={settings.autoStartBreaks}
              onChange={(e) => handleSettingChange('autoStartBreaks', e.target.checked)}
            />
            自动开始休息
          </label>
        </div>

        <div className="setting-item checkbox">
          <label className="setting-label">
            <input
              type="checkbox"
              checked={settings.autoStartPomodoros}
              onChange={(e) => handleSettingChange('autoStartPomodoros', e.target.checked)}
            />
            自动开始下一个番茄
          </label>
        </div>

        <div className="setting-item checkbox">
          <label className="setting-label">
            <input
              type="checkbox"
              checked={settings.soundEnabled}
              onChange={(e) => handleSettingChange('soundEnabled', e.target.checked)}
            />
            启用提示音
          </label>
        </div>

        <div className="setting-item">
          <label className="setting-label">
            浏览器通知
            <span className={`permission-status ${notificationPermission}`}>
              {notificationPermission === 'granted' ? '✅ 已允许' : 
               notificationPermission === 'denied' ? '❌ 已拒绝' : '⏳ 默认'}
            </span>
          </label>
          {notificationPermission !== 'granted' && (
            <button 
              className="permission-btn"
              onClick={handleRequestNotificationPermission}
            >
              请求通知权限
            </button>
          )}
        </div>
      </div>

      <div className="settings-section">
        <h2 className="section-title">☁️ 云端同步</h2>

        <button 
          className="toggle-config-btn"
          onClick={() => setShowFirebaseConfig(!showFirebaseConfig)}
        >
          {showFirebaseConfig ? '隐藏 Firebase 配置' : '⚙️ 配置 Firebase'}
        </button>

        {showFirebaseConfig && (
          <div className="firebase-config-form">
            <p className="config-hint">
              请在 <a href="https://console.firebase.google.com/" target="_blank" rel="noopener noreferrer">
                Firebase 控制台
              </a> 创建项目并获取配置信息
            </p>
            
            <div className="config-fields">
              <input
                type="text"
                placeholder="API Key"
                value={firebaseConfig.apiKey}
                onChange={(e) => handleFirebaseConfigChange('apiKey', e.target.value)}
                className="config-input"
              />
              <input
                type="text"
                placeholder="Auth Domain"
                value={firebaseConfig.authDomain}
                onChange={(e) => handleFirebaseConfigChange('authDomain', e.target.value)}
                className="config-input"
              />
              <input
                type="text"
                placeholder="Project ID"
                value={firebaseConfig.projectId}
                onChange={(e) => handleFirebaseConfigChange('projectId', e.target.value)}
                className="config-input"
              />
              <input
                type="text"
                placeholder="Storage Bucket"
                value={firebaseConfig.storageBucket}
                onChange={(e) => handleFirebaseConfigChange('storageBucket', e.target.value)}
                className="config-input"
              />
              <input
                type="text"
                placeholder="Messaging Sender ID"
                value={firebaseConfig.messagingSenderId}
                onChange={(e) => handleFirebaseConfigChange('messagingSenderId', e.target.value)}
                className="config-input"
              />
              <input
                type="text"
                placeholder="App ID"
                value={firebaseConfig.appId}
                onChange={(e) => handleFirebaseConfigChange('appId', e.target.value)}
                className="config-input"
              />
            </div>

            <button 
              className="save-config-btn"
              onClick={handleSaveFirebaseConfig}
            >
              保存配置
            </button>
          </div>
        )}

        {isFirebaseConfigured() && (
          <div className="auth-section">
            {user ? (
              <div className="user-info">
                <div className="user-avatar">
                  {user.photoURL ? (
                    <img src={user.photoURL} alt="头像" />
                  ) : (
                    <span>{user.email?.[0]?.toUpperCase() || 'U'}</span>
                  )}
                </div>
                <div className="user-details">
                  <span className="user-email">{user.email}</span>
                  <span className="user-uid">UID: {user.uid}</span>
                </div>
                <div className="sync-buttons">
                  <button 
                    className="sync-btn"
                    onClick={handleManualSync}
                    disabled={syncing}
                  >
                    {syncing ? '🔄 同步中...' : '🔄 立即同步'}
                  </button>
                  <button 
                    className="signout-btn"
                    onClick={handleSignOut}
                  >
                    退出登录
                  </button>
                </div>
              </div>
            ) : (
              <div className="auth-form">
                <div className="auth-tabs">
                  <button 
                    className={`auth-tab ${loginMode === 'signin' ? 'active' : ''}`}
                    onClick={() => setLoginMode('signin')}
                  >
                    登录
                  </button>
                  <button 
                    className={`auth-tab ${loginMode === 'signup' ? 'active' : ''}`}
                    onClick={() => setLoginMode('signup')}
                  >
                    注册
                  </button>
                </div>

                <input
                  type="email"
                  placeholder="邮箱"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="auth-input"
                />
                <input
                  type="password"
                  placeholder="密码"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="auth-input"
                />

                {error && <div className="auth-error">{error}</div>}

                <button 
                  className="auth-btn"
                  onClick={loginMode === 'signin' ? handleSignIn : handleSignUp}
                >
                  {loginMode === 'signin' ? '登录' : '注册'}
                </button>

                <div className="divider">或</div>

                <button 
                  className="google-btn"
                  onClick={handleGoogleSignIn}
                >
                  <svg width="20" height="20" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  使用 Google 登录
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default Settings
