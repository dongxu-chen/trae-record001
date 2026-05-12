import { useState, useEffect, useRef } from 'react'
import * as THREE from 'three'
import { VRButton } from 'three/examples/jsm/webxr/VRButton.js'
import useStore from '../store/store'
import './ARView.css'

function ARFallback() {
  return (
    <div className="ar-fallback">
      <div className="ar-fallback-icon">📱</div>
      <h3>AR 模拟模式</h3>
      <p>WebXR AR 在桌面端不可用</p>
      <p className="ar-hint">已启用 AR 模拟模式，场景背景设为透明</p>
    </div>
  )
}

export default function ARView() {
  const [isXrAvailable, setIsXrAvailable] = useState(null)
  const [isArActive, setIsArActive] = useState(false)
  const [showFallback, setShowFallback] = useState(false)
  const arMode = useStore((state) => state.arMode)
  const setArMode = useStore((state) => state.setArMode)
  const vrButtonRef = useRef(null)
  const containerRef = useRef(null)

  useEffect(() => {
    const checkXrSupport = async () => {
      try {
        if (navigator.xr) {
          const vrSupported = await navigator.xr.isSessionSupported('immersive-vr')
          const arSupported = await navigator.xr.isSessionSupported('immersive-ar')
          setIsXrAvailable(vrSupported || arSupported)
        } else {
          setIsXrAvailable(false)
        }
      } catch (error) {
        console.warn('XR support check failed:', error)
        setIsXrAvailable(false)
      }
    }
    
    checkXrSupport()
  }, [])

  useEffect(() => {
    if (containerRef.current && isXrAvailable && !vrButtonRef.current) {
      const dummyRenderer = {
        xr: {
          isPresenting: false,
          setSession: () => {},
          enabled: false,
          dispose: () => {},
        },
        domElement: document.createElement('canvas'),
      }
      
      const button = VRButton.createButton(dummyRenderer)
      button.style.position = 'absolute'
      button.style.top = '20px'
      button.style.left = '20px'
      button.style.zIndex = '100'
      button.style.display = 'none'
      containerRef.current.appendChild(button)
      vrButtonRef.current = button
    }
    
    return () => {
      if (vrButtonRef.current && containerRef.current) {
        containerRef.current.removeChild(vrButtonRef.current)
        vrButtonRef.current = null
      }
    }
  }, [isXrAvailable])

  const handleToggleAR = () => {
    if (isXrAvailable) {
      setIsArActive(!isArActive)
      setArMode(!isArActive)
    } else {
      setIsArActive(!isArActive)
      setArMode(!isArActive)
      if (!isArActive) {
        setShowFallback(true)
        setTimeout(() => setShowFallback(false), 4000)
      }
    }
  }

  return (
    <div ref={containerRef}>
      <button
        className={`ar-toggle-btn ${isArActive ? 'active' : ''}`}
        onClick={handleToggleAR}
        title={isXrAvailable ? '切换 AR/VR 模式' : '启用 AR 模拟模式'}
      >
        <span className="ar-icon">🕶️</span>
        <span className="ar-text">{isArActive ? '退出 AR' : 'AR 预览'}</span>
      </button>
      
      {showFallback && (
        <div className="ar-fallback-overlay">
          <ARFallback />
        </div>
      )}
    </div>
  )
}
