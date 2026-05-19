'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

interface Version {
  id: string
  title: string
  description: string | null
  code: string
  language: string
  versionNumber: number
  createdAt: string
  createdBy: {
    id: string
    name: string | null
    email: string
  }
}

interface VersionHistoryProps {
  snippetId: string
  isOwner: boolean
}

export default function VersionHistory({ snippetId, isOwner }: VersionHistoryProps) {
  const router = useRouter()
  const [versions, setVersions] = useState<Version[]>([])
  const [showVersions, setShowVersions] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (showVersions && versions.length === 0) {
      fetchVersions()
    }
  }, [showVersions])

  const fetchVersions = async () => {
    try {
      const response = await fetch(`/api/snippets/${snippetId}/versions`)
      if (response.ok) {
        const data = await response.json()
        setVersions(data)
      }
    } catch (error) {
      console.error('Failed to fetch versions:', error)
    }
  }

  const handleRollback = async (versionNumber: number) => {
    if (!confirm(`确定要回滚到版本 ${versionNumber} 吗？当前版本将被保存为新版本。`)) {
      return
    }

    setIsLoading(true)
    try {
      const response = await fetch(`/api/snippets/${snippetId}/versions/${versionNumber}/rollback`, {
        method: 'POST'
      })

      if (response.ok) {
        router.refresh()
        setShowVersions(false)
      }
    } catch (error) {
      console.error('Failed to rollback:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="mt-4">
      <button
        onClick={() => setShowVersions(!showVersions)}
        className="text-blue-600 hover:text-blue-800 text-sm"
      >
        {showVersions ? '隐藏版本历史' : '查看版本历史'}
      </button>

      {showVersions && (
        <div className="mt-4 bg-white rounded-lg shadow-md p-4">
          <h3 className="font-bold mb-4">版本历史</h3>
          {versions.length === 0 ? (
            <p className="text-gray-500">暂无历史版本</p>
          ) : (
            <div className="space-y-3">
              {versions.map((version, index) => (
                <div
                  key={version.id}
                  className={`p-4 rounded-lg border ${
                    index === 0 ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200'
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <span className="font-semibold">
                        版本 {version.versionNumber}
                        {index === 0 && (
                          <span className="ml-2 px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded">
                            当前
                          </span>
                        )}
                      </span>
                      <p className="text-sm text-gray-600">{version.title}</p>
                    </div>
                    {isOwner && index !== 0 && (
                      <button
                        onClick={() => handleRollback(version.versionNumber)}
                        disabled={isLoading}
                        className="px-3 py-1 bg-yellow-500 text-white text-sm rounded hover:bg-yellow-600 transition disabled:opacity-50"
                      >
                        回滚到此版本
                      </button>
                    )}
                  </div>
                  <div className="text-xs text-gray-500">
                    <span>
                      编辑者: {version.createdBy.name || version.createdBy.email}
                    </span>
                    <span className="mx-2">•</span>
                    <span>{new Date(version.createdAt).toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
