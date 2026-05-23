'use client'

import { Wifi, WifiOff, RefreshCw, AlertCircle } from 'lucide-react'

interface OfflineStatusProps {
  isOffline: boolean
  isSyncing: boolean
  pendingChanges: number
  syncError: string | null
  onSync: () => void
}

export default function OfflineStatus({
  isOffline,
  isSyncing,
  pendingChanges,
  syncError,
  onSync,
}: OfflineStatusProps) {
  if (!isOffline && pendingChanges === 0 && !syncError) {
    return null
  }

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium">
      {isOffline ? (
        <>
          <WifiOff size={14} className="text-amber-500" />
          <span className="text-amber-600">离线模式</span>
          {pendingChanges > 0 && (
            <span className="bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full">
              {pendingChanges} 待同步
            </span>
          )}
        </>
      ) : isSyncing ? (
        <>
          <RefreshCw size={14} className="text-blue-500 animate-spin" />
          <span className="text-blue-600">同步中...</span>
        </>
      ) : syncError ? (
        <>
          <AlertCircle size={14} className="text-red-500" />
          <span className="text-red-600">同步失败</span>
          <button
            onClick={onSync}
            className="ml-1 text-blue-600 hover:underline"
          >
            重试
          </button>
        </>
      ) : pendingChanges > 0 ? (
        <>
          <Wifi size={14} className="text-green-500" />
          <span className="text-gray-600">
            {pendingChanges} 项待同步
          </span>
          <button
            onClick={onSync}
            className="ml-1 text-blue-600 hover:underline"
          >
            立即同步
          </button>
        </>
      ) : null}
    </div>
  )
}
