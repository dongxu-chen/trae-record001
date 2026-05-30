import { useState, useCallback } from 'react';
import { Link as LinkIcon, Play, Pause, CheckCircle, XCircle, Loader2, Globe, List, Plus, Trash2 } from 'lucide-react';
import type { PageScanResult, BatchScanSession } from '@/types';
import { batchScanPages } from '@/utils/batchScan';

interface BatchScanPanelProps {
  onComplete?: (session: BatchScanSession) => void;
}

export default function BatchScanPanel({ onComplete }: BatchScanPanelProps) {
  const [urls, setUrls] = useState<string[]>(['https://example.com/']);
  const [scanMode, setScanMode] = useState<'manual' | 'sitemap'>('manual');
  const [sitemapUrl, setSitemapUrl] = useState('');
  const [scanning, setScanning] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [results, setResults] = useState<PageScanResult[]>([]);
  const [session, setSession] = useState<BatchScanSession | null>(null);

  const addUrl = useCallback(() => {
    setUrls([...urls, '']);
  }, [urls]);

  const removeUrl = useCallback((index: number) => {
    setUrls(urls.filter((_, i) => i !== index));
  }, [urls]);

  const updateUrl = useCallback((index: number, value: string) => {
    const newUrls = [...urls];
    newUrls[index] = value;
    setUrls(newUrls);
  }, [urls]);

  const handleProgress = useCallback((index: number, result: PageScanResult) => {
    setCurrentIndex(index + 1);
    setResults((prev) => {
      const newResults = [...prev];
      newResults[index] = result;
      return newResults;
    });
  }, []);

  const startScan = useCallback(async () => {
    const validUrls = urls.filter((u) => u.trim().length > 0 && u.startsWith('http'));
    if (validUrls.length === 0) return;

    setScanning(true);
    setResults(new Array(validUrls.length).fill(null));
    setCurrentIndex(0);

    try {
      const newSession = await batchScanPages(validUrls, handleProgress);
      setSession(newSession);
      if (onComplete) onComplete(newSession);
    } catch (error) {
      console.error('Scan failed:', error);
    } finally {
      setScanning(false);
    }
  }, [urls, handleProgress, onComplete]);

  const getStatusIcon = (result: PageScanResult | null, index: number) => {
    if (!result) {
      if (index < currentIndex) return <XCircle className="w-4 h-4 text-red-500" />;
      return null;
    }
    if (result.status === 'scanning') return <Loader2 className="w-4 h-4 text-[#00d4aa] animate-spin" />;
    if (result.status === 'completed') return <CheckCircle className="w-4 h-4 text-[#00d4aa]" />;
    if (result.status === 'error') return <XCircle className="w-4 h-4 text-red-500" />;
    return null;
  };

  const getPassRateColor = (rate: number) => {
    if (rate >= 80) return 'text-[#00d4aa]';
    if (rate >= 50) return 'text-yellow-500';
    return 'text-red-500';
  };

  return (
    <div className="space-y-6">
      <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-[#00d4aa]/10 flex items-center justify-center">
            <Globe className="w-5 h-5 text-[#00d4aa]" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-zinc-100">批量页面扫描</h3>
            <p className="text-sm text-zinc-500">同时扫描多个页面，生成全站无障碍检测报告</p>
          </div>
        </div>

        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setScanMode('manual')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
              scanMode === 'manual'
                ? 'bg-[#00d4aa]/10 text-[#00d4aa] border border-[#00d4aa]/20'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
            }`}
          >
            <List className="w-4 h-4" />
            手动输入
          </button>
          <button
            onClick={() => setScanMode('sitemap')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
              scanMode === 'sitemap'
                ? 'bg-[#00d4aa]/10 text-[#00d4aa] border border-[#00d4aa]/20'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
            }`}
          >
            <LinkIcon className="w-4 h-4" />
            Sitemap
          </button>
        </div>

        {scanMode === 'sitemap' ? (
          <div className="mb-6">
            <label className="block text-sm text-zinc-400 mb-2">Sitemap XML 地址</label>
            <input
              type="url"
              value={sitemapUrl}
              onChange={(e) => setSitemapUrl(e.target.value)}
              placeholder="https://example.com/sitemap.xml"
              className="w-full px-4 py-3 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-200 placeholder-zinc-500 focus:border-[#00d4aa] focus:outline-none transition-colors"
            />
          </div>
        ) : (
          <div className="space-y-3 mb-6">
            <label className="block text-sm text-zinc-400">页面 URL 列表</label>
            {urls.map((url, index) => (
              <div key={index} className="flex gap-2">
                <input
                  type="url"
                  value={url}
                  onChange={(e) => updateUrl(index, e.target.value)}
                  placeholder="https://example.com/page"
                  className="flex-1 px-4 py-2.5 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-200 placeholder-zinc-500 focus:border-[#00d4aa] focus:outline-none transition-colors text-sm"
                />
                {urls.length > 1 && (
                  <button
                    onClick={() => removeUrl(index)}
                    className="px-3 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-400 hover:text-red-400 hover:border-red-500/30 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
            <button
              onClick={addUrl}
              className="w-full py-2.5 rounded-lg border border-dashed border-zinc-700 text-zinc-500 hover:border-[#00d4aa] hover:text-[#00d4aa] transition-colors text-sm flex items-center justify-center gap-2"
            >
              <Plus className="w-4 h-4" />
              添加 URL
            </button>
          </div>
        )}

        <button
          onClick={startScan}
          disabled={scanning}
          className="w-full py-3 rounded-lg bg-[#00d4aa] text-zinc-900 font-medium hover:bg-[#00d4aa]/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
        >
          {scanning ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              扫描中... ({currentIndex}/{urls.filter((u) => u.trim()).length})
            </>
          ) : (
            <>
              <Play className="w-5 h-5" />
              开始扫描
            </>
          )}
        </button>
      </div>

      {results.length > 0 && (
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 overflow-hidden">
          <div className="p-4 border-b border-zinc-800">
            <h4 className="text-sm font-medium text-zinc-300">扫描结果</h4>
          </div>
          <div className="divide-y divide-zinc-800">
            {results.map((result, index) => (
              <div key={index} className="p-4 flex items-center gap-4">
                <div className="w-8 h-8 flex items-center justify-center shrink-0">
                  {getStatusIcon(result, index)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-zinc-200 truncate">
                    {result?.title || urls[index] || '未命名页面'}
                  </p>
                  <p className="text-xs text-zinc-500 truncate font-mono">
                    {result?.url || urls[index]}
                  </p>
                </div>
                {result?.report && (
                  <div className="text-right shrink-0">
                    <p className={`text-lg font-bold font-mono ${getPassRateColor(result.report.passRate)}`}>
                      {result.report.passRate}%
                    </p>
                    <p className="text-xs text-zinc-500">
                      {result.report.failed} 个问题
                    </p>
                  </div>
                )}
                {result?.report && (
                  <div className="w-16 h-2 rounded-full bg-zinc-800 overflow-hidden shrink-0">
                    <div
                      className={`h-full ${
                        result.report.passRate >= 80
                          ? 'bg-[#00d4aa]'
                          : result.report.passRate >= 50
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                      }`}
                      style={{ width: `${result.report.passRate}%` }}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {session && (
        <div className="bg-gradient-to-r from-[#00d4aa]/10 to-transparent rounded-xl border border-[#00d4aa]/20 p-6">
          <h4 className="text-lg font-bold text-zinc-100 mb-4">扫描完成</h4>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-3xl font-bold text-[#00d4aa] font-mono">{session.overallPassRate}%</p>
              <p className="text-xs text-zinc-500 mt-1">平均合规率</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-zinc-200 font-mono">{session.results.length}</p>
              <p className="text-xs text-zinc-500 mt-1">扫描页面</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-[#ff6b35] font-mono">{session.totalIssues}</p>
              <p className="text-xs text-zinc-500 mt-1">问题总数</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
