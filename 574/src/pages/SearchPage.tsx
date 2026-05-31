import { useState } from 'react';
import { Search, Database, Sparkles, Loader2 } from 'lucide-react';
import { api } from '@/services/api';
import { useAppStore } from '@/store';
import { PaperCard } from '@/components/PaperCard/PaperCard';
import type { SourceType, Paper } from '@/types';

export function SearchPage() {
  const {
    searchQuery,
    setSearchQuery,
    selectedSource,
    setSelectedSource,
    searchResults,
    setSearchResults,
    selectedPapers,
    loading,
    setLoading,
    setCurrentPage,
    setGraphData,
  } = useAppStore();

  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await api.searchPapers(searchQuery.trim(), selectedSource, 30);
      if (response.success && response.data) {
        setSearchResults(response.data);
      } else {
        setError(response.error || '搜索失败，请稍后重试');
      }
    } catch (e) {
      setError('网络错误，请检查连接或稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleBuildNetwork = async () => {
    if (selectedPapers.length === 0) return;

    setLoading(true);
    setError(null);

    try {
      const response = await api.buildGraph({
        dois: selectedPapers.map((p) => p.doi),
        depth: 2,
        max_nodes: 200,
      });

      if (response.success && response.data) {
        setGraphData(response.data);
        setCurrentPage('network');
      } else {
        setError(response.error || '构建网络失败');
      }
    } catch (e) {
      setError('构建网络失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleViewInfluence = async (paper: Paper) => {
    setLoading(true);
    try {
      const response = await api.buildGraph({
        dois: [paper.doi],
        depth: 2,
        max_nodes: 100,
      });

      if (response.success && response.data) {
        setGraphData(response.data);
        setCurrentPage('influence');
      }
    } catch (e) {
      setError('分析失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-grid">
      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="text-center mb-12 animate-fade-in">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-accent-blue/10 border border-accent-blue/20 rounded-full text-accent-blue text-sm mb-6">
            <Sparkles className="w-4 h-4" />
            <span>学术论文引用网络分析平台</span>
          </div>

          <h1 className="font-display text-5xl font-bold text-white mb-4">
            探索 <span className="text-gradient">学术引用</span> 的奥秘
          </h1>
          <p className="text-dark-400 text-lg max-w-2xl mx-auto">
            从 Crossref 和 DBLP 获取学术论文数据，构建引用关系网络，
            计算 PageRank、H 指数等影响力指标，发现领域核心论文
          </p>
        </div>

        <div className="glass rounded-2xl p-6 mb-8 animate-slide-up delay-100">
          <div className="flex items-center gap-4 mb-4">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-dark-400" />
              <span className="text-sm text-dark-400">数据源:</span>
            </div>
            <div className="flex gap-2">
              {(['crossref', 'dblp'] as SourceType[]).map((source) => (
                <button
                  key={source}
                  onClick={() => setSelectedSource(source)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    selectedSource === source
                      ? 'bg-accent-blue text-white shadow-lg shadow-accent-blue/30'
                      : 'bg-dark-700/50 text-dark-400 hover:text-white hover:bg-dark-600/50'
                  }`}
                >
                  {source === 'crossref' ? 'Crossref' : 'DBLP'}
                </button>
              ))}
            </div>
          </div>

          <div className="flex gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="搜索论文标题、作者、关键词或 DOI..."
                className="w-full pl-12 pr-4 py-4 bg-dark-800/50 border border-dark-600 rounded-xl text-white placeholder-dark-500 focus:outline-none focus:border-accent-blue/50 focus:ring-2 focus:ring-accent-blue/20 transition-all"
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={loading || !searchQuery.trim()}
              className="px-8 py-4 bg-gradient-to-r from-accent-blue to-accent-green text-white font-medium rounded-xl hover:shadow-lg hover:shadow-accent-blue/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Search className="w-5 h-5" />
              )}
              搜索
            </button>
          </div>
        </div>

        {selectedPapers.length > 0 && (
          <div className="glass rounded-2xl p-5 mb-8 animate-slide-up delay-200 flex items-center justify-between">
            <div>
              <p className="text-dark-300">
                已选择 <span className="text-accent-blue font-semibold">{selectedPapers.length}</span> 篇论文用于构建网络
              </p>
              <p className="text-xs text-dark-500 mt-1">
                {selectedPapers.map((p) => p.title).join('; ').substring(0, 100)}...
              </p>
            </div>
            <button
              onClick={handleBuildNetwork}
              disabled={loading}
              className="px-6 py-3 bg-gradient-to-r from-accent-amber to-accent-rose text-white font-medium rounded-xl hover:shadow-lg hover:shadow-accent-amber/30 transition-all disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : null}
              构建引用网络
            </button>
          </div>
        )}

        {error && (
          <div className="bg-accent-rose/10 border border-accent-rose/30 rounded-xl p-4 mb-8 text-accent-rose">
            {error}
          </div>
        )}

        {searchResults.length > 0 && (
          <div className="space-y-4 animate-slide-up delay-300">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-white">
                搜索结果 ({searchResults.length})
              </h2>
            </div>

            <div className="space-y-4">
              {searchResults.map((paper, index) => (
                <div key={paper.doi} style={{ animationDelay: `${index * 50}ms` }}>
                  <PaperCard paper={paper} onSelect={handleViewInfluence} />
                </div>
              ))}
            </div>
          </div>
        )}

        {searchResults.length === 0 && !loading && !error && (
          <div className="text-center py-16 animate-fade-in">
            <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-dark-700/50 flex items-center justify-center">
              <Search className="w-10 h-10 text-dark-500" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">开始搜索</h3>
            <p className="text-dark-400">
              输入关键词、作者或论文标题，开始探索学术引用网络
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
