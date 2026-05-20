'use client'

import { useEffect, useRef, useState } from 'react'
import hljs from 'highlight.js'

interface CodeBlockProps {
  code: string
  language: string
}

export default function CodeBlock({ code, language }: CodeBlockProps) {
  const codeRef = useRef<HTMLElement>(null)
  const [copied, setCopied] = useState(false)
  const [copyError, setCopyError] = useState(false)

  useEffect(() => {
    if (codeRef.current) {
      hljs.highlightElement(codeRef.current)
    }
  }, [code, language])

  const fallbackCopy = (text: string): boolean => {
    try {
      const textArea = document.createElement('textarea')
      textArea.value = text
      textArea.style.position = 'fixed'
      textArea.style.left = '-9999px'
      textArea.style.top = '-9999px'
      textArea.setAttribute('readonly', '')
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()

      const successful = document.execCommand('copy')
      document.body.removeChild(textArea)
      return successful
    } catch (err) {
      console.error('Fallback copy failed:', err)
      return false
    }
  }

  const handleCopy = async () => {
    setCopyError(false)

    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(code)
      } else {
        const success = fallbackCopy(code)
        if (!success) {
          throw new Error('Fallback copy failed')
        }
      }

      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
      setCopyError(true)
      setTimeout(() => setCopyError(false), 3000)
    }
  }

  return (
    <div className="relative">
      <button
        onClick={handleCopy}
        disabled={copied}
        className={`absolute top-2 right-2 px-3 py-1 text-sm rounded transition z-10 ${
          copied
            ? 'bg-green-600 text-white'
            : copyError
            ? 'bg-red-600 text-white'
            : 'bg-gray-700 text-white hover:bg-gray-600'
        } ${copied ? 'cursor-default' : 'cursor-pointer'}`}
      >
        {copied ? '✓ Copied!' : copyError ? '✗ Failed' : 'Copy'}
      </button>
      <pre className="overflow-x-auto">
        <code ref={codeRef} className={`language-${language}`}>
          {code}
        </code>
      </pre>
      {copyError && (
        <p className="mt-2 text-sm text-red-500">
          复制失败，请手动选择并复制代码
        </p>
      )}
    </div>
  )
}
