import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { CheckCircle, XCircle, AlertTriangle, Clock, Shield, FileText, ArrowLeft, RefreshCw, MapPin, ShieldAlert } from 'lucide-react';
import { useVerificationStore } from '@/store/verificationStore';
import { verificationApi } from '@/services/api';
import { cn } from '@/lib/utils';
import CertificateChain from '@/components/CertificateChain/CertificateChain';
import TimestampDisplay from '@/components/TimestampDisplay/TimestampDisplay';
import IntegrityDisplay from '@/components/IntegrityDisplay/IntegrityDisplay';
import ComplianceReport from '@/components/ComplianceReport/ComplianceReport';
import ReportExport from '@/components/ReportExport/ReportExport';
import SignatureVisualization from '@/components/SignatureVisualization/SignatureVisualization';
import AntiForgeryDisplay from '@/components/AntiForgeryDisplay/AntiForgeryDisplay';
import type { VerifyResponse } from '../../shared';

type TabType = 'certificate' | 'timestamp' | 'integrity' | 'compliance' | 'visualization' | 'antiForgery';

export default function VerifyResultPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { setVerificationResult, isLoading, setIsLoading, error, setError } = useVerificationStore();

  const [result, setResult] = useState<VerifyResponse | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('certificate');

  useEffect(() => {
    if (id) {
      loadResult(id);
    }
  }, [id]);

  const loadResult = async (verifyId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await verificationApi.getVerificationById(verifyId);
      setResult(data);
      setVerificationResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载验证结果失败');
    } finally {
      setIsLoading(false);
    }
  };

  const getResultIcon = (overallResult: string) => {
    switch (overallResult) {
      case 'valid':
        return <CheckCircle className="w-8 h-8 text-emerald-500" />;
      case 'invalid':
        return <XCircle className="w-8 h-8 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="w-8 h-8 text-amber-500" />;
      default:
        return <AlertTriangle className="w-8 h-8 text-gray-500" />;
    }
  };

  const getResultText = (overallResult: string) => {
    switch (overallResult) {
      case 'valid':
        return '验证通过';
      case 'invalid':
        return '验证失败';
      case 'warning':
        return '存在警告';
      default:
        return '未知状态';
    }
  };

  const getResultColor = (overallResult: string) => {
    switch (overallResult) {
      case 'valid':
        return 'text-emerald-700 bg-emerald-50 border-emerald-200';
      case 'invalid':
        return 'text-red-700 bg-red-50 border-red-200';
      case 'warning':
        return 'text-amber-700 bg-amber-50 border-amber-200';
      default:
        return 'text-gray-700 bg-gray-50 border-gray-200';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-600';
    if (score >= 60) return 'text-amber-600';
    return 'text-red-600';
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  const tabs = [
    { id: 'certificate' as TabType, label: '证书链', icon: Shield },
    { id: 'timestamp' as TabType, label: '时间戳', icon: Clock },
    { id: 'integrity' as TabType, label: '完整性', icon: FileText },
    { id: 'compliance' as TabType, label: '合规性', icon: CheckCircle },
    { id: 'visualization' as TabType, label: '签名位置', icon: MapPin },
    { id: 'antiForgery' as TabType, label: '防伪检测', icon: ShieldAlert },
  ];

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8 px-4">
        <div className="max-w-5xl mx-auto">
          <div className="mb-6">
            <div className="h-6 w-32 bg-gray-200 rounded animate-pulse mb-4" />
            <div className="h-8 w-64 bg-gray-200 rounded animate-pulse" />
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="space-y-2">
                  <div className="h-4 w-20 bg-gray-200 rounded animate-pulse" />
                  <div className="h-6 w-24 bg-gray-200 rounded animate-pulse" />
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="h-14 border-b border-gray-200 bg-gray-100 animate-pulse" />
            <div className="p-6 space-y-4">
              <div className="h-20 bg-gray-200 rounded animate-pulse" />
              <div className="h-32 bg-gray-200 rounded animate-pulse" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center py-8 px-4">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 flex items-center justify-center">
            <XCircle className="w-8 h-8 text-red-500" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">加载失败</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => navigate(-1)}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              返回
            </button>
            <button
              onClick={() => id && loadResult(id)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              重试
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!result) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-5xl mx-auto">
        <button
          onClick={() => navigate(-1)}
          className="mb-6 flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          返回
        </button>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
            <div className="flex items-center gap-4">
              {getResultIcon(result.overallResult)}
              <div>
                <h1 className="text-2xl font-bold text-gray-900">验证结果</h1>
                <span className={cn(
                  "inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium border mt-2",
                  getResultColor(result.overallResult)
                )}>
                  {getResultText(result.overallResult)}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-sm text-gray-500">验证得分</div>
                <div className={cn("text-3xl font-bold", getScoreColor(result.score))}>
                  {result.score}
                  <span className="text-lg text-gray-400">/100</span>
                </div>
              </div>
              <ReportExport verificationId={result.id} />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-4 border-t border-gray-100">
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="text-xs text-gray-500 mb-1">文件名</div>
              <div className="text-sm font-medium text-gray-900 truncate" title={result.fileInfo.name}>
                {result.fileInfo.name}
              </div>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="text-xs text-gray-500 mb-1">文件大小</div>
              <div className="text-sm font-medium text-gray-900">
                {formatFileSize(result.fileInfo.size)}
              </div>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="text-xs text-gray-500 mb-1">签名格式</div>
              <div className="text-sm font-medium text-gray-900">{result.signatureFormat}</div>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="text-xs text-gray-500 mb-1">验证时间</div>
              <div className="text-sm font-medium text-gray-900">{formatDate(result.timestamp)}</div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="border-b border-gray-200">
            <nav className="flex overflow-x-auto">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isRelevant = tab.id === 'visualization'
                  ? result.results.visualization?.hasVisualRepresentation
                  : tab.id === 'antiForgery'
                  ? !!result.results.antiForgery
                  : true;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cn(
                      "flex-1 flex items-center justify-center gap-2 px-4 py-4 text-sm font-medium border-b-2 transition-colors whitespace-nowrap min-w-fit",
                      activeTab === tab.id
                        ? "border-blue-600 text-blue-600 bg-blue-50/50"
                        : isRelevant
                        ? "border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50"
                        : "border-transparent text-gray-300"
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    {tab.label}
                  </button>
                );
              })}
            </nav>
          </div>

          <div className="p-6">
            {activeTab === 'certificate' && (
              <CertificateChain chainResult={result.results.certificateChain} />
            )}
            {activeTab === 'timestamp' && (
              <TimestampDisplay timestampResult={result.results.timestamp} />
            )}
            {activeTab === 'integrity' && (
              <IntegrityDisplay integrityResult={result.results.integrity} />
            )}
            {activeTab === 'compliance' && (
              <ComplianceReport complianceResult={result.results.compliance} />
            )}
            {activeTab === 'visualization' && (
              <SignatureVisualization visualization={result.results.visualization} />
            )}
            {activeTab === 'antiForgery' && (
              <AntiForgeryDisplay antiForgeryResult={result.results.antiForgery} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
