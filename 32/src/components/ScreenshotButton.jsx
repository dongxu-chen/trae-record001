import { useState, useCallback } from 'react'
import { useThree } from '@react-three/fiber'
import { captureAndDownload } from '../utils/screenshot'
import './ScreenshotButton.css'

export default function ScreenshotButton() {
  const { gl } = useThree()
  const [isCapturing, setIsCapturing] = useState(false)
  const [previewUrl, setPreviewUrl] = useState(null)

  const handleCapture = useCallback(() => {
    if (!gl || isCapturing) return
    
    setIsCapturing(true)
    
    try {
      const timestamp = new Date().toISOString().slice(0, 19).replace(/[:]/g, '-')
      const filename = `product-config-${timestamp}.png`
      
      const dataUrl = captureAndDownload(gl, filename)
      setPreviewUrl(dataUrl)
      
      setTimeout(() => setIsCapturing(false), 300)
      setTimeout(() => setPreviewUrl(null), 3000)
    } catch (error) {
      console.error('Screenshot capture failed:', error)
      setIsCapturing(false)
    }
  }, [gl, isCapturing])

  return (
    <>
      <button
        className={`screenshot-btn ${isCapturing ? 'capturing' : ''}`}
        onClick={handleCapture}
        disabled={isCapturing}
        title="截取当前视图"
      >
        <span className="screenshot-icon">📷</span>
        <span className="screenshot-text">截图</span>
      </button>
      
      {previewUrl && (
        <div className="screenshot-preview">
          <div className="preview-content">
            <img src={previewUrl} alt="Screenshot preview" />
            <div className="preview-message">截图已保存</div>
          </div>
        </div>
      )}
    </>
  )
}
