import React, { useState, useEffect } from 'react';
import { Search, Sparkles, FileText, Users, Award, TrendingUp } from 'lucide-react';
import api from '@/services/api';
import type { PaperRecommendations, RecommendedPaper } from '@/types';

const RecommendationPage: React.FC = () => {
  const [searchDOI, setSearchDOI] = useState('10.1234/mock.00001');
  const [method, setMethod] = useState<'hybrid' | 'citation' | 'content'>('hybrid');
  const [recommendations, setRecommendations] = useState<PaperRecommendations | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRecommendations = async () => {
    if (!searchDOI.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await api.getRecommendations(searchDOI, 20, method);
      if (response.success) {
        setRecommendations(response.data);
      } else {
        setError(response.error || '获取推荐失败');
      }
    } catch (err) {
      setError('请求失败，请检查网络连接');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, []);

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-500';
    if (score >= 0.6) return 'text-blue-500';
    if (score >= 0.4) return 'text-yellow-500';
    return 'text-gray-500';
  };

  const getScoreBgColor = (score: number) => {
    if (score >= 0.8) return 'bg-green-100 text-green-700';
    if (score >= 0.6) return 'bg-blue-100 text-blue-700';
    if (score >= 0.4) return 'bg-yellow-100 text-yellow-700';
    return 'bg-gray-100 text-gray-700';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Sparkles className="w-8 h-8 text-indigo-500" />
            <h1 className="text-3xl font-bold text-gray-900">论文推荐</h1>
          </div>
          <p className="text-gray-600">基于引用网络和内容相似度，为您推荐相关学术论文</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
          <div className="flex flex-col gap-4">
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
              <div className="w-48">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  推荐方法
                </label>
                <select
                  value={method}
                  onChange={(e) => setMethod(e.target.value as any)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                >
                  <option value="hybrid">混合推荐</option>
                  <option value="citation">引用网络</option>
                  <option value="content">内容相似</option>
                </select>
              </div>
            </div>
            <button
              onClick={fetchRecommendations}
              disabled={loading}
              className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? '正在获取推荐...' : '获取推荐'}
            </button>
          </div>

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}
        </div>

        {recommendations && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">推荐结果</h2>
                <p className="text-sm text-gray-500 mt-1">
                  基于 {method === 'hybrid' ? '混合算法' : method === 'citation' ? '引用网络' : '内容相似度'}，找到 {recommendations.recommendations.length} 篇相关论文
                </p>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <span>目标论文:</span>
                <code className="px-2 py-1 bg-gray-100 rounded text-indigo-600 font-mono">
                  {recommendations.target_doi}
                </code>
              </div>
            </div>

            <div className="space-y-4">
              {recommendations.recommendations.map((paper, index) => (
                <RecommendationCard
                  key={paper.doi}
                  paper={paper}
                  rank={index + 1}
                  getScoreColor={getScoreColor}
                  getScoreBgColor={getScoreBgColor}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

interface RecommendationCardProps {
  paper: RecommendedPaper;
  rank: number;
  getScoreColor: (score: number) => string;
  getScoreBgColor: (score: number) => string;
}

const RecommendationCard: React.FC<RecommendationCardProps> = ({
  paper,
  rank,
  getScoreColor,
  getScoreBgColor,
}) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div
        className="p-6 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-indigo-100 text-indigo-700 font-bold rounded-lg">
            {rank}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-4">
              <h3 className="text-lg font-semibold text-gray-900 leading-tight hover:text-indigo-600 transition-colors">
                {paper.title}
              </h3>
              <div className={`flex-shrink-0 px-3 py-1 rounded-full text-sm font-medium ${getScoreBgColor(paper.score)}`}>
                {(paper.score * 100).toFixed(0)}%
              </div>
            </div>
            <div className="mt-2 flex items-center gap-4 text-sm text-gray-500">
              <div className="flex items-center gap-1">
                <Users className="w-4 h-4" />
                <span>{paper.authors.map(a => a.name).join(', ')}</span>
              </div>
              <div className="flex items-center gap-1">
                <FileText className="w-4 h-4" />
                <span>{paper.venue} · {paper.year}</span>
              </div>
            </div>
            <div className="mt-3 flex items-center gap-3">
              <span className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-md">
                推荐理由: {paper.reason}
              </span>
              <span className="text-sm text-gray-500">
                内容相似度: <span className={getScoreColor(paper.similarity)}>{(paper.similarity * 100).toFixed(0)}%</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {expanded && (
        <div className="px-6 pb-6 border-t border-gray-100">
          <div className="pt-4 grid grid-cols-2 gap-6">
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                <Award className="w-4 h-4 text-yellow-500" />
                共同参考文献 ({paper.common_references.length})
              </h4>
              <div className="space-y-1">
                {paper.common_references.map((ref, i) => (
                  <div key={i} className="text-sm text-gray-500 font-mono bg-gray-50 px-2 py-1 rounded">
                    {ref}
                  </div>
                ))}
              </div>
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-green-500" />
                共同引用 ({paper.common_citations.length})
              </h4>
              <div className="space-y-1">
                {paper.common_citations.map((cit, i) => (
                  <div key={i} className="text-sm text-gray-500 font-mono bg-gray-50 px-2 py-1 rounded">
                    {cit}
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-gray-100">
            <div className="text-xs text-gray-400 font-mono">
              DOI: {paper.doi}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RecommendationPage;
