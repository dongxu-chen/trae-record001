import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  Clock,
  FileCheck2,
  Award,
  CheckCircle2,
  FileText,
  Upload,
  Play,
  MapPin,
  ShieldAlert,
  Layers,
} from 'lucide-react';
import FileUpload from '@/components/FileUpload/FileUpload';
import VerificationProgress from '@/components/VerificationProgress/VerificationProgress';
import VerifyOptions from '@/components/VerifyOptions/VerifyOptions';
import BatchUpload from '@/components/BatchUpload/BatchUpload';
import { useVerificationStore } from '@/store/verificationStore';
import { verificationApi } from '@/services/api';
import { cn } from '@/lib/utils';

export default function HomePage() {
  const navigate = useNavigate();
  const [showOptions, setShowOptions] = useState(false);

  const {
    currentFile,
    verifyOptions,
    isVerifying,
    setIsVerifying,
    setProgress,
    setCurrentStep,
    setVerificationResult,
    setError,
    addVerificationToHistory,
  } = useVerificationStore();

  const trustBadges = [
    { name: 'ISO 27001', icon: Award },
    { name: '国密认证', icon: ShieldCheck },
    { name: 'eIDAS 合规', icon: CheckCircle2 },
    { name: 'ESIGN 法案', icon: FileText },
  ];

  const supportedFormats = [
    {
      id: 'pades',
      name: 'PAdES',
      description: 'PDF 高级电子签名',
      color: 'from-red-500 to-orange-500',
    },
    {
      id: 'xades',
      name: 'XAdES',
      description: 'XML 高级电子签名',
      color: 'from-blue-500 to-cyan-500',
    },
    {
      id: 'cades',
      name: 'CAdES',
      description: 'CMS 高级电子签名',
      color: 'from-green-500 to-emerald-500',
    },
  ];

  const features = [
    {
      icon: ShieldCheck,
      title: '证书链验证',
      description: '完整的证书信任链验证，确保证书由可信机构签发，支持多级CA链验证。',
      color: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-100 dark:bg-blue-900/30',
    },
    {
      icon: Clock,
      title: '时间戳验证',
      description: '验证可信时间戳的有效性，确保签名时间的不可否认性和完整性。',
      color: 'text-green-600 dark:text-green-400',
      bgColor: 'bg-green-100 dark:bg-green-900/30',
    },
    {
      icon: FileCheck2,
      title: '完整性验证',
      description: '比对文档哈希值，检测文件是否被篡改，确保签名内容的完整性。',
      color: 'text-purple-600 dark:text-purple-400',
      bgColor: 'bg-purple-100 dark:bg-purple-900/30',
    },
    {
      icon: MapPin,
      title: '签名可视化',
      description: '在PDF文档中标注签名位置，直观展示签名在文档中的布局。',
      color: 'text-cyan-600 dark:text-cyan-400',
      bgColor: 'bg-cyan-100 dark:bg-cyan-900/30',
    },
    {
      icon: ShieldAlert,
      title: '防伪检测',
      description: '识别复制粘贴的假签名，检测图像签名和增量更新等伪造手段。',
      color: 'text-red-600 dark:text-red-400',
      bgColor: 'bg-red-100 dark:bg-red-900/30',
    },
    {
      icon: Layers,
      title: '批量验证',
      description: '支持同时上传多个文档进行并行验证，提升批量处理效率。',
      color: 'text-amber-600 dark:text-amber-400',
      bgColor: 'bg-amber-100 dark:bg-amber-900/30',
    },
  ];

  const simulateProgress = () => {
    const steps = [
      { id: 'format', name: '格式检测', delay: 500, progress: 15 },
      { id: 'certificate', name: '证书链验证', delay: 1000, progress: 35 },
      { id: 'timestamp', name: '时间戳验证', delay: 800, progress: 55 },
      { id: 'integrity', name: '完整性验证', delay: 1200, progress: 75 },
      { id: 'compliance', name: '合规性检查', delay: 1000, progress: 90 },
      { id: 'report', name: '生成报告', delay: 500, progress: 100 },
    ];

    let currentProgress = 0;
    steps.forEach((step, index) => {
      setTimeout(() => {
        setCurrentStep(step.id);
        currentProgress = step.progress;
        setProgress(currentProgress);
      }, steps.slice(0, index).reduce((acc, s) => acc + s.delay, 0));
    });
  };

  const handleVerify = async () => {
    if (!currentFile) return;

    setIsVerifying(true);
    setProgress(0);
    setCurrentStep('');
    setError(null);

    try {
      simulateProgress();

      const result = await verificationApi.uploadAndVerify(currentFile, verifyOptions);

      setVerificationResult(result);
      addVerificationToHistory({
        id: result.id,
        fileName: result.fileInfo.name,
        fileHash: result.fileInfo.hash,
        signatureFormat: result.signatureFormat,
        overallResult: result.overallResult,
        score: result.score,
        createdAt: new Date().toISOString(),
        status: result.status,
        results: result.results,
      });

      setTimeout(() => {
        navigate(`/result/${result.id}`);
      }, 500);
    } catch (err) {
      setError(err instanceof Error ? err.message : '验证失败，请重试');
      setIsVerifying(false);
      setProgress(0);
    }
  };

  return (
    <div className="min-h-screen">
      <div className="relative overflow-hidden bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMiIvPjwvZz48L2c+PC9zdmc+')] opacity-50" />
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-400 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-pulse" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-purple-400 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-pulse" />

        <div className="relative max-w-6xl mx-auto px-4 py-16 sm:px-6 lg:px-8">
          <div className="text-center">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white mb-6 tracking-tight">
              电子签名法律效力验证工具
            </h1>
            <p className="text-xl text-blue-100 dark:text-gray-300 mb-8 max-w-3xl mx-auto">
              快速验证 PAdES、XAdES、CAdES 电子签名的法律效力，支持多国合规标准，确保证书链完整、时间戳有效、文件未篡改。
            </p>

            <div className="flex flex-wrap justify-center gap-4 mb-12">
              {trustBadges.map((badge) => {
                const BadgeIcon = badge.icon;
                return (
                  <div
                    key={badge.name}
                    className="flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-sm rounded-full border border-white/20"
                  >
                    <BadgeIcon className="w-5 h-5 text-blue-200" />
                    <span className="text-white/90 font-medium text-sm">{badge.name}</span>
                  </div>
                );
              })}
            </div>

            <div className="max-w-2xl mx-auto">
              <FileUpload />
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
        <div className="mb-12">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6 text-center">
            支持的签名格式
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {supportedFormats.map((format) => (
              <div
                key={format.id}
                className="relative overflow-hidden rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 hover:shadow-lg transition-all duration-300 group"
              >
                <div className={cn('absolute top-0 left-0 right-0 h-1 bg-gradient-to-r', format.color)} />
                <h3 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2 group-hover:translate-x-1 transition-transform">
                  {format.name}
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  {format.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {currentFile && !isVerifying && (
          <div className="mb-8">
            <button
              onClick={() => setShowOptions(!showOptions)}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors font-medium"
            >
              <Upload className="w-5 h-5" />
              {showOptions ? '收起验证选项' : '展开验证选项'}
            </button>

            {showOptions && (
              <div className="mt-6 p-6 bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm">
                <VerifyOptions />
              </div>
            )}
          </div>
        )}

        {isVerifying && (
          <div className="mb-8 p-6 bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm">
            <VerificationProgress />
          </div>
        )}

        {currentFile && !isVerifying && (
          <div className="text-center mb-8">
            <button
              onClick={handleVerify}
              className="inline-flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-semibold text-lg rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200"
            >
              <Play className="w-6 h-6 fill-current" />
              开始验证
            </button>
          </div>
        )}

        <div className="mb-12">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6 text-center">
            核心验证功能
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {features.map((feature) => {
              const FeatureIcon = feature.icon;
              return (
                <div
                  key={feature.title}
                  className="p-6 bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-all duration-300"
                >
                  <div className={cn('inline-flex p-3 rounded-xl mb-4', feature.bgColor)}>
                    <FeatureIcon className={cn('w-6 h-6', feature.color)} />
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-3">
                    {feature.title}
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400 leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        <div className="mb-12">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2 text-center">
            批量验证
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mb-6 text-center">
            同时上传多个文件进行并行验证，最多支持20个文件
          </p>
          <div className="max-w-3xl mx-auto p-6 bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm">
            <BatchUpload />
          </div>
        </div>
      </div>
    </div>
  );
}
