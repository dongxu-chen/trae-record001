import { useState } from 'react';
import { Shield, ShieldCheck, ShieldAlert, ShieldX, ChevronDown, ChevronRight, Fingerprint, Calendar, User, Building } from 'lucide-react';
import { CertificateChainResult, CertificateInfo } from '../../../shared';
import { cn } from '@/lib/utils';

type CertificateStatus = 'valid' | 'expired' | 'expiring-soon';

interface CertificateChainProps {
  chainResult: CertificateChainResult;
}

export default function CertificateChain({ chainResult }: CertificateChainProps) {
  const [expandedCerts, setExpandedCerts] = useState<Set<number>>(new Set([0]));

  const getCertificateStatus = (cert: CertificateInfo): CertificateStatus => {
    const now = new Date();
    const validTo = new Date(cert.validTo);
    const validFrom = new Date(cert.validFrom);
    
    const thirtyDays = 30 * 24 * 60 * 60 * 1000;
    
    if (now < validFrom || now > validTo) {
      return 'expired';
    }
    
    if (validTo.getTime() - now.getTime() < thirtyDays) {
      return 'expiring-soon';
    }
    
    return 'valid';
  };

  const getStatusIcon = (status: CertificateStatus) => {
    switch (status) {
      case 'valid':
        return <ShieldCheck className="w-5 h-5 text-emerald-500" />;
      case 'expiring-soon':
        return <ShieldAlert className="w-5 h-5 text-amber-500" />;
      case 'expired':
        return <ShieldX className="w-5 h-5 text-red-500" />;
    }
  };

  const getStatusColor = (status: CertificateStatus) => {
    switch (status) {
      case 'valid':
        return 'border-emerald-200 bg-emerald-50';
      case 'expiring-soon':
        return 'border-amber-200 bg-amber-50';
      case 'expired':
        return 'border-red-200 bg-red-50';
    }
  };

  const getStatusText = (status: CertificateStatus) => {
    switch (status) {
      case 'valid':
        return '有效';
      case 'expiring-soon':
        return '即将过期';
      case 'expired':
        return '已过期';
    }
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
    });
  };

  const { certificates, trustPath, revocationStatus, errors, warnings } = chainResult;
  const reversedCerts = [...certificates].reverse();

  const getRevocationStatusIcon = () => {
    switch (revocationStatus) {
      case 'valid':
        return <ShieldCheck className="w-4 h-4 text-emerald-500" />;
      case 'revoked':
        return <ShieldX className="w-4 h-4 text-red-500" />;
      case 'unknown':
        return <ShieldAlert className="w-4 h-4 text-amber-500" />;
    }
  };

  const getRevocationStatusText = () => {
    switch (revocationStatus) {
      case 'valid':
        return '未吊销';
      case 'revoked':
        return '已吊销';
      case 'unknown':
        return '未知';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Shield className="w-6 h-6 text-blue-600" />
        <h3 className="text-lg font-semibold text-gray-900">证书链</h3>
      </div>

      {(errors.length > 0 || warnings.length > 0) && (
        <div className="space-y-2">
          {errors.map((error, idx) => (
            <div key={`error-${idx}`} className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
              <ShieldX className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <span className="text-sm text-red-700">{error}</span>
            </div>
          ))}
          {warnings.map((warning, idx) => (
            <div key={`warning-${idx}`} className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <ShieldAlert className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
              <span className="text-sm text-amber-700">{warning}</span>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center gap-2 text-sm text-gray-600">
        <span className="font-medium">吊销状态：</span>
        <div className="flex items-center gap-1">
          {getRevocationStatusIcon()}
          <span className={cn(
            revocationStatus === 'valid' && 'text-emerald-700',
            revocationStatus === 'revoked' && 'text-red-700',
            revocationStatus === 'unknown' && 'text-amber-700'
          )}>
            {getRevocationStatusText()}
          </span>
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-sm font-medium text-gray-700">信任路径</div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          {trustPath.map((subject, idx) => (
            <div key={idx} className="flex items-center">
              <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded-md">{subject}</span>
              {idx < trustPath.length - 1 && (
                <ChevronRight className="w-4 h-4 text-gray-400 mx-1" />
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="relative">
        <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-200" />
        
        <div className="space-y-4">
          {reversedCerts.map((cert, idx) => {
            const status = getCertificateStatus(cert);
            const isExpanded = expandedCerts.has(idx);
            const isRoot = idx === 0;
            
            return (
              <div key={idx} className="relative pl-14">
                <div className="absolute left-4 top-4 w-5 h-5 rounded-full bg-white border-2 border-gray-300 flex items-center justify-center">
                  <div className={cn(
                    "w-2 h-2 rounded-full",
                    status === 'valid' && 'bg-emerald-500',
                    status === 'expiring-soon' && 'bg-amber-500',
                    status === 'expired' && 'bg-red-500'
                  )} />
                </div>
                
                <div className={cn(
                  "border rounded-lg overflow-hidden transition-all",
                  getStatusColor(status)
                )}>
                  <button
                    onClick={() => toggleExpand(idx)}
                    className="w-full p-4 flex items-start justify-between text-left hover:bg-white/50 transition-colors"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        {getStatusIcon(status)}
                        <span className="font-medium text-gray-900">
                          {isRoot ? '根证书' : `证书 ${idx}`}
                        </span>
                        <span className={cn(
                          "px-2 py-0.5 text-xs rounded-full font-medium",
                          status === 'valid' && 'bg-emerald-100 text-emerald-700',
                          status === 'expiring-soon' && 'bg-amber-100 text-amber-700',
                          status === 'expired' && 'bg-red-100 text-red-700'
                        )}>
                          {getStatusText(status)}
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
                    <div className="px-4 pb-4 border-t border-gray-200/50 pt-3 space-y-3">
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
                        
                        <div className="text-sm">
                          <div className="text-gray-500">证书类型</div>
                          <div className="flex gap-2 mt-1">
                            {cert.isSelfSigned && (
                              <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded">
                                自签名
                              </span>
                            )}
                            {cert.isTrustedRoot && (
                              <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded">
                                信任根
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
