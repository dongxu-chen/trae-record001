import React, { useState, useEffect } from 'react';
import { Search, TrendingUp, BarChart3, FileText, Clock, CheckCircle2, AlertCircle, LineChart, Zap, Award } from 'lucide-react';
import { LineChart as RechartsLineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';
import api from '@/services/api';
import type { CitationPrediction } from '@/types';

const PredictionPage: React.FC = () => {
  const [searchDOI, setSearchDOI] = useState('10.1234/mock.00001');
  const [prediction, setPrediction] = useState<CitationPrediction | null>(null);
  const [trendingPapers, setTrendingPapers] = useState<CitationPrediction[]>([]);
  const [loading, setLoading] = useState(false);
  const [trendingLoading, setTrendingLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'single' | 'trending'>('trending');

  const fetchPrediction = async () => {
    if (!searchDOI.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await api.getCitationPrediction(searchDOI);
      if (response.success) {
        setPrediction(response.data);
      } else {
        setError(response.error || '获取预测失败');
      }
    } catch (err) {
      setError('请求失败，请检查网络连接');
    } finally {
      setLoading(false);
    }
  };

  const fetchTrendingPapers = async () => {
    setTrendingLoading(true);

    try {
      const response = await api.getTrendingPapers(20);
      if (response.success) {
        setTrendingPapers(response.data || []);
      }
    } catch (err) {
      console.error('Failed to fetch trending papers');
    } finally {
      setTrendingLoading(false);
    }
  };

  useEffect(() => {
    fetchTrendingPapers();
  }, []);

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-blue-600';
    if (confidence >= 0.4) return 'text-yellow-600';
    return 'text-gray-600';
  };

  const getGrowthColor = (growth: number) => {
    if (growth >= 0.5) return 'text-green-600';
    if (growth >= 0.3) return 'text-blue-600';
    if (growth >= 0.1) return 'text-yellow-600';
    return 'text-gray-600';
  };

  const getGrowthBgColor = (growth: number) => {
    if (growth >= 0.5) return 'bg-green-100 text-green-700';
    if (growth >= 0.3) return 'bg-blue-100 text-blue-700';
    if (growth >= 0.1) return 'bg-yellow-100 text-yellow-700';
    return 'bg-gray-100 text-gray-700';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <TrendingUp className="w-8 h-8 text-indigo-500" />
            <h1 className="text-3xl font-bold text-gray-900">影响力预测</h1>
          </div>
          <p className="text-gray-600">基于历史引用数据和网络特征，预测论文未来的引用增长趋势</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                论文 DOI
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  value={searchDOI}
                  onChange={(e) => setSearchDOI(e.target.value)}
                  placeholder="输入论文DOI..."
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
            </div>
            <div className="flex items-end gap-3">
              <button
                onClick={fetchPrediction}
                disabled={loading}
                className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? '预测中...' : '预测引用量'}
              </button>
            </div>
          </div>

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden mb-8">
          <div className="flex border-b border-gray-200">
            <button
              onClick={() => setActiveTab('trending')}
              className={`flex-1 px-6 py-3 text-sm font-medium transition-colors ${
                activeTab === 'trending'
                  ? 'bg-gray-50 border-b-2 border-indigo-500 text-indigo-600'
                  : 'text-gray-500 hover:text-gray-700'
              }"
            >
              <Zap className="w-4 h-4 inline mr-2" />
              高增长趋势论文
            </button>
            <button
              onClick={() => setActiveTab('single')}
              className={`flex-1 px-6 py-3 text-sm font-medium transition-colors ${
                activeTab === 'single'
                  ? 'bg-gray-50 border-b-2 border-indigo-500 text-indigo-600'
                  : 'text-gray-500 hover:text-gray-700'
              }"
            >
              <BarChart3 className="w-4 h-4 inline mr-2" />
              单篇论文预测
            </button>
          </div>

          <div className="p-6">
            {activeTab === 'trending' ? (
              <div>
                {trendingLoading ? (
                  <div className="text-center py-12">
                    <div className="animate-spin w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full mx-auto mb-4" />
                    <p className="text-gray-500">正在分析趋势...</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      {trendingPapers.slice(0, 6).map((paper, index) => (
                        <TrendingCard
                          key={paper.doi}
                          paper={paper}
                          rank={index + 1}
                          getGrowthColor={getGrowthColor}
                          getGrowthBgColor={getGrowthBgColor}
                        />
                      ))}
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">增长率对比</h3>
                      <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={trendingPapers.slice(0, 10).map((p, i) => ({
                            name: `#${i + 1}`,
                            growth: p.growth_rate * 100,
                            citations: p.current_citations
                          }))}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="name" />
                            <YAxis />
                            <Tooltip
                              formatter={(value: number, name: string) => [
                                name === 'growth' ? `${value.toFixed(1)}%` : value,
                                name === 'growth' ? '增长率' : '当前引用'
                              ]}
                            />
                            <Legend />
                            <Bar dataKey="growth" name="增长率 (%)" fill="#6366f1" />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              prediction && <PredictionDetail prediction={prediction} getConfidenceColor={getConfidenceColor} getGrowthColor={getGrowthColor} />
            )}
          </div>
        </div>

        {prediction && activeTab === 'single' && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-gray-900">预测详情</h2>
            <PredictionDetail prediction={prediction} getConfidenceColor={getConfidenceColor} getGrowthColor={getGrowthColor} />
          </div>
        )}
      </div>
    </div>
  );
};

interface TrendingCardProps {
  paper: CitationPrediction;
  rank: number;
  getGrowthColor: (growth: number) => string;
  getGrowthBgColor: (growth: number) => string;
}

const TrendingCard: React.FC<TrendingCardProps> = ({ paper, rank, getGrowthBgColor }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-gray-50 rounded-lg border border-gray-200 overflow-hidden">
      <div
        className="p-4 cursor-pointer hover:bg-gray-100 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-gradient-to-br from-yellow-400 to-orange-500 text-white font-bold rounded-lg">
            {rank}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-4">
              <h3 className="text-sm font-semibold text-gray-900 line-clamp-2">
                {paper.title}
              </h3>
              <div className={`flex-shrink-0 px-3 py-1 rounded-full text-xs font-medium ${getGrowthBgColor(paper.growth_rate)}`}>
                +{(paper.growth_rate * 100).toFixed(0)}%
              </div>
            </div>
            <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
              <div className="flex items-center gap-1">
                <FileText className="w-3 h-3" />
                <span>当前引用: {paper.current_citations}</span>
              </div>
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span>发表 {paper.age_years.toFixed(1)} 年</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-200">
          <div className="pt-4 space-y-3">
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-3 bg-blue-50 rounded-lg">
                <div className="text-lg font-bold text-blue-700">{paper.predicted_citations_1y}</div>
                <div className="text-xs text-gray-500">1年预测</div>
              </div>
              <div className="text-center p-3 bg-green-50 rounded-lg">
                <div className="text-lg font-bold text-green-700">{paper.predicted_citations_3y}</div>
                <div className="text-xs text-gray-500">3年预测</div>
              </div>
              <div className="text-center p-3 bg-purple-50 rounded-lg">
                <div className="text-lg font-bold text-purple-700">{paper.predicted_citations_5y}</div>
                <div className="text-xs text-gray-500">5年预测</div>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {paper.key_factors.map((factor, i) => (
                <span key={i} className="px-2 py-1 bg-indigo-50 text-indigo-700 text-xs rounded-md">
                  {factor}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

interface PredictionDetailProps {
  prediction: CitationPrediction;
  getConfidenceColor: (confidence: number) => string;
  getGrowthColor: (growth: number) => string;
}

const PredictionDetail: React.FC<PredictionDetailProps> = ({ prediction, getConfidenceColor, getGrowthColor }) => {
  const chartData = [
    { year: '当前', citations: prediction.current_citations },
    { year: '1年后', citations: prediction.predicted_citations_1y },
    { year: '3年后', citations: prediction.predicted_citations_3y },
    { year: '5年后', citations: prediction.predicted_citations_5y },
  ];

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl p-6 text-white">
        <h3 className="text-xl font-bold mb-2">{prediction.title}</h3>
        <div className="flex items-center gap-6 text-sm opacity-90">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4" />
            <span>DOI: {prediction.doi}</span>
          </div>
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4" />
            <span>发表 {prediction.age_years.toFixed(1)} 年</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
          <div className="text-3xl font-bold text-gray-900">{prediction.current_citations}</div>
          <div className="text-sm text-gray-500 mt-1">当前引用</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
          <div className="text-3xl font-bold text-blue-600">{prediction.predicted_citations_1y}</div>
          <div className="text-sm text-gray-500 mt-1">1年预测</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
          <div className="text-3xl font-bold text-green-600">{prediction.predicted_citations_3y}</div>
          <div className="text-sm text-gray-500 mt-1">3年预测</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
          <div className="text-3xl font-bold text-purple-600">{prediction.predicted_citations_5y}</div>
          <div className="text-sm text-gray-500 mt-1">5年预测</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <LineChart className="w-5 h-5 text-indigo-500" />
            引用增长趋势
          </h4>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsLineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="year" />
                <YAxis />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="citations"
                  stroke="#6366f1"
                  strokeWidth={3}
                  dot={{ fill: '#6366f1', strokeWidth: 2, r: 6 }}
                />
              </RechartsLineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-indigo-500" />
              预测指标
            </h4>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">置信度</span>
                  <span className={`font-medium ${getConfidenceColor(prediction.confidence_score)}`}>
                    {(prediction.confidence_score * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-green-500 transition-all"
                    style={{ width: `${prediction.confidence_score * 100}%` }}
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">年增长率</span>
                  <span className={`font-medium ${getGrowthColor(prediction.growth_rate)}`}>
                    {(prediction.growth_rate * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-yellow-500 to-green-500 transition-all"
                    style={{ width: `${Math.min(prediction.growth_rate * 100, 100)}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Award className="w-5 h-5 text-indigo-500" />
              关键影响因素
            </h4>
            <div className="space-y-2">
              {prediction.key_factors.map((factor, index) => (
                <div key={index} className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                  <span className="text-sm text-gray-700">{factor}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PredictionPage;
