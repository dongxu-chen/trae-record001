'use client'

import { useState, useRef } from 'react'
import { Upload, Image as ImageIcon, X, Loader2, Eye, FileText } from 'lucide-react'

interface ImageUploaderProps {
  onImageInsert: (imageMarkdown: string, ocrText: string) => void
}

export default function ImageUploader({ onImageInsert }: ImageUploaderProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [preview, setPreview] = useState<{
    url: string
    ocrText: string
    confidence: number
  } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = async (file: File) => {
    if (!file.type.startsWith('image/')) {
      alert('请选择图片文件')
      return
    }

    setIsProcessing(true)
    setProgress(10)

    try {
      const { recognizeAndSaveImage } = await import('@/lib/ocrService')
      
      setProgress(30)
      
      const result = await recognizeAndSaveImage(file)
      
      setProgress(100)
      
      setPreview({
        url: result.imageUrl,
        ocrText: result.text,
        confidence: result.confidence,
      })
    } catch (error) {
      console.error('Image processing error:', error)
      alert('图片处理失败，请重试')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleInsert = () => {
    if (!preview) return
    
    const imageMarkdown = `![OCR图片](${preview.url})\n\n`
    onImageInsert(imageMarkdown, preview.ocrText)
    
    setPreview(null)
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    const file = e.dataTransfer.files[0]
    if (file) {
      await handleFileSelect(file)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  return (
    <div className="space-y-4">
      {!preview && (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          className={`relative border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
            isDragging
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
            className="hidden"
          />
          
          {isProcessing ? (
            <div className="space-y-2">
              <Loader2 size={32} className="mx-auto text-blue-500 animate-spin" />
              <p className="text-sm text-gray-600">正在识别图片文字...</p>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          ) : (
            <>
              <Upload size={32} className="mx-auto text-gray-400 mb-2" />
              <p className="text-sm text-gray-600">
                拖拽图片到此处或点击上传
              </p>
              <p className="text-xs text-gray-400 mt-1">
                支持 JPG、PNG、GIF 格式，自动识别文字
              </p>
            </>
          )}
        </div>
      )}

      {preview && (
        <div className="border rounded-lg overflow-hidden">
          <div className="relative">
            <img
              src={preview.url}
              alt="Preview"
              className="w-full h-48 object-contain bg-gray-100"
            />
            <button
              onClick={() => setPreview(null)}
              className="absolute top-2 right-2 p-1 bg-white rounded-full shadow hover:bg-gray-100"
            >
              <X size={16} />
            </button>
          </div>
          
          <div className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText size={16} className="text-gray-500" />
                <span className="text-sm font-medium text-gray-700">识别结果</span>
              </div>
              <span className="text-xs text-gray-500">
                置信度: {preview.confidence.toFixed(1)}%
              </span>
            </div>
            
            <div className="max-h-24 overflow-y-auto bg-gray-50 rounded p-2">
              <p className="text-sm text-gray-600 whitespace-pre-wrap">
                {preview.ocrText || '未识别到文字'}
              </p>
            </div>
            
            <div className="flex gap-2">
              <button
                onClick={handleInsert}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                <ImageIcon size={16} />
                插入到笔记
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
