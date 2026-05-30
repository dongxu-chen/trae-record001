import React, { useState, useEffect } from 'react'
import { CaptchaProvider, useCaptcha } from './contexts/CaptchaContext'
import SlideCaptcha from './components/SlideCaptcha'
import RotateCaptcha from './components/RotateCaptcha'
import ClickCaptcha from './components/ClickCaptcha'
import VoiceCaptcha from './components/VoiceCaptcha'
import CaptchaStats from './components/CaptchaStats'
import './App.css'

const CaptchaCard = ({ title, description, type, CaptchaComponent }) => {
  const { handleVerifySuccess, handleVerifyError, isLocked, getRemainingLockTime } = useCaptcha()
  const [result, setResult] = useState(null)
  const [lockTime, setLockTime] = useState(0)

  useEffect(() => {
    if (isLocked) {
      const interval = setInterval(() => {
        setLockTime(getRemainingLockTime())
      }, 1000)
      return () => clearInterval(interval)
    } else {
      setLockTime(0)
    }
  }, [isLocked, getRemainingLockTime])

  const handleSuccess = (captchaId) => {
    setResult({ type: 'success', message: '验证成功！' })
    handleVerifySuccess(captchaId)
  }

  const handleError = (errorData) => {
    setResult({ type: 'error', message: errorData?.message || '验证失败' })
    handleVerifyError(errorData)
  }

  return (
    <div className="captcha-card">
      <h2>{title}</h2>
      <p className="description">{description}</p>

      {isLocked ? (
        <div className="lock-warning">
          <div className="lock-icon">🔒</div>
          <p>操作过于频繁，请 {lockTime} 秒后再试</p>
        </div>
      ) : (
        <div className="captcha-wrapper">
          <CaptchaComponent
            onSuccess={handleSuccess}
            onError={handleError}
          />
        </div>
      )}

      {result && !isLocked && (
        <div className={`verification-result ${result.type}`}>
          {result.message}
        </div>
      )}
    </div>
  )
}

const AppContent = () => {
  const { globalErrorCount, maxErrors, isLocked, getRemainingLockTime } = useCaptcha()
  const [lockTime, setLockTime] = useState(0)
  const [activeTab, setActiveTab] = useState('all')

  useEffect(() => {
    if (isLocked) {
      const interval = setInterval(() => {
        setLockTime(getRemainingLockTime())
      }, 1000)
      return () => clearInterval(interval)
    }
  }, [isLocked, getRemainingLockTime])

  const captchaTypes = [
    {
      key: 'slide',
      title: '🧩 拼图滑块',
      description: '拖动拼图滑块到正确的位置完成验证，有效防御机器识别。',
      type: 'slide',
      CaptchaComponent: SlideCaptcha,
    },
    {
      key: 'rotate',
      title: '🔄 旋转图片',
      description: '拖动滑块旋转图片至正确角度，利用人类空间感知能力。',
      type: 'rotate',
      CaptchaComponent: RotateCaptcha,
    },
    {
      key: 'click',
      title: '👆 点选文字',
      description: '按照提示顺序点击图中的文字，结合视觉识别与记忆。',
      type: 'click',
      CaptchaComponent: ClickCaptcha,
    },
    {
      key: 'voice',
      title: '🔊 语音验证',
      description: '无障碍模式，播放语音验证码，支持视觉障碍用户使用。',
      type: 'voice',
      CaptchaComponent: VoiceCaptcha,
    },
  ]

  const showStats = activeTab === 'stats'
  const filteredTypes = activeTab === 'all'
    ? captchaTypes
    : captchaTypes.filter(t => t.key === activeTab)

  return (
    <div className="app-container">
      <header className="page-header">
        <h1>🎯 Web端图形验证码组件</h1>
        <p>多种验证方式 · 前后端双重校验 · 防暴力破解 · 无障碍支持</p>

        <div className="status-bar">
          <div className="status-item">
            <span className="status-label">错误次数:</span>
            <span className={`status-value ${globalErrorCount > maxErrors * 0.6 ? 'warning' : ''}`}>
              {globalErrorCount} / {maxErrors}
            </span>
          </div>
          {isLocked && (
            <div className="status-item locked">
              <span className="status-label">🔒 锁定剩余:</span>
              <span className="status-value">{lockTime}秒</span>
            </div>
          )}
        </div>

        <div className="tab-nav">
          <button
            className={`tab-btn ${activeTab === 'all' ? 'active' : ''}`}
            onClick={() => setActiveTab('all')}
          >
            全部
          </button>
          {captchaTypes.map(type => (
            <button
              key={type.key}
              className={`tab-btn ${activeTab === type.key ? 'active' : ''}`}
              onClick={() => setActiveTab(type.key)}
            >
              {type.title.split(' ')[0]}
            </button>
          ))}
          <button
            className={`tab-btn ${activeTab === 'stats' ? 'active' : ''}`}
            onClick={() => setActiveTab('stats')}
          >
            📊 统计
          </button>
        </div>
      </header>

      <main className="captcha-demo-container">
        {showStats ? (
          <CaptchaStats />
        ) : (
          filteredTypes.map(captcha => (
            <CaptchaCard
              key={captcha.key}
              title={captcha.title}
              description={captcha.description}
              type={captcha.type}
              CaptchaComponent={captcha.CaptchaComponent}
            />
          ))
        )}
      </main>

      <footer className="page-footer">
        <div className="feature-list">
          <div className="feature-item">
            <span className="feature-icon">🛡️</span>
            <span>防暴力破解</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">♿</span>
            <span>无障碍支持</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">🔐</span>
            <span>前后端校验</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">📱</span>
            <span>移动端适配</span>
          </div>
        </div>
        <p className="copyright">© 2024 Captcha System - 基于 React + Node.js + Canvas 构建</p>
      </footer>
    </div>
  )
}

const App = () => {
  return (
    <CaptchaProvider>
      <AppContent />
    </CaptchaProvider>
  )
}

export default App
