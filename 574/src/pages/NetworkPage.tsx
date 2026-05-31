import { useState, useEffect, useRef } from 'react';
import { Network, Info, ArrowRight, Loader2, Layers, RefreshCw } from 'lucide-react';
import { CitationGraph } from '@/components/CitationGraph/CitationGraph';
import { useAppStore } from '@/store';
import { api } from '@/services/api';

export function NetworkPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const { graphData, selectedPapers, setGraphData, loading, setLoading, setCurrentPage } = useAppStore();
  const [depth, setDepth] = useState(2);
  const [useHierarchical, setUseHierarchical] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: Math.max(600, window.innerHeight - 200),
        });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  const handleBuildDemoNetwork = async () => {
    if (selectedPapers.length === 0) {
      setError('请先在搜索页面选择论文');
      setCurrentPage('search');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = useHierarchical 
        ? await api.getHierarchicalGraph(true)
        : await api.buildGraph({
            dois: selectedPapers.map((p) => p.doi),
            depth: depth,
            max_nodes: 200,
          });

      if (response.success && response.data) {
        setGraphData(response.data);
      } else {
        setError(response.error || '构建网络失败');
      }
    } catch (e) {
      setError('构建网络失败，请检查后端服务是否运行');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-grid">
      <div className="max-w-[1600px] mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-display font-bold text-white mb-2">
              引用网络可视化
            </h1>
            <p className="text-dark-400">
              交互式探索论文之间的引用关系，发现研究脉络
            </p>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-accent-blue" />
              <span className="text-sm text-dark-400">分层可视化:</span>
              <button
                onClick={() => setUseHierarchical(!useHierarchical)}
                className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                  useHierarchical
                    ? 'bg-accent-blue/20 text-accent-blue border border-accent-blue/30'
                    : 'bg-dark-700 text-dark-300 border border-dark-600'
                }`}
              >
                {useHierarchical ? '已开启' : '已关闭'}
              </button>
            </div>

            {selectedPapers.length > 0 && (
              <>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-dark-400">遍历深度:</span>
                  <select
                    value={depth}
                    onChange={(e) => setDepth(Number(e.target.value))}
                    className="px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white text-sm focus:outline-none focus:border-accent-blue/50"
                  >
                    <option value={1}>1 层</option>
                    <option value={2}>2 层</option>
                    <option value={3}>3 层</option>
                  </select>
                </div>
                <button
                  onClick={handleBuildDemoNetwork}
                  disabled={loading}
                  className="px-5 py-2 bg-gradient-to-r from-accent-blue to-accent-green text-white font-medium rounded-xl hover:shadow-lg hover:shadow-accent-blue/30 transition-all disabled:opacity-50 flex items-center gap-2"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <RefreshCw className="w-4 h-4" />
                  )}
                  重建网络
                </button>
              </>
            )}
          </div>
        </div>

        {error && (
          <div className="bg-accent-rose/10 border border-accent-rose/30 rounded-xl p-4 mb-6 text-accent-rose flex items-center gap-3">
            <Info className="w-5 h-5" />
            <span>{error}</span>
            <button
              onClick={() => setCurrentPage('search')}
              className="ml-auto px-4 py-1 bg-dark-700 rounded-lg text-sm hover:bg-dark-600 transition-colors"
            >
              去搜索
            </button>
          </div>
        )}

        {graphData ? (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            <div className="lg:col-span-3" ref={containerRef}>
              <div className="glass rounded-2xl overflow-hidden">
                <CitationGraph
                  graphData={graphData}
                  height={dimensions.height}
                />
              </div>
            </div>

            <div className="space-y-6">
              <div className="glass rounded-2xl p-5">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Network className="w-5 h-5 text-accent-blue" />
                  网络统计
                </h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-dark-400">节点数量</span>
                    <span className="text-white font-semibold">
                      {graphData.stats.total_nodes.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-dark-400">边数量</span>
                    <span className="text-white font-semibold">
                      {graphData.stats.total_edges.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-dark-400">平均度数</span>
                    <span className="text-white font-semibold">
                      {graphData.stats.avg_degree.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-dark-400">网络密度</span>
                    <span className="text-white font-semibold">
                      {graphData.stats.density.toFixed(4)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-dark-400">社区数量</span>
                    <span className="text-accent-green font-semibold">
                      {graphData.stats.communities}
                    </span>
                  </div>
                </div>
              </div>

              <div className="glass rounded-2xl p-5">
                <h3 className="text-lg font-semibold text-white mb-4">操作指南</h3>
                <div className="space-y-3 text-sm text-dark-400">
                  <div className="flex items-start gap-2">
                    <div className="w-6 h-6 rounded bg-accent-blue/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-accent-blue text-xs">1</span>
                    </div>
                    <p>鼠标悬停查看节点详情，高亮相邻节点</p>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="w-6 h-6 rounded bg-accent-green/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-accent-green text-xs">2</span>
                    </div>
                    <p>拖拽节点可重新定位，滚轮缩放视图</p>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="w-6 h-6 rounded bg-accent-amber/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-accent-amber text-xs">3</span>
                    </div>
                    <p>点击节点选中，查看详细信息</p>
                  </div>
                </div>
              </div>

              <button
                onClick={() => setCurrentPage('influence')}
                className="w-full p-4 glass rounded-2xl hover:border-accent-blue/30 transition-all group text-left"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-white font-medium">查看影响力分析</p>
                    <p className="text-sm text-dark-400">PageRank、H指数排名</p>
                  </div>
                  <ArrowRight className="w-5 h-5 text-dark-400 group-hover:text-accent-blue group-hover:translate-x-1 transition-all" />
                </div>
              </button>
            </div>
          </div>
        ) : (
          <div className="glass rounded-2xl p-16 text-center">
            {loading ? (
              <div className="flex flex-col items-center gap-4">
                <Loader2 className="w-12 h-12 text-accent-blue animate-spin" />
                <p className="text-dark-400">正在构建引用网络...</p>
              </div>
            ) : (
              <div>
                <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-dark-700/50 flex items-center justify-center">
                  <Network className="w-10 h-10 text-dark-500" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">暂无网络数据</h3>
                <p className="text-dark-400 mb-6">
                  请先在搜索页面搜索并选择论文，然后构建引用网络
                </p>
                <button
                  onClick={() => setCurrentPage('search')}
                  className="px-6 py-3 bg-gradient-to-r from-accent-blue to-accent-green text-white font-medium rounded-xl hover:shadow-lg hover:shadow-accent-blue/30 transition-all"
                >
                  去搜索论文
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
