import { useEffect, useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Modal } from 'antd'
import { WarningOutlined } from '@ant-design/icons'
import { RootState } from '../store'
import { recordTabSwitch, recordFullscreenExit, recordCopy, recordPaste } from '../store/examSlice'

export function useAntiCheat() {
  const dispatch = useDispatch()
  const isSubmitted = useSelector((state: RootState) => state.exam.isSubmitted)
  const startTime = useSelector((state: RootState) => state.exam.startTime)
  const antiCheat = useSelector((state: RootState) => state.exam.antiCheat)
  const warningShownRef = useRef<Set<number>>(new Set())
  const [isFullscreen, setIsFullscreen] = useState(false)

  useEffect(() => {
    if (!startTime || isSubmitted) return

    const handleVisibilityChange = () => {
      if (document.hidden) {
        dispatch(recordTabSwitch())
      }
    }

    const handleCopy = (e: ClipboardEvent) => {
      dispatch(recordCopy())
      e.preventDefault()
      showWarning('禁止复制考试内容！')
    }

    const handlePaste = (e: ClipboardEvent) => {
      dispatch(recordPaste())
      e.preventDefault()
      showWarning('禁止粘贴内容到考试！')
    }

    const handleContextMenu = (e: MouseEvent) => {
      e.preventDefault()
      showWarning('禁止右键菜单！')
    }

    const handleFullscreenChange = () => {
      const isNowFullscreen = !!document.fullscreenElement
      setIsFullscreen(isNowFullscreen)
      
      if (!isNowFullscreen && startTime && !isSubmitted) {
        dispatch(recordFullscreenExit())
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    document.addEventListener('copy', handleCopy)
    document.addEventListener('paste', handlePaste)
    document.addEventListener('contextmenu', handleContextMenu)
    document.addEventListener('fullscreenchange', handleFullscreenChange)

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      document.removeEventListener('copy', handleCopy)
      document.removeEventListener('paste', handlePaste)
      document.removeEventListener('contextmenu', handleContextMenu)
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
    }
  }, [dispatch, startTime, isSubmitted])

  useEffect(() => {
    if (antiCheat.warnings.length > 0) {
      const latestWarningIndex = antiCheat.warnings.length - 1
      if (!warningShownRef.current.has(latestWarningIndex)) {
        warningShownRef.current.add(latestWarningIndex)
        const latestWarning = antiCheat.warnings[latestWarningIndex]
        showWarning(latestWarning)
      }
    }
  }, [antiCheat.warnings])

  const showWarning = (message: string) => {
    Modal.warning({
      title: '考试纪律警告',
      content: message,
      okText: '我知道了',
      centered: true
    })
  }

  const requestFullscreen = async () => {
    try {
      await document.documentElement.requestFullscreen()
      setIsFullscreen(true)
    } catch (error) {
      console.error('Failed to enter fullscreen:', error)
    }
  }

  const exitFullscreen = async () => {
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen()
      }
      setIsFullscreen(false)
    } catch (error) {
      console.error('Failed to exit fullscreen:', error)
    }
  }

  return {
    isFullscreen,
    requestFullscreen,
    exitFullscreen,
    antiCheat
  }
}
