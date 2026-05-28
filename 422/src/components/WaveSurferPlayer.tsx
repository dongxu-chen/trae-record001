import { useEffect, useRef, useCallback } from 'react'
import WaveSurfer from 'wavesurfer.js'

interface WaveSurferPlayerProps {
  url: string
  color?: string
  progressColor?: string
  height?: number
  waveColor?: string
  onReady?: (duration: number) => void
  onTimeUpdate?: (time: number) => void
  onPlay?: () => void
  onPause?: () => void
  interactive?: boolean
  cursorWidth?: number
  barRadius?: number
  barGap?: number
  barWidth?: number
}

export function WaveSurferPlayer({
  url,
  color = '#4ade80',
  progressColor = '#22c55e',
  height = 100,
  waveColor = '#3b82f6',
  onReady,
  onTimeUpdate,
  onPlay,
  onPause,
  interactive = true,
  cursorWidth = 2,
  barRadius = 3,
  barGap = 2,
  barWidth = 2,
}: WaveSurferPlayerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const waveSurferRef = useRef<WaveSurfer | null>(null)

  useEffect(() => {
    if (!containerRef.current || !url) return

    const ws = WaveSurfer.create({
      container: containerRef.current,
      waveColor: waveColor,
      progressColor: progressColor,
      height: height,
      cursorColor: color,
      cursorWidth: cursorWidth,
      barRadius: barRadius,
      barGap: barGap,
      barWidth: barWidth,
      normalize: true,
      interact: interactive,
    })

    waveSurferRef.current = ws

    ws.load(url)

    ws.on('ready', () => {
      onReady?.(ws.getDuration())
    })

    ws.on('audioprocess', () => {
      onTimeUpdate?.(ws.getCurrentTime())
    })

    ws.on('seeking', () => {
      onTimeUpdate?.(ws.getCurrentTime())
    })

    ws.on('play', () => onPlay?.())
    ws.on('pause', () => onPause?.())

    return () => {
      ws.destroy()
      waveSurferRef.current = null
    }
  }, [url, waveColor, progressColor, color, height, interactive, cursorWidth, barRadius, barGap, barWidth, onReady, onTimeUpdate, onPlay, onPause])

  const playPause = useCallback(() => {
    waveSurferRef.current?.playPause()
  }, [])

  const seekTo = useCallback((time: number) => {
    const ws = waveSurferRef.current
    if (!ws) return
    const duration = ws.getDuration()
    if (duration > 0) {
      ws.seekTo(time / duration)
    }
  }, [])

  const setVolume = useCallback((volume: number) => {
    waveSurferRef.current?.setVolume(volume)
  }, [])

  return (
    <div ref={containerRef} className="wavesurfer-container" style={{ minHeight: height }} />
  )
}

export { WaveSurferPlayer as default }
