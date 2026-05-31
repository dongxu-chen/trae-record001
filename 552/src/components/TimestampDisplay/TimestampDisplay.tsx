import { useState } from 'react';
import { Clock, CheckCircle, XCircle, AlertTriangle, Building, Hash, Fingerprint, ChevronDown, ChevronRight, User, Calendar } from 'lucide-react';
import { TimestampResult, CertificateInfo } from '../../../shared';
import { cn } from '@/lib/utils';

type TimestampStatus = 'valid' | 'invalid' | 'none';

interface TimestampDisplayProps {
  timestampResult: TimestampResult;
}

export default function TimestampDisplay({ timestampResult }: TimestampDisplayProps) {
  const [expandedCerts, setExpandedCerts] = useState<Set<number>>(new Set());

  const getTimestampStatus = (): TimestampStatus => {
    if (!timestampResult.hasTimestamp) {
      return 'none';
    }
    return timestampResult.isValid ? 'valid' : 'invalid';
  };

  const getStatusIcon = (status: TimestampStatus) => {
    switch (status) {
      case 'valid':
        return <CheckCircle className="w-6 h-6 text-emerald-500" />;
      case 'invalid':
        return <XCircle className="w-6 h-6 text-red-500" />;
      case 'none':
        return <AlertTriangle className="w-6 h-6 text-amber-500" />;
    }
  };

  const getStatusText = (status: TimestampStatus) => {
    switch (status) {
      case 'valid':
        return '时间戳有效';
      case 'invalid':
        return '时间戳无效';
      case 'none':
        return '无时间戳';
    }
  };

  const getStatusColor = (status: TimestampStatus) => {
    switch (status) {
      case 'valid':
        return 'border-emerald-200 bg-emerald-50';
      case 'invalid':
        return 'border-red-200 bg-red-50';
      case 'none':
        return 'border-amber-200 bg-amber-50';
    }
  };

  const getCertStatusIcon = (cert: CertificateInfo) => {
    const now = new Date();
    const validTo = new Date(cert.validTo);
    const validFrom = new Date(cert.validFrom);
    
    if (now < validFrom || now > validTo) {
      return <XCircle className="w-4 h-4 text-red-500" />;
    }
    
    return <CheckCircle className="w-4 h-4 text-emerald-500" />;
  };

  const toggleExpand = (index: number) => {
    const newExpanded = new Set(expandedCerts);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedCerts(newExpanded);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const status = getTimestampStatus();
  const { hasTimestamp, timestampTime, timestampAuthority, certificateChain, hashAlgorithm, messageImprint, errors, warnings } = timestampResult;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Clock className="w-6 h-6 text-blue-600" />
        <h3 className="text-lg font-semibold text-gray-900">时间戳</h3>
      </div>

      {(errors.length > 0 || warnings.length > 0) && (
        <div className="space-y-2">
          {errors.map((error, idx) => (
            <div key={`error-${idx}`} className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
              <XCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <span className="text-sm text-red-700">{error}</span>
            </div>
          ))}
          {warnings.map((warning, idx) => (
            <div key={`warning-${idx}`} className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
              <span className="text-sm text-amber-700">{warning}</span>
            </div>
          ))}
        </div>
      )}

      <div className="relative">
        <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-200" />

        <div className="space-y-0">
          <div className="relative pl-14">
            <div className="absolute left-4 top-4 w-5 h-5 rounded-full bg-white border-2 border-gray-300 flex items-center justify-center">
              <div className={cn(
                "w-2 h-2 rounded-full",
                status === 'valid' && 'bg-emerald-500',
                status === 'invalid' && 'bg-red-500',
                status === 'none' && 'bg-amber-500'
              )} />
            </div>

            <div className={cn(
              "border rounded-lg overflow-hidden",
              getStatusColor(status)
            )}>
              <div className="p-4">
                <div className="flex items-center gap-2 mb-4">
                  {getStatusIcon(status)}
                  <span className={cn(
                    "font-medium",
                    status === 'valid' && 'text-emerald-700',
                    status === 'invalid' && 'text-red-700',
                    status === 'none' && 'text-amber-700'
                  )}>
                    {getStatusText(status)}
                  </span>
                </div>

                {hasTimestamp && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="flex items-start gap-3">
                        <Calendar className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
                        <div>
                          <div className="text-sm text-gray-500">时间戳时间</div>
                          <div className="text-gray-900 font-medium">{formatDate(timestampTime)}</div>
                        </div>
                      </div>

                      <div className="flex items-start gap-3">
                        <Building className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
                        <div>
                          <div className="text-sm text-gray-500">时间戳颁发机构（TSA）</div>
                          <div className="text-gray-900 font-medium">{timestampAuthority}</div>
                        </div>
                      </div>

                      <div className="flex items-start gap-3">
                        <Hash className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
                        <div>
                          <div className="text-sm text-gray-500">哈希算法</div>
                          <div className="text-gray-900 font-medium">{hashAlgorithm}</div>
                        </div>
                      </div>

                      <div className="flex items-start gap-3">
                        <Fingerprint className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
                        <div className="min-w-0">
                          <div className="text-sm text-gray-500">消息印记</div>
                          <div className="text-gray-900 font-mono text-xs truncate" title={messageImprint}>
                            {messageImprint}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {!hasTimestamp && (
                  <p className="text-sm text-amber-700">
                    该签名未包含时间戳信息。建议添加时间戳以确保签名的长期有效性。
                  </p>
                )}
              </div>
            </div>
          </div>

          {hasTimestamp && certificateChain.length > 0 && (
            <div className="relative pl-14 mt-4">
              <div className="absolute left-4 top-4 w-5 h-5 rounded-full bg-white border-2 border-gray-300 flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-blue-500" />
              </div>

              <div className="border border-gray-200 bg-white rounded-lg overflow-hidden">
                <div className="p-4 border-b border-gray-200">
                  <div className="flex items-center gap-2">
                    <Fingerprint className="w-5 h-5 text-blue-600" />
                    <span className="font-medium text-gray-900">时间戳证书链</span>
                    <span className="text-sm text-gray-500">({certificateChain.length} 个证书)</span>
                  </div>
                </div>

                <div className="divide-y divide-gray-100">
                  {[...certificateChain].reverse().map((cert, idx) => {
                    const isExpanded = expandedCerts.has(idx);
                    
                    return (
                      <div key={idx} className="p-4">
                        <button
                          onClick={() => toggleExpand(idx)}
                          className="w-full flex items-start justify-between text-left"
                        >
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              {getCertStatusIcon(cert)}
                              <span className="font-medium text-gray-900">
                                {idx === 0 ? '根证书' : `证书 ${idx}`}
                              </span>
                              {cert.isCA && (
                                <span className="px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-700 font-medium">
                                  CA
                                </span>
                              )}
                            </div>
                            
                            <div className="space-y-1 text-sm text-gray-600">
                              <div className="flex items-center gap-2">
                                <User className="w-4 h-4" />
                                <span className="truncate" title={cert.subject}>{cert.subject}</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <Building className="w-4 h-4" />
                                <span className="truncate" title={cert.issuer}>{cert.issuer}</span>
                              </div>
                            </div>
                          </div>
                          
                          {isExpanded ? (
                            <ChevronDown className="w-5 h-5 text-gray-400 flex-shrink-0 ml-4" />
                          ) : (
                            <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0 ml-4" />
                          )}
                        </button>

                        {isExpanded && (
                          <div className="mt-3 pt-3 border-t border-gray-100 space-y-3">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                              <div className="flex items-start gap-2 text-sm">
                                <Calendar className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                                <div>
                                  <div className="text-gray-500">有效期</div>
                                  <div className="text-gray-700">
                                    {formatDate(cert.validFrom)} - {formatDate(cert.validTo)}
                                  </div>
                                </div>
                              </div>
                              
                              <div className="flex items-start gap-2 text-sm">
                                <Fingerprint className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                                <div className="min-w-0">
                                  <div className="text-gray-500">指纹</div>
                                  <div className="text-gray-700 font-mono text-xs truncate" title={cert.fingerprint}>
                                    {cert.fingerprint}
                                  </div>
                                </div>
                              </div>
                              
                              <div className="text-sm">
                                <div className="text-gray-500">序列号</div>
                                <div className="text-gray-700 font-mono text-xs">{cert.serialNumber}</div>
                              </div>
                              
                              <div className="text-sm">
                                <div className="text-gray-500">签名算法</div>
                                <div className="text-gray-700">{cert.signatureAlgorithm}</div>
                              </div>
                              
                              <div className="text-sm">
                                <div className="text-gray-500">密钥用法</div>
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {cert.keyUsage.map((usage, uIdx) => (
                                    <span key={uIdx} className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">
                                      {usage}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
