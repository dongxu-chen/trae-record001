import { useState } from 'react';
import { Download, FileText, FileSpreadsheet, Share2, CheckCircle, Loader2 } from 'lucide-react';
import { reportApi } from '@/services/api';
import { useVerificationStore } from '@/store/verificationStore';
import { cn } from '@/lib/utils';

interface ReportExportProps {
  verificationId: string;
  className?: string;
}

export default function ReportExport({ verificationId, className }: ReportExportProps) {
  const [exportingFormat, setExportingFormat] = useState<'pdf' | 'html' | null>(null);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);
  const [shareLinkCopied, setShareLinkCopied] = useState(false);

  const handleExportPDF = async () => {
    setExportingFormat('pdf');
    try {
      await reportApi.downloadPDFReport(verificationId);
      setExportSuccess('pdf');
      setTimeout(() => setExportSuccess(null), 3000);
    } catch (error) {
      console.error('Failed to export PDF:', error);
    } finally {
      setExportingFormat(null);
    }
  };

  const handleExportHTML = async () => {
    setExportingFormat('html');
    try {
      const html = await reportApi.getHTMLReport(verificationId);
      const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `verification-report-${verificationId}.html`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setExportSuccess('html');
      setTimeout(() => setExportSuccess(null), 3000);
    } catch (error) {
      console.error('Failed to export HTML:', error);
    } finally {
      setExportingFormat(null);
    }
  };

  const handleShareLink = async () => {
    const shareUrl = `${window.location.origin}/verify/${verificationId}`;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setShareLinkCopied(true);
      setTimeout(() => setShareLinkCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy share link:', error);
    }
  };

  return (
    <div className={cn('bg-white rounded-xl shadow-sm border border-gray-100 p-6', className)}>
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <FileText className="w-5 h-5 text-blue-600" />
        导出验证报告
      </h3>
      <p className="text-sm text-gray-600 mb-6">
        导出完整的验证报告，包含所有验证细节和合规性检查结果，可作为法律证据保存。
      </p>
      
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <button
          onClick={handleExportPDF}
          disabled={exportingFormat !== null}
          className={cn(
            'flex flex-col items-center justify-center p-4 rounded-lg border-2 transition-all duration-200',
            'hover:border-blue-400 hover:bg-blue-50',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            exportSuccess === 'pdf' ? 'border-green-400 bg-green-50' : 'border-gray-200'
          )}
        >
          {exportingFormat === 'pdf' ? (
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-2" />
          ) : exportSuccess === 'pdf' ? (
            <CheckCircle className="w-8 h-8 text-green-600 mb-2" />
          ) : (
            <FileSpreadsheet className="w-8 h-8 text-red-500 mb-2" />
          )}
          <span className="font-medium text-gray-900">
            {exportSuccess === 'pdf' ? '导出成功' : 'PDF 格式'}
          </span>
          <span className="text-xs text-gray-500 mt-1">适合打印和存档</span>
        </button>

        <button
          onClick={handleExportHTML}
          disabled={exportingFormat !== null}
          className={cn(
            'flex flex-col items-center justify-center p-4 rounded-lg border-2 transition-all duration-200',
            'hover:border-blue-400 hover:bg-blue-50',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            exportSuccess === 'html' ? 'border-green-400 bg-green-50' : 'border-gray-200'
          )}
        >
          {exportingFormat === 'html' ? (
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-2" />
          ) : exportSuccess === 'html' ? (
            <CheckCircle className="w-8 h-8 text-green-600 mb-2" />
          ) : (
            <FileText className="w-8 h-8 text-orange-500 mb-2" />
          )}
          <span className="font-medium text-gray-900">
            {exportSuccess === 'html' ? '导出成功' : 'HTML 格式'}
          </span>
          <span className="text-xs text-gray-500 mt-1">适合浏览器查看</span>
        </button>

        <button
          onClick={handleShareLink}
          className="flex flex-col items-center justify-center p-4 rounded-lg border-2 border-gray-200 transition-all duration-200 hover:border-blue-400 hover:bg-blue-50"
        >
          {shareLinkCopied ? (
            <CheckCircle className="w-8 h-8 text-green-600 mb-2" />
          ) : (
            <Share2 className="w-8 h-8 text-blue-500 mb-2" />
          )}
          <span className="font-medium text-gray-900">
            {shareLinkCopied ? '已复制' : '分享链接'}
          </span>
          <span className="text-xs text-gray-500 mt-1">复制验证结果链接</span>
        </button>
      </div>

      <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
        <p className="text-sm text-amber-800">
          <strong>注意：</strong>本验证报告仅作为技术验证参考，具体法律效力请以相关法律法规和司法机关认定为准。
        </p>
      </div>
    </div>
  );
}
