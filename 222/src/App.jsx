import { useState, useRef, useEffect, useCallback } from 'react'
import Visualizer from './components/Visualizer'
import Equalizer from './components/Equalizer'
import LyricsDisplay from './components/LyricsDisplay'
import Playlist from './components/Playlist'
import FloatingLyrics from './components/FloatingLyrics'
import PlaylistManager from './components/PlaylistManager'
import MusicRecognizer from './components/MusicRecognizer'
import { formatTime, getAudioDuration } from './utils/audioUtils'
import { parseLRC } from './utils/lrcParser'

const PLAY_MODES = {
  SEQUENCE: 'sequence',
  SHUFFLE: 'shuffle',
  LOOP: 'loop'
}

const PLAY_MODE_ICONS = {
  [PLAY_MODES.SEQUENCE]: (
    <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
      <path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4zm17-8.5v9l5-4.5z"/>
    </svg>
  ),
  [PLAY_MODES.SHUFFLE]: (
    <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
      <path d="M10.59 9.17L5.41 4 4 5.41l5.17 5.17 1.42-1.41zM14.5 4l2.04 2.04L4 18.59 5.41 20 17.96 7.46 20 9.5V4h-5.5zm.33 9.41l-1.41 1.41 3.13 3.13L14.5 20H20v-5.5l-2.04 2.04-3.13-3.13z"/>
    </svg>
  ),
  [PLAY_MODES.LOOP]: (
    <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
      <path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
    </svg>
  )
}

