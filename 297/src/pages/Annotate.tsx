import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Download, Save, Wand2, Ruler, CheckCircle, Layers } from 'lucide-react'
import PointCloudViewer from '@/components/PointCloudViewer'
import Toolbar from '@/components/Toolbar'
import LabelPanel from '@/components/LabelPanel'
import CollaborationPanel from '@/components/CollaborationPanel'
import MeasurementToolbar from '@/components/MeasurementToolbar'
import QualityPanel from '@/components/QualityPanel'
import AIPanel from '@/components/AIPanel'
import { useAnnotationStore } from '@/store/annotationStore'
import { useAuthStore } from '@/store/authStore'
import { useCollaborationStore } from '@/store/collaborationStore'
import { useToolsStore } from '@/store/toolsStore'
import { annotationApi, projectApi } from '@/services/api'
import { wsService } from '@/services/websocket'
import { Annotation, RegionLock } from '@/types'

type RightPanel = 'labels' | 'collaboration' | 'quality' | 'ai'

export default function Annotate() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [projectName, setProjectName] = useState('')
  const [history, setHistory] = useState<Annotation[][]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const [saving, setSaving] = useState(false)
  const [activeRightPanel, setActiveRightPanel] = useState<RightPanel>('labels')

  const user = useAuthStore((state) => state.user)
  const { annotations, setAnnotations, addAnnotation, deleteAnnotation } = useAnnotationStore()
  const { 
    setOnlineUsers, 
    addOnlineUser, 
    removeOnlineUser,
    setRegionLocks,
    addRegionLock,
    removeRegionLock,
    clearRegionLocks,
  } = useCollaborationStore()
  const { activeTool, setActiveTool } = useToolsStore()

  useEffect(() => {
    if (!projectId) return

    const loadData = async () => {
      try {
        const project = await projectApi.getById(projectId)
        setProjectName(project.name)

        const anns = await annotationApi.getByProjectId(projectId)
        setAnnotations(anns)
        setHistory([anns])
        setHistoryIndex(0)
      } catch {
        navigate('/projects')
      }
    }
    loadData()

    if (user) {
      wsService.connect().then(() => {
        wsService.joinProject(projectId, user.id, user.username)
      })

      wsService.on('user-joined', ({ userId, userName, color }: { userId: string; userName: string; color: string }) => {
        if (userId !== user.id) {
          addOnlineUser({ id: userId, username: userName, color })
        }
      })

      wsService.on('user-left', ({ userId }: { userId: string }) => {
        removeOnlineUser(userId)
      })

      wsService.on('online-users', ({ users }: { users: Array<{ id: string; username: string; color: string }> }) => {
        setOnlineUsers(users.filter(u => u.id !== user.id))
      })

      wsService.on('annotation-created', ({ annotation, userId }: { annotation: Annotation; userId: string }) => {
        if (userId !== user.id) {
          addAnnotation(annotation)
        }
      })

      wsService.on('annotation-deleted', ({ annotationId, userId }: { annotationId: string; userId: string }) => {
        if (userId !== user.id) {
          deleteAnnotation(annotationId)
        }
      })

      wsService.on('region-locks', ({ locks }: { locks: RegionLock[] }) => {
        setRegionLocks(locks)
      })

      wsService.on('region-lock-acquired', ({ lock }: { lock: RegionLock }) => {
        addRegionLock(lock)
      })

      wsService.on('region-lock-released', ({ lockId }: { lockId: string }) => {
        removeRegionLock(lockId)
      })

      wsService.on('region-lock-updated', ({ lock }: { lock: RegionLock }) => {
        addRegionLock(lock)
      })

      wsService.on('region-lock-denied', ({ reason, conflictedLock }: { reason: string; conflictedLock: RegionLock }) => {
        console.warn('Region lock denied:', reason, conflictedLock)
      })
    }

    return () => {
      if (projectId) {
        wsService.leaveProject(projectId)
      }
      clearRegionLocks()
    }
  }, [projectId, user, setAnnotations, addOnlineUser, removeOnlineUser, setOnlineUsers, addAnnotation, deleteAnnotation, setRegionLocks, addRegionLock, removeRegionLock, clearRegionLocks, navigate])

  useEffect(() => {
    if (historyIndex >= 0 && history[historyIndex] !== annotations) {
      setHistory(prev => [...prev.slice(0, historyIndex + 1), [...annotations]])
      setHistoryIndex(prev => prev + 1)
    }
  }, [annotations.length])

  const handleDelete = useCallback(() => {
    const selectedId = useAnnotationStore.getState().selectedAnnotationId
    if (selectedId) {
      deleteAnnotation(selectedId)
      if (user && projectId) {
        wsService.sendAnnotationDeleted(projectId, selectedId)
      }
    }
  }, [deleteAnnotation, user, projectId])

  const handleUndo = useCallback(() => {
    if (historyIndex > 0) {
      setHistoryIndex(prev => prev - 1)
      setAnnotations(history[historyIndex - 1])
    }
  }, [history, historyIndex, setAnnotations])

  const handleResetView = useCallback(() => {
  }, [])

  const handleSave = async () => {
    if (!projectId) return
    setSaving(true)
    try {
      for (const ann of annotations) {
        await annotationApi.create(projectId, ann)
      }
    } catch {
      console.error('Failed to save annotations')
    } finally {
      setSaving(false)
    }
  }

  const handleExport = (format: 'json' | 'las') => {
    if (!projectId) return
    annotationApi.export(projectId, format)
  }

  const rightPanels = [
    { id: 'labels' as RightPanel, icon: Layers, label: '标签' },
    { id: 'collaboration' as RightPanel, icon: Layers, label: '协作' },
    { id: 'quality' as RightPanel, icon: CheckCircle, label: '质检' },
    { id: 'ai' as RightPanel, icon: Wand2, label: 'AI' },
  ]

  return (
    <div className="h-full flex">
      <div className="p-4 flex flex-col gap-4">
        <div className="glass-panel rounded-xl p-2">
          <div className="space-y-1 mb-2">
            <button
              onClick={() => setActiveTool('annotate')}
              className={`w-full p-2 rounded-lg flex items-center justify-center gap-2 text-sm transition-colors ${
                activeTool === 'annotate'
                  ? 'bg-primary-500 text-white'
                  : 'text-zinc-400 hover:bg-zinc-700 hover:text-white'
              }`}
            >
              <Layers className="w-4 h-4" />
            </button>
            <button
              onClick={() => setActiveTool('measure')}
              className={`w-full p-2 rounded-lg flex items-center justify-center gap-2 text-sm transition-colors ${
                activeTool === 'measure'
                  ? 'bg-yellow-500/20 text-yellow-400'
                  : 'text-zinc-400 hover:bg-zinc-700 hover:text-white'
              }`}
            >
              <Ruler className="w-4 h-4" />
            </button>
          </div>
          <div className="h-px bg-zinc-700 my-2" />
        </div>
        
        {activeTool === 'annotate' && (
          <Toolbar
            onDelete={handleDelete}
            onUndo={handleUndo}
            onResetView={handleResetView}
            canUndo={historyIndex > 0}
          />
        )}
      </div>

      <div className="flex-1 relative">
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-10 glass-panel rounded-xl px-6 py-2 flex items-center gap-4">
          <span className="text-white font-medium">{projectName}</span>
          <div className="h-5 w-px bg-zinc-700" />
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 text-sm text-primary-400 hover:text-primary-300 transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? '保存中...' : '保存'}
          </button>
          <div className="relative group">
            <button className="flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors">
              <Download className="w-4 h-4" />
              导出
            </button>
            <div className="absolute top-full left-0 mt-2 glass-panel rounded-lg py-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
              <button
                onClick={() => handleExport('json')}
                className="w-full px-4 py-2 text-sm text-left text-zinc-300 hover:bg-zinc-700 hover:text-white transition-colors"
              >
                JSON 格式
              </button>
              <button
                onClick={() => handleExport('las')}
                className="w-full px-4 py-2 text-sm text-left text-zinc-300 hover:bg-zinc-700 hover:text-white transition-colors"
              >
                LAS 格式
              </button>
            </div>
          </div>
        </div>

        {projectId && <PointCloudViewer projectId={projectId} />}
      </div>

      <div className="p-4 flex flex-col gap-4">
        <div className="flex gap-1 p-1 glass-panel rounded-lg">
          {rightPanels.map((panel) => {
            const Icon = panel.icon
            const isActive = activeRightPanel === panel.id
            return (
              <button
                key={panel.id}
                onClick={() => setActiveRightPanel(panel.id)}
                className={`p-2 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-zinc-700 text-white'
                    : 'text-zinc-400 hover:text-white'
                }`}
                title={panel.label}
              >
                <Icon className="w-4 h-4" />
              </button>
            )
          })}
        </div>

        <div className="flex-1 overflow-y-auto scrollbar-thin">
          {activeRightPanel === 'labels' && <LabelPanel />}
          {activeRightPanel === 'collaboration' && <CollaborationPanel />}
          {activeRightPanel === 'quality' && <QualityPanel />}
          {activeRightPanel === 'ai' && <AIPanel />}
        </div>

        {activeTool === 'measure' && (
          <MeasurementToolbar />
        )}
      </div>
    </div>
  )
}
