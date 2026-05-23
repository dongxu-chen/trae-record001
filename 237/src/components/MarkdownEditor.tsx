'use client'

import dynamic from 'next/dynamic'
import { useMemo } from 'react'
import SimpleMDE from 'react-simplemde-editor'
import 'easymde/dist/easymde.min.css'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MarkdownEditorProps {
  value: string
  onChange: (value: string) => void
  preview?: boolean
}

export default function MarkdownEditor({ value, onChange, preview = false }: MarkdownEditorProps) {
  const SimpleMDEditor = useMemo(
    () => dynamic(() => import('react-simplemde-editor'), { ssr: false }),
    []
  )

  const options = useMemo(
    () => ({
      autofocus: true,
      spellChecker: false,
      status: false,
      toolbar: [
        'bold',
        'italic',
        'heading',
        '|',
        'quote',
        'unordered-list',
        'ordered-list',
        '|',
        'link',
        'image',
        'code',
        'table',
        '|',
        'preview',
        'side-by-side',
        'fullscreen',
        '|',
        'guide',
      ],
    }),
    []
  )

  if (preview) {
    return (
      <div className="markdown-preview p-4 h-full overflow-y-auto">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{value}</ReactMarkdown>
      </div>
    )
  }

  return (
    <div className="h-full">
      <SimpleMDEditor value={value} onChange={onChange} options={options} />
    </div>
  )
}
