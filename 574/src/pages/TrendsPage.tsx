import { useState, useEffect, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  Legend,
  ComposedChart,
  Bar,
} from 'recharts';
import ReactWordcloud from 'react-wordcloud';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Calendar,
  Loader2,
  LineChart as LineChartIcon,
  Cloud,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  Hash,
} from 'lucide-react';
import { api } from '@/services/api';
import type { TrendData, KeywordTrend } from '@/types';

export function TrendsPage() {
  const [trendData, setTrendData] = useState<TrendData[]>([]);
  const [keywordTrends, setKeywordTrends] = useState<KeywordTrend[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'keywords'>('overview');

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [trendRes, keywordRes] = await Promise.all([
          api.getTrendsOverTime(undefined, 2010, 2024),
          api.getKeywordTrends(30),
        ]);

        if (trendRes.success && trendRes.data) {
          setTrendData(trendRes.data);
        }
        if (keywordRes.success && keywordRes.data) {
          setKeywordTrends(keywordRes.data);
        }
      } catch (error) {
        console.error('Failed to load trend data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const wordCloudData = useMemo(() => {
    return keywordTrends.map((kw) => ({
      text: kw.keyword,
      value: kw.count,
    }));
  }, [keywordTrends]);

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'rising':
        return <ArrowUpRight className="w-4 h-4 text-accent-green" />;
      case 'declining':
        return <ArrowDownRight className="w-4 h-4 text-accent-rose" />;
      default:
        return <Minus className="w-4 h-4 text-accent-amber" />;
    }
  };

  const getTrendBadgeClass = (trend: string) => {
    switch (trend) {
      case 'rising':
        return 'bg-accent-green/10 text-accent-green border-accent-green/30';
      case 'declining':
        return 'bg-accent-rose/10 text-accent-rose border-accent-rose/30';
      default:
        return 'bg-accent-amber/10 text-accent-amber border-accent-amber/30';
    }
  };

  const getTrendLabel = (trend: string) => {
    switch (trend) {
      case 'rising':
        return '上升';
      case 'declining':
        return '下降';
      default:
        return '稳定';
    }
  };

  const stats = useMemo(() => {
    if (trendData.length === 0) return null;
    
    const latest = trendData[trendData.length - 1];
    const previous = trendData[trendData.length - 2];
    
    const paperGrowth = previous 
      ? ((latest.paper_count - previous.paper_count) / previous.paper_count * 100).toFixed(1)
      : '0';
    const citationGrowth = previous
      ? ((latest.citation_count - previous.citation_count) / previous.citation_count * 100).toFixed(1)
      : '0';

    return {
      totalPapers: trendData.reduce((sum, d) => sum + d.paper_count, 0),
      totalCitations: trendData.reduce((sum, d) => sum + d.citation_count, 0),
      latestYear: latest.year,
      paperGrowth,
      citationGrowth,
      avgCitations: latest.avg_citations,
    };
  }, [trendData]);

  const callbacks = {
    getWordTooltip: (word: { text: string; value: number }) => {
      const trend = keywordTrends.find((k) => k.keyword === word.text);
      return (
        <div className="bg-dark-800 border border-dark-600 rounded-lg p-3 shadow-xl">
          <p className="text-white font-medium">{word.text}</p>
          <p className="text-dark-400 text-sm">出现次数: {word.value}</p>
          {trend && (
            <p className={`text-sm ${trend.trend === 'rising' ? 'text-accent-green' : trend.trend === 'declining' ? 'text-accent-rose' : 'text-accent-amber'}`}>
              增长率: {trend.growth_rate > 0 ? '+' : ''}{trend.growth_rate}%
            </p>
          )}
        </div>
      );
    },
  };

  const options = {
    rotations: 2,
    rotationAngles: [0, 90],
    fontSizes: [16, 64],
    scale: 'sqrt' as const,
    spiral: 'archimedean' as const,
  };

  return (
    <div className="min-h-screen bg-grid">
      <div className="max-w-[1600px] mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-display font-bold text-white mb-2">
            研究趋势分析
          </h1>
          <p className="text-dark-400">
            分析领域研究热点和发展趋势，洞察学术前沿动态
          </p>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-24">
            <Loader2 className="w-12 h-12 text-accent-blue animate-spin mb-4" />
            <p className="text-dark-400">正在加载趋势数据...</p>
          </div>
        ) : (
          <>
            {stats && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <div className="glass rounded-2xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-blue to-accent-cyan flex items-center justify-center">
                      <Hash className="w-5 h-5 text-white" />
                    </div>
                    <span className={`text-sm font-medium flex items-center gap-1 ${parseFloat(stats.paperGrowth) >= 0 ? 'text-accent-green' : 'text-accent-rose'}`}>
                      {parseFloat(stats.paperGrowth) >= 0 ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
                      {Math.abs(parseFloat(stats.paperGrowth))}%
                    </span>
                  </div>
                  <p className="text-dark-400 text-sm mb-1">论文总数</p>
                  <p className="text-3xl font-bold text-gradient">{stats.totalPapers.toLocaleString()}</p>
                </div>

                <div className="glass rounded-2xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-green to-accent-emerald flex items-center justify-center">
                      <TrendingUp className="w-5 h-5 text-white" />
                    </div>
                    <span className={`text-sm font-medium flex items-center gap-1 ${parseFloat(stats.citationGrowth) >= 0 ? 'text-accent-green' : 'text-accent-rose'}`}>
                      {parseFloat(stats.citationGrowth) >= 0 ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
                      {Math.abs(parseFloat(stats.citationGrowth))}%
                    </span>
                  </div>
                  <p className="text-dark-400 text-sm mb-1">引用总数</p>
                  <p className="text-3xl font-bold text-gradient">{stats.totalCitations.toLocaleString()}</p>
                </div>

                <div className="glass rounded-2xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-amber to-accent-rose flex items-center justify-center">
                      <Calendar className="w-5 h-5 text-white" />
                    </div>
                  </div>
                  <p className="text-dark-400 text-sm mb-1">最新年份</p>
                  <p className="text-3xl font-bold text-gradient">{stats.latestYear}</p>
                </div>

                <div className="glass rounded-2xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-purple to-accent-blue flex items-center justify-center">
                      <BarChart3 className="w-5 h-5 text-white" />
                    </div>
                  </div>
                  <p className="text-dark-400 text-sm mb-1">平均引用量</p>
                  <p className="text-3xl font-bold text-gradient">{stats.avgCitations}</p>
                </div>
              </div>
            )}

            <div className="flex bg-dark-800/50 rounded-lg p-1 mb-6 w-fit">
              {(['overview', 'keywords'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-6 py-2 rounded-md text-sm font-medium transition-all flex items-center gap-2 ${
                    activeTab === tab
                      ? 'bg-accent-blue text-white shadow-lg shadow-accent-blue/30'
                      : 'text-dark-400 hover:text-white'
                  }`}
                >
                  {tab === 'overview' ? <LineChartIcon className="w-4 h-4" /> : <Cloud className="w-4 h-4" />}
                  {tab === 'overview' ? '总体趋势' : '关键词分析'}
                </button>
              ))}
            </div>

            {activeTab === 'overview' && (
              <div className="space-y-6">
                <div className="glass rounded-2xl p-6">
                  <div className="flex items-center gap-3 mb-6">
                    <LineChartIcon className="w-5 h-5 text-accent-blue" />
                    <h3 className="text-lg font-semibold text-white">论文数量与引用量趋势</h3>
                  </div>
                  <ResponsiveContainer width="100%" height={400}>
                    <ComposedChart data={trendData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
                      <XAxis
                        dataKey="year"
                        stroke="#718096"
                        tick={{ fill: '#a0aec0' }}
                      />
                      <YAxis
                        yAxisId="left"
                        stroke="#718096"
                        tick={{ fill: '#a0aec0' }}
                        label={{ value: '论文数量', angle: -90, position: 'insideLeft', fill: '#a0aec0' }}
                      />
                      <YAxis
                        yAxisId="right"
                        orientation="right"
                        stroke="#718096"
                        tick={{ fill: '#a0aec0' }}
                        label={{ value: '引用总量', angle: 90, position: 'insideRight', fill: '#a0aec0' }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1a202c',
                          border: '1px solid #2d3748',
                          borderRadius: '8px',
                          color: 'white',
                        }}
                      />
                      <Legend />
                      <Bar
                        yAxisId="left"
                        dataKey="paper_count"
                        name="论文数量"
                        fill="#3b82f6"
                        radius={[4, 4, 0, 0]}
                        opacity={0.8}
                      />
                      <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="citation_count"
                        name="引用总量"
                        stroke="#10b981"
                        strokeWidth={3}
                        dot={{ fill: '#10b981', r: 5 }}
                        activeDot={{ r: 8 }}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>

                <div className="glass rounded-2xl p-6">
                  <div className="flex items-center gap-3 mb-6">
                    <TrendingUp className="w-5 h-5 text-accent-green" />
                    <h3 className="text-lg font-semibold text-white">平均引用量变化趋势</h3>
                  </div>
                  <ResponsiveContainer width="100%" height={350}>
                    <AreaChart data={trendData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                      <defs>
                        <linearGradient id="colorAvgCitations" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8} />
                          <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
                      <XAxis
                        dataKey="year"
                        stroke="#718096"
                        tick={{ fill: '#a0aec0' }}
                      />
                      <YAxis
                        stroke="#718096"
                        tick={{ fill: '#a0aec0' }}
                        label={{ value: '平均引用量', angle: -90, position: 'insideLeft', fill: '#a0aec0' }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1a202c',
                          border: '1px solid #2d3748',
                          borderRadius: '8px',
                          color: 'white',
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="avg_citations"
                        name="平均引用量"
                        stroke="#8b5cf6"
                        strokeWidth={3}
                        fillOpacity={1}
                        fill="url(#colorAvgCitations)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {activeTab === 'keywords' && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="glass rounded-2xl p-6">
                  <div className="flex items-center gap-3 mb-6">
                    <Cloud className="w-5 h-5 text-accent-purple" />
                    <h3 className="text-lg font-semibold text-white">关键词词云</h3>
                  </div>
                  <div className="h-[500px] bg-dark-800/30 rounded-xl">
                    {wordCloudData.length > 0 ? (
                      <ReactWordcloud
                        words={wordCloudData}
                        options={options}
                        callbacks={callbacks}
                      />
                    ) : (
                      <div className="flex items-center justify-center h-full text-dark-400">
                        暂无数据
                      </div>
                    )}
                  </div>
                </div>

                <div className="glass rounded-2xl p-6">
                  <div className="flex items-center gap-3 mb-6">
                    <TrendingUp className="w-5 h-5 text-accent-green" />
                    <h3 className="text-lg font-semibold text-white">关键词趋势排名</h3>
                  </div>
                  <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
                    {keywordTrends.map((kw, index) => (
                      <div
                        key={kw.keyword}
                        className="flex items-center gap-4 p-3 bg-dark-800/50 rounded-xl hover:bg-dark-700/50 transition-colors group"
                      >
                        <span className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm ${
                          index < 5
                            ? 'bg-gradient-to-br from-accent-blue/20 to-accent-purple/20 text-accent-blue'
                            : 'bg-dark-700 text-dark-400'
                        }`}>
                          {index + 1}
                        </span>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-white font-medium group-hover:text-accent-blue transition-colors">
                              {kw.keyword}
                            </span>
                            <span className={`px-2 py-0.5 rounded-full text-xs border flex items-center gap-1 ${getTrendBadgeClass(kw.trend)}`}>
                              {getTrendIcon(kw.trend)}
                              {getTrendLabel(kw.trend)}
                            </span>
                          </div>
                          <div className="flex items-center gap-4 text-xs text-dark-400">
                            <span>出现次数: {kw.count.toLocaleString()}</span>
                            <span className={kw.growth_rate >= 0 ? 'text-accent-green' : 'text-accent-rose'}>
                              增长率: {kw.growth_rate >= 0 ? '+' : ''}{kw.growth_rate}%
                            </span>
                          </div>
                        </div>

                        <div className="w-24 bg-dark-700 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              kw.trend === 'rising'
                                ? 'bg-gradient-to-r from-accent-green to-accent-emerald'
                                : kw.trend === 'declining'
                                ? 'bg-gradient-to-r from-accent-rose to-accent-red'
                                : 'bg-gradient-to-r from-accent-amber to-accent-orange'
                            }`}
                            style={{ width: `${Math.min(100, (kw.count / keywordTrends[0].count) * 100)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
