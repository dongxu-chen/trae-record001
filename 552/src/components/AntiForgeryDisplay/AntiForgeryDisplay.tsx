import { ShieldAlert, ShieldCheck, ShieldQuestion, AlertTriangle, CheckCircle, XCircle, Info } from 'lucide-react';
import type { AntiForgeryResult } from '../../../shared';
import { cn } from '@/lib/utils';

interface AntiForgeryDisplayProps {
  antiForgeryResult?: AntiForgeryResult;
}

export default function AntiForgeryDisplay({ antiForgeryResult }: AntiForgeryDisplayProps) {
  if (!antiForgeryResult) {
    return (
      <div className="text-center py-8">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
          <ShieldQuestion className="w-8 h-8 text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">未执行防伪检测</h3>
        <p className="text-gray-500 text-sm">该文档未进行防伪检测分析</p>
      </div>
    );
  }

  const { isAuthentic, overallRisk, score, checks, warnings, errors } = antiForgeryResult;

  const getRiskConfig = (risk: string) => {
    switch (risk) {
      case 'high':
        return { color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', icon: ShieldAlert, label: '高风险' };
      case 'medium':
        return { color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', icon: AlertTriangle, label: '中风险' };
      default:
        return { color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', icon: ShieldCheck, label: '低风险' };
    }
  };

  const riskConfig = getRiskConfig(overallRisk);
  const RiskIcon = riskConfig.icon;

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pass':
        return <CheckCircle className="w-5 h-5 text-emerald-500" />;
      case 'fail':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-amber-500" />;
      default:
        return <Info className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pass':
        return 'bg-emerald-100 text-emerald-700';
      case 'fail':
        return 'bg-red-100 text-red-700';
      case 'warning':
        return 'bg-amber-100 text-amber-700';
      default:
        return 'bg-gray-100 text-gray-500';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'pass': return '通过';
      case 'fail': return '不通过';
      case 'warning': return '警告';
      default: return '不适用';
    }
  };

  const getRiskBadge = (risk: string) => {
    switch (risk) {
      case 'high': return 'bg-red-100 text-red-700';
      case 'medium': return 'bg-amber-100 text-amber-700';
      default: return 'bg-emerald-100 text-emerald-700';
    }
  };

  const getRiskLabel = (risk: string) => {
    switch (risk) {
      case 'high': return '高';
      case 'medium': return '中';
      default: return '低';
    }
  };

  return (
    <div className="space-y-6">
      <div className={cn('p-6 rounded-xl border', riskConfig.bg, riskConfig.border)}>
        <div className="flex items-center gap-4">
          <RiskIcon className={cn('w-12 h-12', riskConfig.color)} />
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className={cn('text-xl font-bold', riskConfig.color)}>
                {isAuthentic ? '签名真实可信' : '签名存在伪造嫌疑'}
              </h3>
              <span className={cn('px-2 py-0.5 rounded text-xs font-medium', getRiskBadge(overallRisk))}>
                {riskConfig.label}
              </span>
            </div>
            <p className="text-gray-600 text-sm">
              防伪评分：<strong className={riskConfig.color}>{score}</strong>/100 | 共检测 {checks.length} 项
            </p>
          </div>
          <div className="text-right">
            <div className={cn('text-4xl font-bold', riskConfig.color)}>{score}</div>
            <div className="text-xs text-gray-500">防伪评分</div>
          </div>
        </div>
        <div className="mt-4 w-full bg-gray-200 rounded-full h-2.5">
          <div
            className={cn(
              'h-2.5 rounded-full transition-all',
              score >= 80 ? 'bg-emerald-500' : score >= 50 ? 'bg-amber-500' : 'bg-red-500'
            )}
            style={{ width: `${score}%` }}
          />
        </div>
      </div>

      {warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <h4 className="font-medium text-amber-700 mb-2 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />警告信息
          </h4>
          <ul className="space-y-1">
            {warnings.map((w, i) => (
              <li key={i} className="text-sm text-amber-600">• {w}</li>
            ))}
          </ul>
        </div>
      )}

      {errors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h4 className="font-medium text-red-700 mb-2 flex items-center gap-2">
            <XCircle className="w-4 h-4" />错误信息
          </h4>
          <ul className="space-y-1">
            {errors.map((e, i) => (
              <li key={i} className="text-sm text-red-600">• {e}</li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <h4 className="font-medium text-gray-900 mb-3">检测项目明细</h4>
        <div className="space-y-3">
          {checks.map((check) => (
            <div
              key={check.id}
              className={cn(
                'border rounded-lg p-4 transition-colors',
                check.status === 'fail' ? 'border-red-200 bg-red-50/50' :
                check.status === 'warning' ? 'border-amber-200 bg-amber-50/50' :
                check.status === 'pass' ? 'border-emerald-200 bg-emerald-50/50' :
                'border-gray-200 bg-gray-50/50'
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 flex-1">
                  {getStatusIcon(check.status)}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-gray-900 text-sm">{check.name}</span>
                      <span className={cn('px-1.5 py-0.5 rounded text-xs font-medium', getStatusBadge(check.status))}>
                        {getStatusLabel(check.status)}
                      </span>
                      <span className={cn('px-1.5 py-0.5 rounded text-xs font-medium', getRiskBadge(check.risk))}>
                        风险: {getRiskLabel(check.risk)}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{check.description}</p>
                    {check.evidence && (
                      <p className="text-xs text-gray-600 mt-2 bg-white/60 rounded p-2 border border-gray-100">
                        💡 {check.evidence}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
