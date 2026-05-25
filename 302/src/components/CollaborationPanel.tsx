import React, { useState, useEffect, useCallback } from 'react'
import { CollaborativeSession, CollaborativeSegment, Collaborator, MergeResult } from '../types'
import { collaborationService, splitTextIntoSegments } from '../services/collaborationService'
import { LANGUAGE_MAP } from '../constants'

interface CollaborationPanelProps {
  initialText?: string
  sourceLang?: string
  targetLang?: string
  onMergeComplete?: (mergedText: string) => void
}

const CollaboratorAvatar: React.FC<{ collaborator: Collaborator; showName?: boolean }> = ({ collaborator, showName = true }) => {
  return (
    <div className="flex items-center gap-2">
      <div className="relative">
        {collaborator.avatar ? (
          <img
            src={collaborator.avatar}
            alt={collaborator.name}
            className="w-8 h-8 rounded-full border-2"
            style={{ borderColor: collaborator.color }}
          />
        ) : (
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium"
            style={{ backgroundColor: collaborator.color }}
          >
            {collaborator.name.charAt(0)}
          </div>
        )}
        <div
          className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white ${
            collaborator.isOnline ? 'bg-green-500' : 'bg-gray-400'
          }`}
        />
      </div>
      {showName && (
        <div>
          <p className="text-sm font-medium text-gray-800">{collaborator.name}</p>
          <p className="text-xs text-gray-500">
            {collaborator.isOnline ? '在线' : '离线 ' + new Date(collaborator.lastActive).toLocaleTimeString()}
          </p>
        </div>
      )}
    </div>
  )
}

const SegmentCard: React.FC<{
  segment: CollaborativeSegment
  session: CollaborativeSession
  onClaim: (segmentId: string) => void
  onRelease: (segmentId: string) => void
  onUpdate: (segmentId: string, text: string) => void
  onResolveConflict: (segmentId: string, versionIndex: number) => void
  currentUserId: string
}> = ({ segment, session, onClaim, onRelease, onUpdate, onResolveConflict, currentUserId }) => {
  const [editText, setEditText] = useState(segment.translatedText)
  const [isEditing, setIsEditing] = useState(false)
  const [showVersions, setShowVersions] = useState(false)

  const assignee = segment.assignee
    ? session.collaborators.find(c => c.id === segment.assignee)
    : null

  const statusConfig = {
    pending: { bg: 'bg-gray-100', text: 'text-gray-600', label: '待翻译', border: 'border-gray-300' },
    in_progress: { bg: 'bg-blue-50', text: 'text-blue-600', label: '翻译中', border: 'border-blue-300' },
    translated: { bg: 'bg-green-50', text: 'text-green-600', label: '已翻译', border: 'border-green-300' },
    reviewed: { bg: 'bg-purple-50', text: 'text-purple-600', label: '已审核', border: 'border-purple-300' },
    conflict: { bg: 'bg-red-50', text: 'text-red-600', label: '有冲突', border: 'border-red-300' },
  }

  const config = statusConfig[segment.status]
  const isClaimedByMe = segment.assignee === currentUserId
  const canEdit = isClaimedByMe || !segment.assignee

  useEffect(() => {
    setEditText(segment.translatedText)
  }, [segment.translatedText])

  const handleSave = () => {
    if (editText !== segment.translatedText) {
      onUpdate(segment.id, editText)
    }
    setIsEditing(false)
  }

  const calculateWidth = (value: number, total: number) => {
    return String((value / total) * 100) + '%'
  }

  return (
    <div className={`p-4 rounded-xl border-2 ${config.border} ${config.bg} mb-3`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <p className="text-sm text-gray-700 mb-2">{segment.sourceText}</p>
          {assignee && (
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: assignee.color }} />
              <span className="text-xs text-gray-500">
                {isClaimedByMe ? '由我负责' : '由 ' + assignee.name + ' 负责'}
              </span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
            {config.label}
          </span>
          {segment.versions.length > 0 && (
            <button
              onClick={() => setShowVersions(!showVersions)}
              className="text-xs text-gray-500 hover:text-blue-600"
            >
              📜 {segment.versions.length}个版本
            </button>
          )}
        </div>
      </div>

      {segment.status === 'conflict' && (
        <div className="mb-3 p-3 bg-red-100 rounded-lg">
          <p className="text-sm font-medium text-red-800 mb-2">⚠️ 存在翻译冲突</p>
          <div className="space-y-2">
            {segment.versions.map((version, idx) => (
              <div key={idx} className="p-2 bg-white rounded flex items-center justify-between">
                <div>
                  <p className="text-sm">{version.text}</p>
                  <p className="text-xs text-gray-500">
                    {(session.collaborators.find(c => c.id === version.by)?.name || '未知用户') + ' · ' + new Date(version.timestamp).toLocaleTimeString()}
                  </p>
                </div>
                <button
                  onClick={() => onResolveConflict(segment.id, idx)}
                  className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  选择此版本
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {isEditing ? (
        <div>
          <textarea
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            className="w-full p-3 border rounded-lg mb-2"
            rows={3}
            placeholder="输入翻译..."
          />
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              保存
            </button>
            <button
              onClick={() => {
                setEditText(segment.translatedText)
                setIsEditing(false)
              }}
              className="px-3 py-1 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
            >
              取消
            </button>
          </div>
        </div>
      ) : (
        <div className="flex items-start justify-between">
          <p className="flex-1 text-gray-800">
            {segment.translatedText || <span className="text-gray-400">暂无翻译</span>}
          </p>
          {canEdit && segment.status !== 'conflict' && (
            <button
              onClick={() => setIsEditing(true)}
              className="ml-2 px-2 text-blue-600 hover:text-blue-800"
            >
              ✏️
            </button>
          )}
        </div>
      )}

      <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-200">
        <span className="text-xs text-gray-500">
          最后修改: {new Date(segment.lastModified).toLocaleString()}
        </span>
        <div className="flex gap-2">
          {!segment.assignee && (
            <button
              onClick={() => onClaim(segment.id)}
              className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
            >
              认领翻译
            </button>
          )}
          {isClaimedByMe && (
            <button
              onClick={() => onRelease(segment.id)}
              className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
            >
              释放
            </button>
          )}
        </div>
      </div>

      {showVersions && segment.versions.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <p className="text-xs font-medium text-gray-700 mb-2">历史版本</p>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {segment.versions.slice().reverse().map((version, idx) => {
              const contributor = session.collaborators.find(c => c.id === version.by)
              return (
                <div key={idx} className="p-2 bg-gray-50 rounded text-sm">
                  <p className="text-gray-800">{version.text}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {(contributor?.name || '未知') + ' · ' + new Date(version.timestamp).toLocaleString()}
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

export const CollaborationPanel: React.FC<CollaborationPanelProps> = ({
  initialText = '',
  sourceLang = 'zh',
  targetLang = 'en',
  onMergeComplete,
}) => {
  const [session, setSession] = useState<CollaborativeSession | null>(null)
  const [sessionTitle, setSessionTitle] = useState('协作翻译任务')
  const [isCreating, setIsCreating] = useState(false)
  const [mergeResult, setMergeResult] = useState<MergeResult | null>(null)
  const [showMergeResult, setShowMergeResult] = useState(false)

  const currentUser = collaborationService.getCurrentUser()

  useEffect(() => {
    if (!session) return

    const unsubscribe = collaborationService.subscribe(session.id, (updatedSession) => {
      setSession({ ...updatedSession })
    })

    return () => unsubscribe()
  }, [session?.id])

  const handleCreateSession = useCallback(async () => {
    if (!initialText.trim()) {
      alert('请先输入要翻译的文本')
      return
    }

    setIsCreating(true)
    try {
      const segments = splitTextIntoSegments(initialText, 150)
      const newSession = collaborationService.createSession(
        sessionTitle,
        sourceLang as any,
        targetLang as any,
        segments
      )
      setSession(newSession)
    } finally {
      setIsCreating(false)
    }
  }, [initialText, sessionTitle, sourceLang, targetLang])

  const handleJoinSession = useCallback((sessionId: string) => {
    const joined = collaborationService.joinSession(sessionId)
    if (joined) {
      setSession(joined)
    }
  }, [])

  const handleLeaveSession = useCallback(() => {
    if (session) {
      collaborationService.leaveSession(session.id)
      setSession(null)
      setMergeResult(null)
      setShowMergeResult(false)
    }
  }, [session])

  const handleClaimSegment = useCallback((segmentId: string) => {
    if (session) {
      collaborationService.claimSegment(session.id, segmentId)
    }
  }, [session])

  const handleReleaseSegment = useCallback((segmentId: string) => {
    if (session) {
      collaborationService.releaseSegment(session.id, segmentId)
    }
  }, [session])

  const handleUpdateTranslation = useCallback((segmentId: string, text: string) => {
    if (session) {
      collaborationService.updateTranslation(session.id, segmentId, text)
    }
  }, [session])

  const handleResolveConflict = useCallback((segmentId: string, versionIndex: number) => {
    if (session) {
      collaborationService.resolveConflict(session.id, segmentId, versionIndex)
    }
  }, [session])

  const handleMerge = useCallback(() => {
    if (!session) return
    
    const result = collaborationService.mergeSegments(session.id)
    setMergeResult(result)
    setShowMergeResult(true)

    if (result.manualRequired === 0 && onMergeComplete) {
      const mergedText = result.merged
        .map(s => s.translatedText)
        .filter(Boolean)
        .join(' ')
      onMergeComplete(mergedText)
    }
  }, [session, onMergeComplete])

  const getMergedText = () => {
    if (!session) return ''
    return session.segments
      .map(s => s.translatedText)
      .filter(Boolean)
      .join(' ')
  }

  const progress = session ? {
    total: session.segments.length,
    translated: session.segments.filter(s => s.status === 'translated' || s.status === 'reviewed').length,
    inProgress: session.segments.filter(s => s.status === 'in_progress').length,
    conflicts: session.segments.filter(s => s.status === 'conflict').length,
  } : null

  const calculateWidth = (value: number, total: number) => {
    return String((value / total) * 100) + '%'
  }

  if (!session) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <span>👥</span> 实时协作翻译
        </h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              任务名称
            </label>
            <input
              type="text"
              value={sessionTitle}
              onChange={(e) => setSessionTitle(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="输入协作任务名称"
            />
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleCreateSession}
              disabled={isCreating || !initialText.trim()}
              className="flex-1 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {isCreating ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                  创建中...
                </>
              ) : (
                <>
                  <span>➕</span> 创建协作会话
                </>
              )}
            </button>
          </div>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">或者</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              加入已有会话
            </label>
            <div className="space-y-2">
              {collaborationService.getAllSessions().map((s) => (
                <button
                  key={s.id}
                  onClick={() => handleJoinSession(s.id)}
                  className="w-full p-3 text-left border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors"
                >
                  <p className="font-medium text-gray-800">{s.title}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {s.collaborators.length + ' 位协作者 · ' + s.segments.length + ' 个段落 · ' +
                    (LANGUAGE_MAP[s.sourceLang as keyof typeof LANGUAGE_MAP]?.nativeName || s.sourceLang) +
                    ' → ' + (LANGUAGE_MAP[s.targetLang as keyof typeof LANGUAGE_MAP]?.nativeName || s.targetLang)}
                  </p>
                </button>
              ))}
              {collaborationService.getAllSessions().length === 0 && (
                <p className="text-sm text-gray-500 text-center py-4">
                  暂无可用的协作会话
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden">
      <div className="p-6 bg-gradient-to-r from-purple-50 to-indigo-50 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
              <span>👥</span> {session.title}
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              {(LANGUAGE_MAP[session.sourceLang as keyof typeof LANGUAGE_MAP]?.nativeName || session.sourceLang) +
              ' → ' + (LANGUAGE_MAP[session.targetLang as keyof typeof LANGUAGE_MAP]?.nativeName || session.targetLang)}
            </p>
          </div>
          <button
            onClick={handleLeaveSession}
            className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            离开会话
          </button>
        </div>

        {progress && (
          <div className="mt-4">
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="text-gray-600">翻译进度</span>
              <span className="font-medium text-gray-800">
                {progress.translated + ' / ' + progress.total + ' 段'}
              </span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden flex">
              <div
                className="h-full bg-green-500 transition-all"
                style={{ width: calculateWidth(progress.translated, progress.total) }}
              />
              <div
                className="h-full bg-blue-500 transition-all"
                style={{ width: calculateWidth(progress.inProgress, progress.total) }}
              />
              {progress.conflicts > 0 && (
                <div
                  className="h-full bg-red-500 transition-all"
                  style={{ width: calculateWidth(progress.conflicts, progress.total) }}
                />
              )}
            </div>
            <div className="flex gap-4 mt-2 text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 bg-green-500 rounded-full" />
                已翻译 {progress.translated}
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 bg-blue-500 rounded-full" />
                翻译中 {progress.inProgress}
              </span>
              {progress.conflicts > 0 && (
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 bg-red-500 rounded-full" />
                  冲突 {progress.conflicts}
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="p-6 border-b border-gray-200">
        <h4 className="text-sm font-medium text-gray-700 mb-3">协作者 ({session.collaborators.length})</h4>
        <div className="flex flex-wrap gap-4">
          {session.collaborators.map(collaborator => (
            <CollaboratorAvatar key={collaborator.id} collaborator={collaborator} />
          ))}
        </div>
      </div>

      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-sm font-medium text-gray-700">翻译段落 ({session.segments.length})</h4>
          <button
            onClick={handleMerge}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm transition-colors flex items-center gap-2"
          >
            <span>🔀</span> 合并翻译结果
          </button>
        </div>

        <div className="max-h-96 overflow-y-auto">
          {session.segments.map((segment, index) => (
            <SegmentCard
              key={segment.id}
              segment={segment}
              session={session}
              onClaim={handleClaimSegment}
              onRelease={handleReleaseSegment}
              onUpdate={handleUpdateTranslation}
              onResolveConflict={handleResolveConflict}
              currentUserId={currentUser.id}
            />
          ))}
        </div>
      </div>

      {showMergeResult && mergeResult && (
        <div className="p-6 bg-gray-50 border-t border-gray-200">
          <h4 className="text-sm font-medium text-gray-700 mb-3">合并结果</h4>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="p-4 bg-green-50 rounded-lg text-center">
              <p className="text-2xl font-bold text-green-600">{mergeResult.autoMerged}</p>
              <p className="text-sm text-green-700">自动合并</p>
            </div>
            <div className="p-4 bg-red-50 rounded-lg text-center">
              <p className="text-2xl font-bold text-red-600">{mergeResult.manualRequired}</p>
              <p className="text-sm text-red-700">需人工处理</p>
            </div>
          </div>

          {mergeResult.conflicts.length > 0 && (
            <div className="mb-4">
              <p className="text-sm font-medium text-red-700 mb-2">待解决的冲突</p>
              {mergeResult.conflicts.map((conflict, idx) => (
                <div key={idx} className="p-3 bg-red-100 rounded-lg mb-2">
                  <p className="text-sm text-red-800">
                    段落 {(session.segments.findIndex(s => s.id === conflict.segmentId) + 1)}
                  </p>
                </div>
              ))}
            </div>
          )}

          {mergeResult.manualRequired === 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">合并后的译文</p>
              <div className="p-4 bg-white rounded-lg border border-gray-200 max-h-40 overflow-y-auto">
                <p className="text-gray-800">{getMergedText() || '暂无内容'}</p>
              </div>
              <button
                onClick={() => navigator.clipboard.writeText(getMergedText())}
                className="mt-3 w-full py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm transition-colors"
              >
                📋 复制合并结果
              </button>
            </div>
          )}

          <button
            onClick={() => setShowMergeResult(false)}
            className="mt-4 w-full py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm transition-colors"
          >
            关闭
          </button>
        </div>
      )}
    </div>
  )
}
