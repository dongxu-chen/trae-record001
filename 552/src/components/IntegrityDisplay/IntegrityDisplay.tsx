import { useState } from 'react'
import { cn } from '@/lib/utils'
import {
  FileCheck,
  FileX,
  Hash,
  Calendar,
  Signature,
  AlertTriangle,
  Copy,
  Check
} from 'lucide-react'
import type { IntegrityResult } from '../../../shared'

interface IntegrityDisplayProps {
  integrityResult: IntegrityResult
}

export default function IntegrityDisplay({ integrityResult }: IntegrityDisplayProps) {
  const [copiedField, setCopiedField] = useState<string | null>(null)

  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedField(field)
      setTimeout(() => setCopiedField(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const getStatusColor = (isValid: boolean) =>
    isValid ? 'text-green-600 bg-green-50 border-green-200' : 'text-red-600 bg-red-50 border-red-200'

  const getHashMatchColor = (match: boolean) =>
    match ? 'text-green-600' : 'text-red-600'

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className={cn(
        'flex items-center gap-3 px-6 py-4 border-b',
        integrityResult.isValid ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
      )}>
        {integrityResult.isValid ? (
          <FileCheck className="w-6 h-6 text-green-600" />
        ) : (
          <FileX className="w-6 h-6 text-red-600" />
        )}
        <div>
          <h3 className="text-lg font-semibold text-gray-900">文档完整性验证</h3>
          <p className={cn('text-sm font-medium', getStatusColor(integrityResult.isValid).split(' ')[0])}>
            {integrityResult.isValid ? '文档完整，未被篡改' : '文档已被篡改'}
          </p>
        </div>
      </div>

      <div className="p-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <Hash className="w-4 h-4" />
              <span>文档哈希</span>
            </div>
            <div className="flex items-center gap-2">
              <code className={cn(
                'flex-1 p-3 rounded-lg font-mono text-sm bg-gray-50 border border-gray-200 break-all',
                getHashMatchColor(integrityResult.hashMatch)
              )}>
                {integrityResult.documentHash}
              </code>
              <button
                onClick={() => copyToClipboard(integrityResult.documentHash, 'documentHash')}
                className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                title="复制到剪贴板"
              >
                {copiedField === 'documentHash' ? (
                  <Check className="w-4 h-4 text-green-600" />
                ) : (
                  <Copy className="w-4 h-4 text-gray-500" />
                )}
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <Hash className="w-4 h-4" />
              <span>签名哈希</span>
            </div>
            <div className="flex items-center gap-2">
              <code className={cn(
                'flex-1 p-3 rounded-lg font-mono text-sm bg-gray-50 border border-gray-200 break-all',
                getHashMatchColor(integrityResult.hashMatch)
              )}>
                {integrityResult.signedHash}
              </code>
              <button
                onClick={() => copyToClipboard(integrityResult.signedHash, 'signedHash')}
                className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                title="复制到剪贴板"
              >
                {copiedField === 'signedHash' ? (
                  <Check className="w-4 h-4 text-green-600" />
                ) : (
                  <Copy className="w-4 h-4 text-gray-500" />
                )}
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-lg bg-gray-50 border border-gray-200">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
              <Signature className="w-4 h-4" />
              <span>签名算法</span>
            </div>
            <p className="text-sm font-medium text-gray-900">{integrityResult.signatureAlgorithm}</p>
          </div>

          <div className="p-4 rounded-lg bg-gray-50 border border-gray-200">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
              <Calendar className="w-4 h-4" />
              <span>签名时间</span>
            </div>
            <p className="text-sm font-medium text-gray-900">{integrityResult.signingTime}</p>
          </div>

          <div className="p-4 rounded-lg bg-gray-50 border border-gray-200">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
              <AlertTriangle className="w-4 h-4" />
              <span>篡改检测</span>
            </div>
            <p className={cn(
              'text-sm font-medium',
              integrityResult.hasModifications ? 'text-red-600' : 'text-green-600'
            )}>
              {integrityResult.hasModifications ? '检测到篡改' : '未检测到篡改'}
            </p>
          </div>
        </div>

        {integrityResult.errors.length > 0 && (
          <div className="p-4 rounded-lg bg-red-50 border border-red-200">
            <h4 className="flex items-center gap-2 text-sm font-semibold text-red-800 mb-2">
              <AlertTriangle className="w-4 h-4" />
              错误信息
            </h4>
            <ul className="space-y-1">
              {integrityResult.errors.map((error, index) => (
                <li key={index} className="text-sm text-red-700">• {error}</li>
              ))}
            </ul>
          </div>
        )}

        {integrityResult.warnings.length > 0 && (
          <div className="p-4 rounded-lg bg-amber-50 border border-amber-200">
            <h4 className="flex items-center gap-2 text-sm font-semibold text-amber-800 mb-2">
              <AlertTriangle className="w-4 h-4" />
              警告信息
            </h4>
            <ul className="space-y-1">
              {integrityResult.warnings.map((warning, index) => (
                <li key={index} className="text-sm text-amber-700">• {warning}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
