import { useState, useCallback } from 'react';
import { Globe, Download, FileText, BarChart3, TrendingUp, AlertTriangle } from 'lucide-react';
import BatchScanPanel from '@/components/BatchScanPanel';
import type { BatchScanSession } from '@/types';
import { generateBatchFixSummary } from '@/utils/codeFixGenerator';

export default function BatchScan() {
  const [session, setSession] = useState<BatchScanSession | null>(null);

  const handleComplete = useCallback((newSession: BatchScanSession) => {
    setSession(newSession);
  }, []);

  const handleDownloadReport = useCallback(() => {
    if (!session) return;

    const allIssues = session.results.flatMap((r) => r.report?.issues || []);
    const summary = generateBatchFixSummary(allIssues);

    const report = {
      session: session.id,
      name: session.name,
      createdAt: session.createdAt,
      completedAt: session.completedAt,
      overallPassRate: session.overallPassRate,
      totalIssues: session.totalIssues,
      results: session.results.map((r) => ({
        url: r.url,
        title: r.title,
        passRate: r.report?.passRate,
        issuesCount: r.report?.failed,
        criticalCount: r.report?.criticalCount,
        majorCount: r.report?.majorCount,
        minorCount: r.report?.minorCount,
      })),
      codeFixSummary: summary,
    };

    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `batch-scan-report-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [session]);

  const handleDownloadCssFixes = useCallback(() => {
    if (!session) return;
    const allIssues = session.results.flatMap((r) => r.report?.issues || []);
    const summary = generateBatchFixSummary(allIssues);

    const blob = new Blob([summary], { type: 'text/css' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `color-a11y-fixes-${Date.now()}.css`;
    a.click();
    URL.revokeObjectURL(url);
  }, [session]);

  const getPassRateColor = (rate: number) => {
    if (rate >= 80) return 'text-[#00d4aa]';
    if (rate >= 50) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getPassBgColor = (rate: number) => {
    if (rate >= 80) return 'bg-[#00d4aa]';
    if (rate >= 50) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#00d4aa]/10 text-[#00d4aa] text-sm font-medium">
          <Globe className="w-4 h-4" />
          全站扫描
        </div>
        <h1 className="text-3xl md:text-4xl font-bold text-zinc-100">
          批量页面无障碍检测
        </h1>
        <p className="text-zinc-500 max-w-xl mx-auto">
          同时扫描多个页面，生成全站无障碍检测报告。支持手动输入 URL 或通过 Sitemap 自动发现。
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <BatchScanPanel onComplete={handleComplete} />
        </div>

        <div className="space-y-6">
          <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6">
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 className="w-5 h-5 text-[#00d4aa]" />
              <h3 className="text-lg font-semibold text-zinc-200">扫描统计</h3>
            </div>

            {session ? (
              <div className="space-y-4">
                <div className="text-center p-4 rounded-lg bg-zinc-950">
                  <p className={`text-4xl font-bold font-mono ${getPassRateColor(session.overallPassRate)}`}>
                    {session.overallPassRate}%
                  </p>
                  <p className="text-sm text-zinc-500 mt-1">平均合规率</p>
                </div>

                <div className="w-full h-2 rounded-full bg-zinc-800 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 ${getPassBgColor(session.overallPassRate)}`}
                    style={{ width: `${session.overallPassRate}%` }}
                  />
                </div>

                <div className="grid grid-cols-2 gap-3 text-center">
                  <div className="p-3 rounded-lg bg-zinc-950">
                    <p className="text-2xl font-bold text-zinc-200">{session.results.length}</p>
                    <p className="text-xs text-zinc-500">扫描页面</p>
                  </div>
                  <div className="p-3 rounded-lg bg-zinc-950">
                    <p className="text-2xl font-bold text-[#ff6b35]">{session.totalIssues}</p>
                    <p className="text-xs text-zinc-500">问题总数</p>
                  </div>
                </div>

                <div className="space-y-2 pt-2">
                  <p className="text-xs text-zinc-500">各页面合规率</p>
                  {session.results.map((result, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <span className="text-xs text-zinc-500 truncate w-20" title={result.title}>
                        {result.title}
                      </span>
                      <div className="flex-1 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                        <div
                          className={`h-full ${getPassBgColor(result.report?.passRate || 0)}`}
                          style={{ width: `${result.report?.passRate || 0}%` }}
                        />
                      </div>
                      <span className={`text-xs font-mono w-10 text-right ${getPassRateColor(result.report?.passRate || 0)}`}>
                        {result.report?.passRate || 0}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-12">
                <div className="w-16 h-16 rounded-full bg-zinc-800 flex items-center justify-center mx-auto mb-3">
                  <Globe className="w-8 h-8 text-zinc-600" />
                </div>
                <p className="text-sm text-zinc-500">开始扫描后这里显示统计数据</p>
              </div>
            )}
          </div>

          {session && (
            <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6 space-y-3">
              <h3 className="text-sm font-medium text-zinc-300">导出报告</h3>
              <button
                onClick={handleDownloadReport}
                className="w-full py-2.5 rounded-lg bg-zinc-800 text-zinc-200 text-sm font-medium hover:bg-zinc-700 transition-colors flex items-center justify-center gap-2"
              >
                <FileText className="w-4 h-4" />
                下载 JSON 报告
              </button>
              <button
                onClick={handleDownloadCssFixes}
                className="w-full py-2.5 rounded-lg bg-[#00d4aa]/10 text-[#00d4aa] text-sm font-medium hover:bg-[#00d4aa]/20 transition-colors flex items-center justify-center gap-2"
              >
                <Download className="w-4 h-4" />
                下载 CSS 修复代码
              </button>
            </div>
          )}

          <div className="bg-gradient-to-br from-[#00d4aa]/10 to-transparent rounded-xl border border-[#00d4aa]/20 p-5">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="w-5 h-5 text-[#00d4aa]" />
              <h3 className="text-sm font-semibold text-zinc-200">扫描提示</h3>
            </div>
            <ul className="space-y-2 text-xs text-zinc-400">
              <li className="flex items-start gap-2">
                <AlertTriangle className="w-3.5 h-3.5 text-yellow-500 mt-0.5 shrink-0" />
                大型网站建议使用 sitemap 模式自动发现页面
              </li>
              <li className="flex items-start gap-2">
                <AlertTriangle className="w-3.5 h-3.5 text-yellow-500 mt-0.5 shrink-0" />
                扫描时请确保目标网站可正常访问
              </li>
              <li className="flex items-start gap-2">
                <AlertTriangle className="w-3.5 h-3.5 text-yellow-500 mt-0.5 shrink-0" />
                需要登录的页面请使用 Chrome 扩展模式
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
