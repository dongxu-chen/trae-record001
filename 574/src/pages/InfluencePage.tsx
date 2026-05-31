import { useState, useEffect, useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
} from 'recharts';
import {
  Award,
  TrendingUp,
  BookOpen,
  Star,
  Search,
  Loader2,
  BarChart3,
  Radar as RadarIcon,
  Crown,
  ArrowUpRight,
  Filter,
  ChevronRight,
  ChevronDown,
  Layers,
  Users,
  FileText,
} from 'lucide-react';
import { api } from '@/services/api';
import { useAppStore } from '@/store';
import type { InfluenceMetrics, RankingMetric, MultiGranularClusters, HierarchicalCommunity } from '@/types';

const COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6',
  '#f43f5e', '#06b6d4', '#84cc16', '#f97316',
  '#6366f1', '#ec4899', '#14b8a6', '#a855f7'
];

export function InfluencePage() {
  const { setCurrentPage } = useAppStore();
  const [activeMetric, setActiveMetric] = useState<RankingMetric>('pagerank');
  const [rankings, setRankings] = useState<InfluenceMetrics[]>([]);
  const [corePapers, setCorePapers] = useState<InfluenceMetrics[]>([]);
  const [clusters, setClusters] = useState<MultiGranularClusters | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'list' | 'chart' | 'clusters'>('list');
  const [expandedClusters, setExpandedClusters] = useState<Set<string>>(new Set());
  const [clusterLevel, setClusterLevel] = useState(0);
  const [loadingClusters, setLoadingClusters] = useState<Set<string>>(new Set());
  const [clusterPapersCache, setClusterPapersCache] = useState<Record<string, InfluenceMetrics[]>>({});

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [rankingRes, coreRes, clustersRes] = await Promise.all([
          api.getInfluenceRanking(activeMetric, 50),
          api.getCorePapers(),
          api.getClusters(3),
        ]);

        if (rankingRes.success && rankingRes.data) {
          setRankings(rankingRes.data);
        }
        if (coreRes.success && coreRes.data) {
          setCorePapers(coreRes.data);
        }
        if (clustersRes.success && clustersRes.data) {
          setClusters(clustersRes.data);
        }
      } catch (error) {
        console.error('Failed to load influence data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [activeMetric]);

  const filteredRankings = useMemo(() => {
    if (!searchQuery.trim()) return rankings;
    const query = searchQuery.toLowerCase();
    return rankings.filter((p) =>
      p.title.toLowerCase().includes(query) || p.doi.toLowerCase().includes(query)
    );
  }, [rankings, searchQuery]);

  const chartData = useMemo(() => {
    return rankings.slice(0, 15).map((paper) => ({
      name: paper.title.substring(0, 20) + '...',
      pagerank: parseFloat((paper.pagerank * 1000).toFixed(2)),
      h_index: paper.h_index,
      citations: paper.citations / 100,
    }));
  }, [rankings]);

  const radarData = useMemo(() => {
    if (rankings.length === 0) return [];
    const topPaper = rankings[0];
    const avgPaper = rankings[Math.floor(rankings.length / 2)];
    
    return [
      {
        metric: 'PageRank',
        top: parseFloat((topPaper.pagerank * 100).toFixed(2)),
        average: parseFloat((avgPaper.pagerank * 100).toFixed(2)),
        fullMark: 5,
      },
      {
        metric: 'H指数',
        top: topPaper.h_index,
        average: avgPaper.h_index,
        fullMark: 150,
      },
      {
        metric: '引用量',
        top: topPaper.citations / 50,
        average: avgPaper.citations / 50,
        fullMark: 100,
      },
      {
        metric: '中介中心性',
        top: (topPaper.betweenness_centrality || 0) * 100,
        average: (avgPaper.betweenness_centrality || 0) * 100,
        fullMark: 50,
      },
      {
        metric: '接近中心性',
        top: (topPaper.closeness_centrality || 0) * 100,
        average: (avgPaper.closeness_centrality || 0) * 100,
        fullMark: 100,
      },
    ];
  }, [rankings]);

  const toggleClusterExpand = async (level: number, clusterId: number) => {
    const key = `${level}-${clusterId}`;
    
    if (expandedClusters.has(key)) {
      setExpandedClusters((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
      return;
    }

    setExpandedClusters((prev) => new Set(prev).add(key));

    if (!clusterPapersCache[key]) {
      setLoadingClusters((prev) => new Set(prev).add(key));
      try {
        const response = await api.getClusterPapers(level, clusterId, 20);
        if (response.success && response.data) {
          setClusterPapersCache((prev) => ({
            ...prev,
            [key]: response.data,
          }));
        }
      } catch (error) {
        console.error('Failed to load cluster papers:', error);
      } finally {
        setLoadingClusters((prev) => {
          const next = new Set(prev);
          next.delete(key);
          return next;
        });
      }
    }
  };

  const metricConfig = {
    pagerank: { label: 'PageRank', icon: TrendingUp, color: 'from-accent-blue to-accent-cyan' },
    h_index: { label: 'H指数', icon: Award, color: 'from-accent-amber to-accent-rose' },
    citations: { label: '引用量', icon: BookOpen, color: 'from-accent-green to-accent-emerald' },
  };

  const getMetricValue = (paper: InfluenceMetrics, metric: RankingMetric): number => {
    switch (metric) {
      case 'pagerank':
        return paper.pagerank;
      case 'h_index':
        return paper.h_index;
      case 'citations':
        return paper.citations;
    }
  };

  const getMetricRank = (paper: InfluenceMetrics, metric: RankingMetric): number => {
    switch (metric) {
      case 'pagerank':
        return paper.pagerank_rank;
      case 'h_index':
        return paper.h_index_rank;
      case 'citations':
        return paper.citations_rank;
    }
  };

  const formatValue = (value: number, metric: RankingMetric): string => {
    switch (metric) {
      case 'pagerank':
        return value.toFixed(6);
      case 'h_index':
        return value.toString();
      case 'citations':
        return value.toLocaleString();
    }
  };

  const currentCommunities = useMemo(() => {
    if (!clusters) return [];
    return Object.entries(clusters.communities[clusterLevel] || {}).map(([id, comm]) => ({
      ...comm,
      id: Number(id),
    }));
  }, [clusters, clusterLevel]);

  return (
    <div className="min-h-screen bg-grid">
      <div className="max-w-[1600px] mx-auto px-6 py-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-display font-bold text-white mb-2">
              影响力分析
            </h1>
            <p className="text-dark-400">
              基于 PageRank、H 指数等多维度指标评估论文影响力
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex bg-dark-800/50 rounded-lg p-1">
              {(['list', 'chart', 'clusters'] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setViewMode(mode)}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-all flex items-center gap-2 ${
                    viewMode === mode
                      ? 'bg-accent-blue text-white shadow-lg shadow-accent-blue/30'
                      : 'text-dark-400 hover:text-white'
                  }`}
                >
                  {mode === 'list' ? <Filter className="w-4 h-4" /> : 
                   mode === 'chart' ? <BarChart3 className="w-4 h-4" /> :
                   <Layers className="w-4 h-4" />}
                  {mode === 'list' ? '列表' : mode === 'chart' ? '图表' : '聚类'}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {(['pagerank', 'h_index', 'citations'] as RankingMetric[]).map((metric) => {
            const config = metricConfig[metric];
            const Icon = config.icon;
            const topValue = rankings.length > 0 ? getMetricValue(rankings[0], metric) : 0;
            const isActive = activeMetric === metric;

            return (
              <button
                key={metric}
                onClick={() => setActiveMetric(metric)}
                className={`glass rounded-2xl p-6 text-left transition-all group ${
                  isActive
                    ? 'border-accent-blue/50 shadow-lg shadow-accent-blue/10'
                    : 'hover:border-dark-500'
                }`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div
                    className={`w-12 h-12 rounded-xl bg-gradient-to-br ${config.color} flex items-center justify-center shadow-lg`}
                  >
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  {isActive && (
                    <div className="w-3 h-3 rounded-full bg-accent-blue animate-pulse" />
                  )}
                </div>
                <h3 className="text-lg font-semibold text-white mb-1">{config.label}</h3>
                <p className="text-3xl font-bold text-gradient mb-1">
                  {formatValue(topValue, metric)}
                </p>
                <p className="text-sm text-dark-400">
                  当前排名第 {isActive ? '1' : getMetricRank(rankings[0] || ({} as any), metric)} 位
                </p>
              </button>
            );
          })}
        </div>

        {corePapers.length > 0 && (
          <div className="glass rounded-2xl p-6 mb-8">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-amber to-accent-rose flex items-center justify-center">
                <Crown className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-white">核心论文</h2>
                <p className="text-sm text-dark-400">基于多指标综合评估的领域核心论文</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {corePapers.slice(0, 6).map((paper, index) => (
                <div
                  key={paper.doi}
                  className="bg-dark-800/50 rounded-xl p-4 hover:bg-dark-700/50 transition-colors group"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-amber/20 to-accent-rose/20 flex items-center justify-center flex-shrink-0">
                      <span className="text-accent-amber font-bold text-sm">#{index + 1}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-white font-medium mb-1 line-clamp-2 group-hover:text-accent-blue transition-colors">
                        {paper.title}
                      </h4>
                      <div className="flex flex-wrap gap-2 text-xs">
                        <span className="px-2 py-0.5 rounded-full bg-accent-blue/10 text-accent-blue">
                          PR: {paper.pagerank.toFixed(5)}
                        </span>
                        <span className="px-2 py-0.5 rounded-full bg-accent-amber/10 text-accent-amber">
                          H: {paper.h_index}
                        </span>
                        <span className="px-2 py-0.5 rounded-full bg-accent-green/10 text-accent-green">
                          C: {paper.citations.toLocaleString()}
                        </span>
                      </div>
                      {paper.core_reason && (
                        <p className="text-xs text-dark-400 mt-2 flex items-center gap-1">
                          <Star className="w-3 h-3 text-accent-amber" />
                          {paper.core_reason}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {viewMode === 'chart' && rankings.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div className="glass rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-6">
                <BarChart3 className="w-5 h-5 text-accent-blue" />
                <h3 className="text-lg font-semibold text-white">Top 15 论文对比</h3>
              </div>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
                  <XAxis
                    dataKey="name"
                    stroke="#718096"
                    tick={{ fill: '#a0aec0', fontSize: 11 }}
                    angle={-45}
                    textAnchor="end"
                    height={80}
                  />
                  <YAxis stroke="#718096" tick={{ fill: '#a0aec0' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1a202c',
                      border: '1px solid #2d3748',
                      borderRadius: '8px',
                      color: 'white',
                    }}
                  />
                  <Legend />
                  <Bar dataKey="pagerank" name="PageRank (×1000)" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="h_index" name="H指数" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="citations" name="引用量 (÷100)" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="glass rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-6">
                <RadarIcon className="w-5 h-5 text-accent-amber" />
                <h3 className="text-lg font-semibold text-white">Top vs 平均 雷达图</h3>
              </div>
              <ResponsiveContainer width="100%" height={400}>
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                  <PolarGrid stroke="#2d3748" />
                  <PolarAngleAxis dataKey="metric" tick={{ fill: '#a0aec0', fontSize: 12 }} />
                  <PolarRadiusAxis stroke="#4a5568" tick={{ fill: '#718096' }} />
                  <Radar
                    name="Top论文"
                    dataKey="top"
                    stroke="#3b82f6"
                    fill="#3b82f6"
                    fillOpacity={0.5}
                  />
                  <Radar
                    name="平均水平"
                    dataKey="average"
                    stroke="#f59e0b"
                    fill="#f59e0b"
                    fillOpacity={0.3}
                  />
                  <Legend />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1a202c',
                      border: '1px solid #2d3748',
                      borderRadius: '8px',
                      color: 'white',
                    }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {viewMode === 'clusters' && clusters && (
          <div className="glass rounded-2xl p-6 mb-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
              <div className="flex items-center gap-3">
                <Layers className="w-6 h-6 text-accent-purple" />
                <div>
                  <h2 className="text-xl font-semibold text-white">多粒度聚类分析</h2>
                  <p className="text-sm text-dark-400">展开聚类查看子主题和核心论文</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-sm text-dark-400">聚类粒度:</span>
                {clusters.levels.map((level) => (
                  <button
                    key={level}
                    onClick={() => setClusterLevel(level)}
                    className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                      clusterLevel === level
                        ? 'bg-accent-purple/20 text-accent-purple border border-accent-purple/30'
                        : 'bg-dark-700 text-dark-300 hover:bg-dark-600'
                    }`}
                  >
                    层级 {level}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {currentCommunities.map((community) => {
                const key = `${clusterLevel}-${community.id}`;
                const isExpanded = expandedClusters.has(key);
                const isLoading = loadingClusters.has(key);
                const papers = clusterPapersCache[key] || [];
                const color = COLORS[community.id % COLORS.length];

                return (
                  <div
                    key={key}
                    className="bg-dark-800/50 rounded-xl overflow-hidden transition-all"
                    style={{ borderLeft: `4px solid ${color}` }}
                  >
                    <button
                      onClick={() => toggleClusterExpand(clusterLevel, community.id)}
                      className="w-full p-4 text-left hover:bg-dark-700/30 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2">
                            {isExpanded ? (
                              <ChevronDown className="w-5 h-5 text-dark-400 flex-shrink-0" />
                            ) : (
                              <ChevronRight className="w-5 h-5 text-dark-400 flex-shrink-0" />
                            )}
                            <h4 className="text-white font-medium" style={{ color }}>
                              {community.name || `聚类 ${community.id}`}
                            </h4>
                          </div>
                          
                          <div className="flex items-center gap-4 text-sm text-dark-400 mb-2">
                            <span className="flex items-center gap-1">
                              <Users className="w-4 h-4" />
                              {community.size} 篇论文
                            </span>
                            {community.children.length > 0 && (
                              <span className="flex items-center gap-1">
                                <Layers className="w-4 h-4" />
                                {community.children.length} 个子聚类
                              </span>
                            )}
                          </div>

                          {community.keywords.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {community.keywords.slice(0, 3).map((kw) => (
                                <span
                                  key={kw}
                                  className="px-2 py-0.5 rounded-full text-xs bg-dark-700 text-dark-300"
                                >
                                  {kw}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>

                        <div
                          className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                          style={{ backgroundColor: `${color}20` }}
                        >
                          <FileText className="w-6 h-6" style={{ color }} />
                        </div>
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="border-t border-dark-700">
                        {isLoading ? (
                          <div className="p-6 flex items-center justify-center">
                            <Loader2 className="w-5 h-5 text-accent-blue animate-spin" />
                          </div>
                        ) : papers.length > 0 ? (
                          <div className="divide-y divide-dark-700/50">
                            {papers.slice(0, 5).map((paper, idx) => (
                              <div
                                key={paper.doi}
                                className="p-3 hover:bg-dark-700/20 transition-colors"
                              >
                                <p className="text-white text-sm mb-1 line-clamp-1">
                                  {paper.title}
                                </p>
                                <div className="flex items-center gap-3 text-xs">
                                  <span className="text-accent-blue">#{idx + 1}</span>
                                  <span className="text-dark-400">
                                    PR: {paper.pagerank.toFixed(6)}
                                  </span>
                                  <span className="text-dark-400">
                                    引用: {paper.citations.toLocaleString()}
                                  </span>
                                </div>
                              </div>
                            ))}
                            {papers.length > 5 && (
                              <div className="p-3 text-center">
                                <span className="text-sm text-dark-400">
                                  还有 {papers.length - 5} 篇论文...
                                </span>
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="p-6 text-center text-dark-400 text-sm">
                            暂无论文数据
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {viewMode === 'list' && (
          <div className="glass rounded-2xl p-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
              <div className="flex items-center gap-3">
                <Award className="w-6 h-6 text-accent-blue" />
                <h2 className="text-xl font-semibold text-white">
                  {metricConfig[activeMetric].label} 排名
                </h2>
              </div>

              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="搜索论文标题或 DOI..."
                  className="pl-10 pr-4 py-2 bg-dark-800/50 border border-dark-600 rounded-lg text-white placeholder-dark-500 focus:outline-none focus:border-accent-blue/50 w-full md:w-80"
                />
              </div>
            </div>

            {loading ? (
              <div className="flex flex-col items-center justify-center py-16">
                <Loader2 className="w-10 h-10 text-accent-blue animate-spin mb-4" />
                <p className="text-dark-400">正在加载影响力数据...</p>
              </div>
            ) : filteredRankings.length === 0 ? (
              <div className="text-center py-16">
                <Search className="w-12 h-12 text-dark-500 mx-auto mb-4" />
                <p className="text-dark-400">未找到匹配的论文</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-dark-600">
                      <th className="text-left py-3 px-4 text-dark-400 font-medium text-sm">排名</th>
                      <th className="text-left py-3 px-4 text-dark-400 font-medium text-sm">论文标题</th>
                      <th className="text-right py-3 px-4 text-dark-400 font-medium text-sm">PageRank</th>
                      <th className="text-right py-3 px-4 text-dark-400 font-medium text-sm">H指数</th>
                      <th className="text-right py-3 px-4 text-dark-400 font-medium text-sm">引用量</th>
                      <th className="text-right py-3 px-4 text-dark-400 font-medium text-sm">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRankings.slice(0, 30).map((paper, index) => (
                      <tr
                        key={paper.doi}
                        className="border-b border-dark-700/50 hover:bg-dark-700/30 transition-colors group"
                      >
                        <td className="py-4 px-4">
                          <div className="flex items-center gap-2">
                            <span
                              className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm ${
                                index === 0
                                  ? 'bg-gradient-to-br from-amber-400 to-amber-600 text-white'
                                  : index === 1
                                  ? 'bg-gradient-to-br from-gray-300 to-gray-500 text-white'
                                  : index === 2
                                  ? 'bg-gradient-to-br from-amber-600 to-amber-800 text-white'
                                  : 'bg-dark-700 text-dark-300'
                              }`}
                            >
                              {index + 1}
                            </span>
                            {paper.is_core && <Crown className="w-4 h-4 text-accent-amber" />}
                          </div>
                        </td>
                        <td className="py-4 px-4">
                          <div>
                            <p className="text-white font-medium mb-1 group-hover:text-accent-blue transition-colors">
                              {paper.title}
                            </p>
                            <p className="text-xs text-dark-500 font-mono">{paper.doi}</p>
                          </div>
                        </td>
                        <td className="py-4 px-4 text-right">
                          <span className="text-accent-blue font-mono">
                            {paper.pagerank.toFixed(6)}
                          </span>
                        </td>
                        <td className="py-4 px-4 text-right">
                          <span className="text-accent-amber font-semibold">{paper.h_index}</span>
                        </td>
                        <td className="py-4 px-4 text-right">
                          <span className="text-accent-green font-semibold">
                            {paper.citations.toLocaleString()}
                          </span>
                        </td>
                        <td className="py-4 px-4 text-right">
                          <button
                            onClick={() => setCurrentPage('network')}
                            className="text-accent-blue hover:text-accent-cyan transition-colors flex items-center gap-1 ml-auto"
                          >
                            <span className="text-sm">查看网络</span>
                            <ArrowUpRight className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
