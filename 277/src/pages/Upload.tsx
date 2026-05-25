import { useState, useCallback, useRef } from 'react'
import { Upload as UploadIcon, X, Check, FileWarning, Tag, FolderTree, ShieldAlert, AlertTriangle } from 'lucide-react'
import { useIconStore } from '@/store/iconStore'
import { useNavigate } from 'react-router-dom'
import { sanitizeSvg, validateSvgFile, type SanitizeResult } from '@/utils/svgUtils'

interface UploadingFile {
  id: string
  file: File
  name: string
  status: 'pending' | 'uploading' | 'success' | 'error'
  progress: number
  error?: string
  tags: string[]
  categoryId: string | null
  sanitizedContent?: string
  sanitizeWarnings?: string[]
  rawContent?: string
}

export default function Upload() {
  const { uploadIcon, categories, fetchCategories } = useIconStore()
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<UploadingFile[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [tagInput, setTagInput] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)

  const handleFiles = async (fileList: FileList) => {
    const newFiles: UploadingFile[] = []

    for (const file of Array.from(fileList)) {
      const validation = await validateSvgFile(file)
      
      if (!validation.valid || !validation.content) {
        newFiles.push({
          id: Math.random().toString(36).slice(2),
          file,
          name: file.name.replace('.svg', ''),
          status: 'error',
          progress: 0,
          error: validation.error || '无效的SVG文件',
          tags: [],
          categoryId: null,
        })
        continue
      }

      const sanitizeResult = sanitizeSvg(validation.content)
      
      newFiles.push({
        id: Math.random().toString(36).slice(2),
        file,
        name: file.name.replace('.svg', ''),
        status: 'pending',
        progress: 0,
        tags: [],
        categoryId: null,
        sanitizedContent: sanitizeResult.clean,
        sanitizeWarnings: sanitizeResult.warnings,
        rawContent: validation.content,
      })
    }

    setFiles((prev) => [...prev, ...newFiles])
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files) {
      handleFiles(e.dataTransfer.files)
    }
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id))
  }

  const addTag = (fileId: string, tag: string) => {
    if (!tag.trim()) return
    setFiles((prev) =>
      prev.map((f) =>
        f.id === fileId && !f.tags.includes(tag.trim())
          ? { ...f, tags: [...f.tags, tag.trim()] }
          : f
      )
    )
  }

  const removeTag = (fileId: string, tag: string) => {
    setFiles((prev) =>
      prev.map((f) =>
        f.id === fileId ? { ...f, tags: f.tags.filter((t) => t !== tag) } : f
      )
    )
  }

  const updateFileName = (fileId: string, name: string) => {
    setFiles((prev) => prev.map((f) => (f.id === fileId ? { ...f, name } : f)))
  }

  const uploadAll = async () => {
    const pendingFiles = files.filter((f) => f.status === 'pending')
    
    for (const uploadFile of pendingFiles) {
      setFiles((prev) =>
        prev.map((f) => (f.id === uploadFile.id ? { ...f, status: 'uploading', progress: 0 } : f))
      )

      try {
        const formData = new FormData()
        formData.append('file', uploadFile.file)
        formData.append('name', uploadFile.name)
        formData.append('tags', JSON.stringify(uploadFile.tags))
        if (uploadFile.categoryId) {
          formData.append('categoryId', uploadFile.categoryId)
        }

        setFiles((prev) =>
          prev.map((f) => (f.id === uploadFile.id ? { ...f, progress: 50 } : f))
        )

        await uploadIcon(formData)

        setFiles((prev) =>
          prev.map((f) => (f.id === uploadFile.id ? { ...f, status: 'success', progress: 100 } : f))
        )
      } catch (err) {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadFile.id
              ? { ...f, status: 'error', error: err instanceof Error ? err.message : '上传失败' }
              : f
          )
        )
      }
    }
  }

  const pendingCount = files.filter((f) => f.status === 'pending').length
  const successCount = files.filter((f) => f.status === 'success').length

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-gray-900">上传中心</h1>
          <p className="text-gray-500 mt-1">上传SVG图标文件，支持批量上传</p>
        </div>
        {successCount > 0 && (
          <button
            onClick={() => navigate('/icons')}
            className="btn btn-primary gap-2"
          >
            <Check size={18} />
            查看图标库
          </button>
        )}
      </div>

      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`card p-12 border-2 border-dashed transition-colors cursor-pointer ${
          isDragging
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 hover:border-primary-400'
        }`}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".svg,image/svg+xml"
          multiple
          className="hidden"
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
        />
        <div className="text-center">
          <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <UploadIcon className="text-primary-500" size={32} />
          </div>
          <h3 className="font-semibold text-gray-900 mb-2">拖拽文件到这里或点击上传</h3>
          <p className="text-gray-500 text-sm">支持SVG格式，可批量上传</p>
        </div>
      </div>

      {files.length > 0 && (
        <>
          <div className="card">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <span className="font-medium text-gray-900">
                {files.length} 个文件
                {pendingCount > 0 && <span className="text-gray-500 ml-2">（{pendingCount} 个待上传）</span>}
              </span>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setFiles([])}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  清空全部
                </button>
                {pendingCount > 0 && (
                  <button onClick={uploadAll} className="btn btn-primary">
                    上传全部
                  </button>
                )}
              </div>
            </div>

            <div className="divide-y divide-gray-100">
              {files.map((file) => (
                <div key={file.id} className="p-4 flex items-center gap-4">
                  <div
                    className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                      file.status === 'error' ? 'bg-red-50' : 'bg-gray-50'
                    }`}
                  >
                    {file.status === 'error' ? (
                      <FileWarning className="text-red-500" size={24} />
                    ) : file.status === 'success' ? (
                      <Check className="text-emerald-500" size={24} />
                    ) : (
                      <div
                        className="w-8 h-8"
                        dangerouslySetInnerHTML={{
                          __html: file.status === 'pending'
                            ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>'
                            : '',
                        }}
                      />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <input
                      type="text"
                      value={file.name}
                      onChange={(e) => updateFileName(file.id, e.target.value)}
                      className="font-medium text-gray-900 bg-transparent border-0 focus:ring-0 p-0 w-full"
                      disabled={file.status !== 'pending'}
                    />
                    
                    {file.status === 'error' ? (
                      <p className="text-sm text-red-500">{file.error}</p>
                    ) : file.status === 'uploading' ? (
                      <div className="h-1 bg-gray-200 rounded-full mt-2 overflow-hidden">
                        <div
                          className="h-full bg-primary-500 transition-all"
                          style={{ width: `${file.progress}%` }}
                        />
                      </div>
                    ) : file.status === 'success' ? (
                      <p className="text-sm text-emerald-500">上传成功</p>
                    ) : (
                      <div className="mt-2">
                        {file.sanitizeWarnings && file.sanitizeWarnings.length > 0 && (
                          <div className="mb-2 p-2 bg-amber-50 rounded-lg border border-amber-200">
                            <div className="flex items-center gap-1.5 text-amber-700 text-xs mb-1">
                              <ShieldAlert size={12} />
                              <span className="font-medium">已安全处理</span>
                            </div>
                            <div className="text-xs text-amber-600">
                              {file.sanitizeWarnings.map((warning, i) => (
                                <div key={i} className="flex items-center gap-1">
                                  <AlertTriangle size={10} />
                                  {warning}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        <div className="flex items-center gap-2">
                          <Tag size={14} className="text-gray-400" />
                          <div className="flex flex-wrap gap-1">
                            {file.tags.map((tag) => (
                              <span
                                key={tag}
                                className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-xs flex items-center gap-1"
                              >
                                {tag}
                                <button
                                  onClick={() => removeTag(file.id, tag)}
                                  className="hover:text-red-500"
                                >
                                  <X size={10} />
                                </button>
                              </span>
                            ))}
                            <input
                              type="text"
                              placeholder="添加标签..."
                              className="text-xs bg-transparent border-0 focus:ring-0 w-20"
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                  addTag(file.id, (e.target as HTMLInputElement).value)
                                  ;(e.target as HTMLInputElement).value = ''
                                }
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {file.status === 'pending' && (
                    <button
                      onClick={() => removeFile(file.id)}
                      className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                      <X size={18} className="text-gray-500" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
