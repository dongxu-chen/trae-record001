import { cn } from '@/lib/utils'
import {
  Scale,
  CheckCircle,
  XCircle,
  AlertTriangle,
  MinusCircle,
  FileText,
  Gauge
} from 'lucide-react'
import type { ComplianceResult, ComplianceCheck } from '../../../shared'

interface ComplianceReportProps {
  complianceResult: ComplianceResult
}

const standardNames: Record<string, string> = {
  'cn-es': '中国电子签名法',
  'eu-eidas': '欧盟 eIDAS 条例',
  'us-esign': '美国 ESIGN 法案'
}

export default function ComplianceReport({ complianceResult }: ComplianceReportProps) {
  const getStatusConfig = (status: ComplianceCheck['status']) => {
    switch (status) {
      case 'pass':
        return {
          icon: CheckCircle,
          color: 'text-green-600',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          label: '通过'
        }
      case 'fail':
        return {
          icon: XCircle,
          color: 'text-red-600',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          label: '失败'
        }
      case 'warning':
        return {
          icon: AlertTriangle,
          color: 'text-amber-600',
          bgColor: 'bg-amber-50',
          borderColor: 'border-amber-200',
          label: '警告'
        }
      case 'not-applicable':
        return {
          icon: MinusCircle,
          color: 'text-gray-500',
          bgColor: 'bg-gray-50',
          borderColor: 'border-gray-200',
          label: '不适用'
        }
    }
  }

  const getOverallStatusColor = (status: ComplianceResult['overallCompliance']) => {
    switch (status) {
      case 'compliant':
        return 'text-green-600 bg-green-50 border-green-200'
      case 'partially-compliant':
        return 'text-amber-600 bg-amber-50 border-amber-200'
      case 'non-compliant':
        return 'text-red-600 bg-red-50 border-red-200'
    }
  }

  const getOverallStatusLabel = (status: ComplianceResult['overallCompliance']) => {
    switch (status) {
      case 'compliant':
        return '合规'
      case 'partially-compliant':
        return '部分合规'
      case 'non-compliant':
        return '不合规'
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'bg-green-500'
    if (score >= 60) return 'bg-amber-500'
    return 'bg-red-500'
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-200 bg-gray-50">
        <Scale className="w-6 h-6 text-gray-700" />
        <div>
          <h3 className="text-lg font-semibold text-gray-900">合规性检查报告</h3>
          <p className="text-sm text-gray-500">
            依据标准：{standardNames[complianceResult.standard] || complianceResult.standard}
          </p>
        </div>
      </div>

      <div className="p-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className={cn(
            'p-4 rounded-lg border',
            getOverallStatusColor(complianceResult.overallCompliance)
          )}>
            <div className="flex items-center gap-2 text-sm font-medium mb-1">
              <FileText className="w-4 h-4" />
              <span>总体合规状态</span>
            </div>
            <p className="text-xl font-bold">
              {getOverallStatusLabel(complianceResult.overallCompliance)}
            </p>
          </div>

          <div className="p-4 rounded-lg bg-gray-50 border border-gray-200">
            <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-3">
              <Gauge className="w-4 h-4" />
              <span>合规得分</span>
              <span className="ml-auto text-2xl font-bold text-gray-900">{complianceResult.score}/100</span>
            </div>
            <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={cn('h-full rounded-full transition-all duration-500', getScoreColor(complianceResult.score))}
                style={{ width: `${complianceResult.score}%` }}
              />
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <h4 className="text-sm font-semibold text-gray-900">检查详情</h4>
          <div className="space-y-3">
            {complianceResult.checks.map((check) => {
              const config = getStatusConfig(check.status)
              const StatusIcon = config.icon
              return (
                <div
                  key={check.id}
                  className={cn(
                    'p-4 rounded-lg border transition-all hover:shadow-sm',
                    config.bgColor,
                    config.borderColor
                  )}
                >
                  <div className="flex items-start gap-3">
                    <StatusIcon className={cn('w-5 h-5 mt-0.5 flex-shrink-0', config.color)} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h5 className="font-medium text-gray-900">{check.name}</h5>
                        <span className={cn(
                          'px-2 py-0.5 text-xs font-medium rounded-full',
                          config.bgColor,
                          config.color
                        )}>
                          {config.label}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{check.description}</p>
                      <div className="flex flex-wrap gap-4 text-xs">
                        <div className="flex items-center gap-1">
                          <span className="text-gray-500">法规引用：</span>
                          <span className="font-mono text-gray-700">{check.regulation}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-gray-500">证据：</span>
                          <span className="text-gray-700">{check.evidence}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
