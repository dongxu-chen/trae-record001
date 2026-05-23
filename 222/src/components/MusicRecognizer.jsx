import { useState, useRef } from 'react'
import { AudioRecorder, AudioFingerprinter, blobToAudioBuffer } from '../utils/audioFingerprint'

export default function MusicRecognizer({ playlist, onMatchFound }) {
  const [showModal, setShowModal] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [result, setResult] = useState(null)
  const [status, setStatus] = useState('idle')
  
  const recorderRef = useRef(null)
  const fingerprinterRef = useRef(null)
  const timerRef = useRef(null)

  const initFingerprinter = async () => {
    if (!fingerprinterRef.current) {
      fingerprinterRef.current = new AudioFingerprinter()
      
      for (const song of playlist) {
        if (song.file && !song.fingerprint) {
          try {
            const fp = await fingerprinterRef.current.generateFingerprintFromFile(song.file)
            song.fingerprint = fp
            fingerprinterRef.current.addToLibrary(song.id, fp, {
              name: song.name,
              duration: song.duration
            })
          } catch (err) {
            console.log('生成指纹失败:', song.name)
          }
        } else if (song.fingerprint) {
          fingerprinterRef.current.addToLibrary(song.id, song.fingerprint, {
            name: song.name,
            duration: song.duration
          })
        }
      }
    }
    return fingerprinterRef.current
  }

  const startRecording = async () => {
    await initFingerprinter()
    
    recorderRef.current = new AudioRecorder()
    const success = await recorderRef.current.start()
    
    if (success) {
      setIsRecording(true)
      setRecordingTime(0)
      setResult(null)
      setStatus('recording')
      
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => {
          if (prev >= 5) {
            stopRecording()
            return prev
          }
          return prev + 1
        })
      }, 1000)
    } else {
      setStatus('error')
    }
  }

  const stopRecording = async () => {
    if (!recorderRef.current) return
    
    clearInterval(timerRef.current)
    setIsRecording(false)
    setStatus('processing')
    
    try {
      const audioBlob = await recorderRef.current.stop()
      const audioBuffer = await blobToAudioBuffer(audioBlob)
      
      const recordedFp = await fingerprinterRef.current.generateFingerprint(audioBuffer)
      const match = await fingerprinterRef.current.identify(recordedFp, 0.5)
      
      if (match) {
        setResult({
          ...match.metadata,
          score: match.score,
          songId: match.songId
        })
        setStatus('success')
        
        if (onMatchFound) {
          onMatchFound(match.songId)
        }
      } else {
        setResult(null)
        setStatus('no-match')
      }
    } catch (err) {
      console.error('识别失败:', err)
      setStatus('error')
    }
    
    recorderRef.current = null
  }

  const handleClose = () => {
    if (isRecording) {
      clearInterval(timerRef.current)
      recorderRef.current?.stop()
    }
    setShowModal(false)
    setResult(null)
    setStatus('idle')
    setRecordingTime(0)
  }

  return (
    <>
      <button className="recognizer-btn" onClick={() => setShowModal(true)}>
        <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
          <path d="M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z"/>
        </svg>
        听歌识曲
      </button>

      {showModal && (
        <div className="modal-overlay" onClick={handleClose}>
          <div className="modal-content recognizer-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>🎤 听歌识曲</h3>
              <button className="close-btn" onClick={handleClose}>
                <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                  <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                </svg>
              </button>
            </div>

            <div className="recognizer-body">
              <div className={`recording-indicator ${isRecording ? 'active' : ''}`}>
                <div className="wave-animation">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="wave-bar" style={{ animationDelay: `${i * 0.1}s` }} />
                  ))}
                </div>
              </div>

              {status === 'idle' && (
                <div className="recognizer-hint">
                  <p>点击按钮开始录制</p>
                  <small>请确保环境安静，录制5-10秒</small>
                </div>
              )}

              {status === 'recording' && (
                <div className="recognizer-status">
                  <p>正在录制... {recordingTime}s</p>
                  <small>对准音源以获得更好效果</small>
                </div>
              )}

              {status === 'processing' && (
                <div className="recognizer-status">
                  <div className="spinner" />
                  <p>正在识别...</p>
                </div>
              )}

              {status === 'success' && result && (
                <div className="recognizer-result success">
                  <div className="result-icon">✓</div>
                  <h4>{result.name}</h4>
                  <p>匹配度: {Math.round(result.score * 100)}%</p>
                  <button 
                    className="play-match-btn"
                    onClick={() => {
                      onMatchFound?.(result.songId)
                      handleClose()
                    }}
                  >
                    播放这首歌
                  </button>
                </div>
              )}

              {status === 'no-match' && (
                <div className="recognizer-result no-match">
                  <div className="result-icon">?</div>
                  <h4>未找到匹配歌曲</h4>
                  <p>请确认歌曲已添加到播放列表</p>
                </div>
              )}

              {status === 'error' && (
                <div className="recognizer-result error">
                  <div className="result-icon">!</div>
                  <h4>识别失败</h4>
                  <p>请检查麦克风权限并重试</p>
                </div>
              )}

              {playlist.length === 0 && (
                <div className="library-hint">
                  <p>当前歌库为空</p>
                  <small>请先添加音乐到播放列表</small>
                </div>
              )}
            </div>

            <div className="recognizer-actions">
              {!isRecording && status !== 'processing' && (
                <button 
                  className="record-btn"
                  onClick={startRecording}
                  disabled={playlist.length === 0}
                >
                  <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
                    <path d="M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z"/>
                  </svg>
                  开始识别
                </button>
              )}
              {isRecording && (
                <button className="stop-btn" onClick={stopRecording}>
                  停止识别
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
