import React, { useState, useEffect } from 'react';
import { Users, Search, Building2, FileText, Tag, TrendingUp, UserPlus, CheckCircle2, Target, Globe } from 'lucide-react';
import api from '@/services/api';
import type { CollaborationNetwork, CollaboratorInfo } from '@/types';

const CollaborationPage: React.FC = () => {
  const [authorName, setAuthorName] = useState('Alice Johnson');
  const [collabNetwork, setCollabNetwork] = useState<CollaborationNetwork | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'existing' | 'potential'>('potential');

  const fetchCollaborators = async () => {
    if (!authorName.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await api.getCollaborators(authorName, 30);
      if (response.success) {
        setCollabNetwork(response.data);
      } else {
        setError(response.error || '获取合作者信息失败');
      }
    } catch (err) {
      setError('请求失败，请检查网络连接');
    } finally {
      setError(null);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCollaborators();
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

  const getImpactColor = (impact: number) => {
    if (impact >= 10) return 'text-green-600';
    if (impact >= 5) return 'text-blue-600';
    return 'text-gray-600';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Users className="w-8 h-8 text-indigo-500" />
            <h1 className="text-3xl font-bold text-gray-900">合作者发现</h1>
          </div>
          <p className="text-gray-600">基于引用网络和研究主题相似性，识别潜在的学术合作机会</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                作者姓名
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  value={authorName}
                  onChange={(e) => setAuthorName(e.target.value)}
                  placeholder="输入作者姓名..."
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
            </div>
            <div className="flex items-end">
              <button
                onClick={fetchCollaborators}
                disabled={loading}
                className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? '正在分析...' : '发现合作者'}
              </button>
            </div>
          </div>

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}
        </div>

        {collabNetwork && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">分析结果</h2>
              <p className="text-sm text-gray-500 mt-1">
                为 <span className="font-medium text-indigo-600">{collabNetwork.target_author}</span> 找到的合作者
              </p>
            </div>
            <div className="flex gap-4 text-sm">
              <span className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full">
                <CheckCircle2 className="w-4 h-4 inline mr-1" />
                现有: {collabNetwork.existing_collaborators.length}
              </span>
              <span className="px-3 py-1 bg-green-50 text-green-700 rounded-full">
                <UserPlus className="w-4 h-4 inline mr-1" />
                潜在: {collabNetwork.potential_collaborators.length}
              </span>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="flex border-b border-gray-200">
              <button
                onClick={() => setActiveTab('potential')}
                className={`flex-1 px-6 py-3 text-sm font-medium transition-colors ${
                  activeTab === 'potential'
                    ? 'bg-gray-50 border-b-2 border-indigo-500 text-indigo-600'
                    : 'text-gray-500 hover:text-gray-700'
                }"
              >
                <UserPlus className="w-4 h-4 inline mr-2" />
                潜在合作者
              </button>
              <button
                onClick={() => setActiveTab('existing')}
                className={`flex-1 px-6 py-3 text-sm font-medium transition-colors ${
                  activeTab === 'existing'
                    ? 'bg-gray-50 border-b-2 border-indigo-500 text-indigo-600'
                    : 'text-gray-500 hover:text-gray-700'
                }"
              >
                <CheckCircle2 className="w-4 h-4 inline mr-2" />
                现有合作者
              </button>
            </div>

            <div className="p-6">
              {activeTab === 'existing' ? (
                <div className="space-y-4">
                  {collabNetwork.existing_collaborators.map((collab, index) => (
                    <CollaboratorCard
                      key={collab.name}
                      collaborator={collab}
                      rank={index + 1}
                      type="existing"
                      getScoreColor={getScoreColor}
                      getScoreBgColor={getScoreBgColor}
                      getImpactColor={getImpactColor}
                    />
                  ))}
                  {collabNetwork.existing_collaborators.length === 0 && (
                    <div className="text-center py-12 text-gray-500">
                      <Users className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                      <p>暂无现有合作者数据</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-4">
                  {collabNetwork.potential_collaborators.map((collab, index) => (
                    <CollaboratorCard
                      key={collab.name}
                      collaborator={collab}
                      rank={index + 1}
                      type="potential"
                      getScoreColor={getScoreColor}
                      getScoreBgColor={getScoreBgColor}
                      getImpactColor={getImpactColor}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
        )}
      </div>
    </div>
  );
};

interface CollaboratorCardProps {
  collaborator: CollaboratorInfo;
  rank: number;
  type: 'existing' | 'potential';
  getScoreColor: (score: number) => string;
  getScoreBgColor: (score: number) => string;
  getImpactColor: (impact: number) => string;
}

const CollaboratorCard: React.FC<CollaboratorCardProps> = ({
  collaborator,
  rank,
  type,
  getScoreColor,
  getScoreBgColor,
  getImpactColor,
}) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`rounded-lg border overflow-hidden transition-colors ${
        type === 'existing'
          ? 'border-blue-200 bg-blue-50/50'
          : 'border-green-200 bg-green-50/50'
      }`}
    >
      <div
        className="p-4 cursor-pointer hover:bg-white/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start gap-4">
          <div className={`flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-lg ${
            type === 'existing' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'
          } font-bold`}>
            {rank}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  {collaborator.name}
                </h3>
                <div className="mt-1 flex items-center gap-3 text-sm text-gray-500">
                  {collaborator.affiliation && (
                    <div className="flex items-center gap-1">
                      <Building2 className="w-4 h-4" />
                      <span>{collaborator.affiliation}</span>
                    </div>
                  )}
                  {collaborator.orcid && (
                    <div className="flex items-center gap-1">
                      <Globe className="w-4 h-4" />
                      <span className="font-mono text-xs">{collaborator.orcid}</span>
                    </div>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className={`px-3 py-1 rounded-full text-sm font-medium ${getScoreBgColor(collaborator.collaboration_score)}`}>
                  匹配度 {(collaborator.collaboration_score * 100).toFixed(0)}%
                </div>
              </div>
            </div>
            <div className="mt-3 flex items-center gap-4 text-sm">
              <div className="flex items-center gap-1 text-gray-600">
                <FileText className="w-4 h-4" />
                <span>发表 {collaborator.paper_count} 篇论文</span>
              </div>
              <div className={`flex items-center gap-1">
                <TrendingUp className="w-4 h-4" />
                <span className={getImpactColor(collaborator.potential_impact)}>
                  潜在影响 {collaborator.potential_impact.toFixed(1)}
                </span>
              </div>
              <div className="flex items-center gap-1 text-gray-600">
                <Target className="w-4 h-4" />
                <span>{collaborator.match_reason}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-200/50">
          <div className="pt-4 grid grid-cols-2 gap-6">
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
              <Tag className="w-4 h-4 text-indigo-500" />
                研究重叠领域
              </h4>
              <div className="flex flex-wrap gap-2">
                {collaborator.research_overlap.map((keyword, i) => (
                  <span
                    key={i}
                    className="px-2 py-1 bg-indigo-50 text-indigo-700 text-xs rounded-md"
                  >
                    {keyword}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-500" />
                相关论文 ({collaborator.common_papers.length})
              </h4>
              <div className="space-y-1">
                {collaborator.common_papers.map((paper, i) => (
                  <div key={i} className="text-sm text-gray-500 font-mono bg-gray-50 px-2 py-1 rounded truncate">
                    {paper}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CollaborationPage;
