import { useCallback } from 'react'
import { useAppStore, type StratifyIndex } from '@/store/appStore'

export function useDataApi() {
  const setFileMeta = useAppStore((s) => s.setFileMeta)
  const setRawData = useAppStore((s) => s.setRawData)
  const setIsUploading = useAppStore((s) => s.setIsUploading)
  const setUploadProgress = useAppStore((s) => s.setUploadProgress)
  const setColumnStats = useAppStore((s) => s.setColumnStats)
  const setStratifyIndex = useAppStore((s) => s.setStratifyIndex)

  const uploadFile = useCallback(
    async (file: File) => {
      setIsUploading(true)
      setUploadProgress(0)

      const formData = new FormData()
      formData.append('file', file)

      try {
        const xhr = new XMLHttpRequest()
        const result = await new Promise<any>((resolve, reject) => {
          xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
              setUploadProgress(Math.round((e.loaded / e.total) * 100))
            }
          })

          xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              resolve(JSON.parse(xhr.responseText))
            } else {
              reject(new Error(`Upload failed: ${xhr.status}`))
            }
          })

          xhr.addEventListener('error', () => reject(new Error('Upload error')))
          xhr.open('POST', '/api/data/upload')
          xhr.send(formData)
        })

        if (result.success) {
          setFileMeta(result.data)
          return result.data
        }
        throw new Error(result.error)
      } finally {
        setIsUploading(false)
        setUploadProgress(100)
      }
    },
    [setFileMeta, setIsUploading, setUploadProgress],
  )

  const fetchChunk = useCallback(
    async (fileId: string, offset: number, limit: number) => {
      const res = await fetch(
        `/api/data/data/${fileId}/chunk?offset=${offset}&limit=${limit}`,
      )
      const result = await res.json()
      if (result.success) {
        setRawData(result.data.data)
        return result.data
      }
      throw new Error(result.error)
    },
    [setRawData],
  )

  const fetchColumnStats = useCallback(
    async (fileId: string, column: string) => {
      const res = await fetch(
        `/api/data/data/${fileId}/column-stats?column=${encodeURIComponent(column)}`,
      )
      const result = await res.json()
      if (result.success) {
        setColumnStats(result.data.distribution)
        return result.data
      }
      throw new Error(result.error)
    },
    [setColumnStats],
  )

  const fetchStratifyIndex = useCallback(
    async (fileId: string, column: string): Promise<StratifyIndex> => {
      const res = await fetch(
        `/api/data/data/${fileId}/stratify-index?column=${encodeURIComponent(column)}`,
      )
      const result = await res.json()
      if (result.success) {
        const index: StratifyIndex = { column: result.data.column, groups: result.data.groups }
        setStratifyIndex(index)
        return index
      }
      throw new Error(result.error)
    },
    [setStratifyIndex],
  )

  const exportSample = useCallback(
    async (fileId: string, sampleIndices: number[], format: 'csv' | 'json') => {
      const res = await fetch('/api/data/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fileId, sampleIndices, format }),
      })

      if (!res.ok) throw new Error('Export failed')

      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `sample.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    },
    [],
  )

  return { uploadFile, fetchChunk, fetchColumnStats, fetchStratifyIndex, exportSample }
}