export default function App() {
  const [playlist, setPlaylist] = useState([])
  const [currentIndex, setCurrentIndex] = useState(-1)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(0.7)
  const [playMode, setPlayMode] = useState(PLAY_MODES.SEQUENCE)
  const [lyrics, setLyrics] = useState([])
  const [eqBands, setEqBands] = useState({ low: 0, mid: 0, high: 0 })
  const [showFloatingLyrics, setShowFloatingLyrics] = useState(false)

  const audioRef = useRef(null)
  const audioContextRef = useRef(null)
  const analyserRef = useRef(null)
  const sourceRef = useRef(null)
  const gainNodeRef = useRef(null)
  const eqNodesRef = useRef({})
  const isAudioContextInitialized = useRef(false)
  const touchStartRef = useRef(null)
  const lastTapRef = useRef(0)

  const currentSong = currentIndex >= 0 ? playlist[currentIndex] : null

  const initAudioContext = useCallback(() => {
    if (isAudioContextInitialized.current) return

    const AudioContext = window.AudioContext || window.webkitAudioContext
    audioContextRef.current = new AudioContext()
    
    analyserRef.current = audioContextRef.current.createAnalyser()
    analyserRef.current.fftSize = 512
    analyserRef.current.smoothingTimeConstant = 0.8

    gainNodeRef.current = audioContextRef.current.createGain()
    gainNodeRef.current.gain.value = volume

    eqNodesRef.current = {
      low: audioContextRef.current.createBiquadFilter(),
      mid: audioContextRef.current.createBiquadFilter(),
      high: audioContextRef.current.createBiquadFilter()
    }

    eqNodesRef.current.low.type = 'lowshelf'
    eqNodesRef.current.low.frequency.value = 80
    eqNodesRef.current.low.gain.value = eqBands.low

    eqNodesRef.current.mid.type = 'peaking'
    eqNodesRef.current.mid.frequency.value = 1000
    eqNodesRef.current.mid.Q.value = 0.7
    eqNodesRef.current.mid.gain.value = eqBands.mid

    eqNodesRef.current.high.type = 'highshelf'
    eqNodesRef.current.high.frequency.value = 5000
    eqNodesRef.current.high.gain.value = eqBands.high

    isAudioContextInitialized.current = true
  }, [volume, eqBands])

  const connectAudioNodes = useCallback(() => {
    if (!audioRef.current || !isAudioContextInitialized.current) return

    if (sourceRef.current) {
      sourceRef.current.disconnect()
    }

    sourceRef.current = audioContextRef.current.createMediaElementSource(audioRef.current)
    
    sourceRef.current
      .connect(eqNodesRef.current.low)
      .connect(eqNodesRef.current.mid)
      .connect(eqNodesRef.current.high)
      .connect(gainNodeRef.current)
      .connect(analyserRef.current)
      .connect(audioContextRef.current.destination)
  }, [])

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files)
    const audioFiles = files.filter(f => f.type.startsWith('audio/'))
    const lrcFiles = files.filter(f => f.name.endsWith('.lrc'))

    const lrcMap = new Map()
    lrcFiles.forEach(lrcFile => {
      const baseName = lrcFile.name.replace('.lrc', '')
      lrcMap.set(baseName, lrcFile)
    })

    const newSongs = []
    for (const file of audioFiles) {
      const songDuration = await getAudioDuration(file)
      const baseName = file.name.replace(/\.[^/.]+$/, '')
      
      let songLyrics = []
      if (lrcMap.has(baseName)) {
        const lrcText = await lrcMap.get(baseName).text()
        songLyrics = parseLRC(lrcText)
      }

      newSongs.push({
        id: Date.now() + Math.random(),
        name: baseName,
        file,
        url: URL.createObjectURL(file),
        duration: songDuration,
        lyrics: songLyrics
      })
    }

    setPlaylist(prev => [...prev, ...newSongs])
    
    if (currentIndex === -1 && newSongs.length > 0) {
      setCurrentIndex(0)
    }

    e.target.value = ''
  }

  const handleSelectSong = (index) => {
    setCurrentIndex(index)
    setLyrics(playlist[index].lyrics || [])
    setIsPlaying(true)
  }

  const handleDeleteSong = (index) => {
    const song = playlist[index]
    if (song.url) {
      URL.revokeObjectURL(song.url)
    }
    
    setPlaylist(prev => prev.filter((_, i) => i !== index))
    
    if (index === currentIndex) {
      setIsPlaying(false)
      setCurrentIndex(-1)
      setLyrics([])
    } else if (index < currentIndex) {
      setCurrentIndex(prev => prev - 1)
    }
  }

  const togglePlay = () => {
    if (!audioRef.current || !currentSong) return

    initAudioContext()

    if (audioContextRef.current.state === 'suspended') {
      audioContextRef.current.resume()
    }

    if (!sourceRef.current) {
      connectAudioNodes()
    }

    if (isPlaying) {
      audioRef.current.pause()
    } else {
      audioRef.current.play()
    }
    setIsPlaying(!isPlaying)
  }

  const playNext = () => {
    if (playlist.length === 0) return

    let nextIndex
    if (playMode === PLAY_MODES.SHUFFLE) {
      nextIndex = Math.floor(Math.random() * playlist.length)
    } else {
      nextIndex = (currentIndex + 1) % playlist.length
    }
    
    setCurrentIndex(nextIndex)
    setLyrics(playlist[nextIndex].lyrics || [])
    setIsPlaying(true)
  }

  const playPrevious = () => {
    if (playlist.length === 0) return

    if (currentTime > 3) {
      audioRef.current.currentTime = 0
      return
    }

    let prevIndex
    if (playMode === PLAY_MODES.SHUFFLE) {
      prevIndex = Math.floor(Math.random() * playlist.length)
    } else {
      prevIndex = (currentIndex - 1 + playlist.length) % playlist.length
    }
    
    setCurrentIndex(prevIndex)
    setLyrics(playlist[prevIndex].lyrics || [])
    setIsPlaying(true)
  }

  const togglePlayMode = () => {
    const modes = Object.values(PLAY_MODES)
    const currentModeIndex = modes.indexOf(playMode)
    const nextModeIndex = (currentModeIndex + 1) % modes.length
    setPlayMode(modes[nextModeIndex])
  }

  const handleSeek = (e) => {
    if (!audioRef.current) return
    const rect = e.currentTarget.getBoundingClientRect()
    const percent = (e.clientX - rect.left) / rect.width
    const newTime = percent * duration
    audioRef.current.currentTime = newTime
    setCurrentTime(newTime)
  }

  const handleVolumeChange = (e) => {
    const newVolume = parseFloat(e.target.value)
    setVolume(newVolume)
    if (gainNodeRef.current) {
      gainNodeRef.current.gain.value = newVolume
    }
  }

  const handleEqChange = (band, value) => {
    setEqBands(prev => ({ ...prev, [band]: value }))
    if (eqNodesRef.current[band]) {
      eqNodesRef.current[band].gain.value = value
    }
  }

  const handleMatchFound = (songId) => {
    const index = playlist.findIndex(s => s.id === songId)
    if (index !== -1) {
      handleSelectSong(index)
    }
  }

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handleTimeUpdate = () => setCurrentTime(audio.currentTime)
    const handleLoadedMetadata = () => setDuration(audio.duration)
    const handleEnded = () => {
      if (playMode === PLAY_MODES.LOOP) {
        audio.currentTime = 0
        audio.play()
      } else {
        playNext()
      }
    }

    audio.addEventListener('timeupdate', handleTimeUpdate)
    audio.addEventListener('loadedmetadata', handleLoadedMetadata)
    audio.addEventListener('ended', handleEnded)

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate)
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata)
      audio.removeEventListener('ended', handleEnded)
    }
  }, [playMode, currentIndex])

  useEffect(() => {
    if (audioRef.current && currentSong) {
      audioRef.current.src = currentSong.url
      setLyrics(currentSong.lyrics || [])
      
      if (isPlaying) {
        initAudioContext()
        if (!sourceRef.current) {
          connectAudioNodes()
        }
        if (audioContextRef.current.state === 'suspended') {
          audioContextRef.current.resume()
        }
        audioRef.current.play().catch(() => {})
      }
    }
  }, [currentIndex])

  const handleGlobalInteraction = useCallback(() => {
    if (!isAudioContextInitialized.current) {
      initAudioContext()
    }
    if (audioContextRef.current?.state === 'suspended') {
      audioContextRef.current.resume()
    }
  }, [initAudioContext])

  const handleTouchStart = useCallback((e) => {
    touchStartRef.current = {
      x: e.touches[0].clientX,
      y: e.touches[0].clientY,
      time: Date.now()
    }
    handleGlobalInteraction()
  }, [handleGlobalInteraction])

  const handleTouchEnd = useCallback((e) => {
    if (!touchStartRef.current) return

    const touch = e.changedTouches[0]
    const deltaX = touch.clientX - touchStartRef.current.x
    const deltaY = touch.clientY - touchStartRef.current.y
    const deltaTime = Date.now() - touchStartRef.current.time

    if (deltaTime < 300 && Math.abs(deltaX) < 10 && Math.abs(deltaY) < 10) {
      const now = Date.now()
      if (now - lastTapRef.current < 300) {
        if (isPlaying) {
          audioRef.current?.pause()
          setIsPlaying(false)
        } else if (currentSong) {
          audioRef.current?.play()
          setIsPlaying(true)
        }
      }
      lastTapRef.current = now
    }

    if (Math.abs(deltaY) < 50) {
      if (deltaX > 50) {
        playPrevious()
      } else if (deltaX < -50) {
        playNext()
      }
    }

    touchStartRef.current = null
  }, [isPlaying, currentSong])

  const handleClick = useCallback(() => {
    handleGlobalInteraction()
  }, [handleGlobalInteraction])

  useEffect(() => {
    document.addEventListener('touchstart', handleTouchStart, { passive: true })
    document.addEventListener('touchend', handleTouchEnd, { passive: true })
    document.addEventListener('click', handleClick)

    return () => {
      document.removeEventListener('touchstart', handleTouchStart)
      document.removeEventListener('touchend', handleTouchEnd)
      document.removeEventListener('click', handleClick)
    }
  }, [handleTouchStart, handleTouchEnd, handleClick])

  useEffect(() => {
    return () => {
      playlist.forEach(song => {
        if (song.url) URL.revokeObjectURL(song.url)
      })
    }
  }, [])

  return (
    <div className="app">
      <div className="header">
        <h1>🎵 音乐播放器</h1>
        <p>支持本地音乐上传 · 歌词显示 · 音频可视化 · 均衡器</p>
      </div>

      <div className="main-container">
        <div className="player-panel">
          <div className={`album-cover ${isPlaying ? 'playing' : ''}`}>
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
            </svg>
          </div>

          <div className="song-info">
            <div className="title">{currentSong?.name || '未选择歌曲'}</div>
            <div className="artist">{currentSong ? '本地音乐' : '请上传音乐开始播放'}</div>
          </div>

          <Visualizer 
            audioContext={audioContextRef.current}
            analyser={analyserRef.current}
            isPlaying={isPlaying}
          />

          <div className="progress-container">
            <div className="progress-bar" onClick={handleSeek}>
              <div 
                className="progress" 
                style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }}
              />
            </div>
            <div className="time-display">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>

          <div className="controls">
            <button 
              className={`control-btn mode-btn ${playMode !== PLAY_MODES.SEQUENCE ? 'active' : ''}`}
              onClick={togglePlayMode}
              title={`播放模式: ${playMode === PLAY_MODES.SEQUENCE ? '顺序' : playMode === PLAY_MODES.SHUFFLE ? '随机' : '单曲循环'}`}
            >
              {PLAY_MODE_ICONS[playMode]}
            </button>
            
            <button className="control-btn" onClick={playPrevious}>
              <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
                <path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/>
              </svg>
            </button>
            
            <button className="control-btn play-btn" onClick={togglePlay}>
              {isPlaying ? (
                <svg viewBox="0 0 24 24" fill="currentColor" width="30" height="30">
                  <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" fill="currentColor" width="30" height="30">
                  <path d="M8 5v14l11-7z"/>
                </svg>
              )}
            </button>
            
            <button className="control-btn" onClick={playNext}>
              <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
                <path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/>
              </svg>
            </button>
            
            <button 
              className={`control-btn ${showFloatingLyrics ? 'active' : ''}`}
              onClick={() => setShowFloatingLyrics(!showFloatingLyrics)}
              title="桌面歌词"
            >
              <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
              </svg>
            </button>
          </div>

          <div className="extra-controls">
            <PlaylistManager playlist={playlist} />
            <MusicRecognizer playlist={playlist} onMatchFound={handleMatchFound} />
          </div>

          <div className="volume-control">
            <svg viewBox="0 0 24 24" fill="currentColor">
              {volume === 0 ? (
                <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>
              ) : volume < 0.5 ? (
                <path d="M18.5 12c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM5 9v6h4l5 5V4L9 9H5z"/>
              ) : (
                <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
              )}
            </svg>
            <input
              type="range"
              className="volume-slider"
              min="0"
              max="1"
              step="0.01"
              value={volume}
              onChange={handleVolumeChange}
            />
            <span className="volume-value">{Math.round(volume * 100)}%</span>
          </div>

          <Equalizer eqBands={eqBands} onEqChange={handleEqChange} />
          
          <LyricsDisplay lyrics={lyrics} currentTime={currentTime} />
        </div>

        <Playlist
          playlist={playlist}
          currentIndex={currentIndex}
          onSelectSong={handleSelectSong}
          onDeleteSong={handleDeleteSong}
          onUpload={handleFileUpload}
        />
      </div>

      {showFloatingLyrics && (
        <FloatingLyrics
          lyrics={lyrics}
          currentTime={currentTime}
          isPlaying={isPlaying}
          onClose={() => setShowFloatingLyrics(false)}
        />
      )}

      <audio ref={audioRef} />
    </div>
  )
}
