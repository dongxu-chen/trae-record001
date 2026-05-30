import { useState, useEffect } from 'react';
import { X, Database, Play, BarChart3, Hash, Table2, GitBranch, Clock, User, ChevronDown, ChevronRight, Layers, Shield, BookOpen, Bell } from 'lucide-react';
import { useLineageStore } from '@/stores/useLineageStore';
import { RiskAssessmentPanel } from './RiskAssessmentPanel';
import { DataDictionaryPanel } from './DataDictionaryPanel';
import { SubscriptionPanel } from './SubscriptionPanel';

type DetailTab = 'overview' | 'risk' | 'dictionary' | 'subscription';

const getTypeIcon = (type: string) => {
  switch (type) {
    case 'field': return <Hash className="w-5 h-5" />;
    case 'table': return <Table2 className="w-5 h-5" />;
    case 'etl': return <Play className="w-5 h-5" />;
    case 'report': return <BarChart3 className="w-5 h-5" />;
    default: return <Database className="w-5 h-5" />;
  }
};

const getTypeColor = (type: string) => {
  switch (type) {
    case 'field': return 'text-blue-500 bg-blue-50';
    case 'table': return 'text-teal-500 bg-teal-50';
    case 'etl': return 'text-orange-500 bg-orange-50';
    case 'report': return 'text-pink-500 bg-pink-50';
    default: return 'text-gray-500 bg-gray-50';
  }
};

const getTypeName = (type: string) => {
  switch (type) {
    case 'field': return '字段';
    case 'table': return '数据表';
    case 'etl': return 'ETL任务';
    case 'report': return '报表';
    default: return '未知';
  }
};

const TABS: { key: DetailTab; label: string; icon: React.ReactNode }[] = [
  { key: 'overview', label: '影响概览', icon: <GitBranch className="w-4 h-4" /> },
  { key: 'risk', label: '风险评估', icon: <Shield className="w-4 h-4" /> },
  { key: 'dictionary', label: '数据字典', icon: <BookOpen className="w-4 h-4" /> },
  { key: 'subscription', label: '变更订阅', icon: <Bell className="w-4 h-4" /> },
];

export const DetailPanel = () => {
  const { selectedNode, analysisResult, setSelectedNode, setShowDetailPanel, showDetailPanel } = useLineageStore();
  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const [expandedDepths, setExpandedDepths] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (activeTab === 'dictionary' && selectedNode) {
      const { loadFieldDictionary } = useLineageStore.getState();
      loadFieldDictionary(selectedNode.id);
    }
    if (activeTab === 'subscription' && selectedNode) {
      const { loadSubscriptions, loadNotifications } = useLineageStore.getState();
      loadSubscriptions(selectedNode.id);
      loadNotifications(selectedNode.id);
    }
  }, [activeTab, selectedNode]);

  const toggleDepth = (depth: number) => {
    setExpandedDepths(prev => {
      const next = new Set(prev);
      if (next.has(depth)) next.delete(depth);
      else next.add(depth);
      return next;
    });
  };

  if (!showDetailPanel) {
    return (
      <button
        onClick={() => setShowDetailPanel(true)}
        className="w-10 bg-white border-l border-gray-200 flex items-center justify-center hover:bg-gray-50"
      >
        <GitBranch className="w-5 h-5 text-gray-500" />
      </button>
    );
  }

  return (
    <div className="w-96 bg-white border-l border-gray-200 flex flex-col h-full animate-slide-in-right">
      <div className="border-b border-gray-200">
        <div className="p-4 flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">分析详情</h3>
          <button onClick={() => setShowDetailPanel(false)} className="p-1 hover:bg-gray-100 rounded">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="flex border-t border-gray-100">
          {TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-1 py-2.5 flex items-center justify-center gap-1.5 text-xs font-medium transition-colors border-b-2 ${
                activeTab === tab.key
                  ? 'text-primary-600 border-primary-500 bg-primary-50/50'
                  : 'text-gray-500 border-transparent hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {!analysisResult && activeTab !== 'subscription' ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-500">
              <GitBranch className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p className="text-sm">请先进行血缘分析</p>
            </div>
          </div>
        ) : activeTab === 'overview' ? (
          <OverviewContent
            selectedNode={selectedNode}
            analysisResult={analysisResult}
            setSelectedNode={setSelectedNode}
            expandedDepths={expandedDepths}
            toggleDepth={toggleDepth}
          />
        ) : activeTab === 'risk' ? (
          <RiskAssessmentPanel />
        ) : activeTab === 'dictionary' ? (
          <DataDictionaryPanel />
        ) : (
          <SubscriptionPanel />
        )}
      </div>
    </div>
  );
};

const OverviewContent = ({ selectedNode, analysisResult, setSelectedNode, expandedDepths, toggleDepth }: {
  selectedNode: any;
  analysisResult: any;
  setSelectedNode: (node: any) => void;
  expandedDepths: Set<number>;
  toggleDepth: (depth: number) => void;
}) => {
  if (!analysisResult) return null;

  if (selectedNode) {
    return (
      <div className="space-y-6">
        <div className="flex items-start gap-3">
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${getTypeColor(selectedNode?.type || '')}`}>
            {getTypeIcon(selectedNode?.type || '')}
          </div>
          <div className="flex-1">
            <h4 className="font-semibold text-gray-900">{selectedNode?.name}</h4>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              <span className={`px-2 py-0.5 text-xs rounded-full ${getTypeColor(selectedNode?.type || '')}`}>
                {getTypeName(selectedNode?.type || '')}
              </span>
              {selectedNode?.depth !== undefined && selectedNode.depth > 0 && (
                <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded-full">
                  深度 {selectedNode.depth}
                </span>
              )}
              {selectedNode?.hasChildren && (
                <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-700 rounded-full">有子节点</span>
              )}
            </div>
          </div>
        </div>
        {selectedNode?.description && (
          <div>
            <h5 className="text-xs font-medium text-gray-500 uppercase mb-1">描述</h5>
            <p className="text-sm text-gray-700">{selectedNode.description}</p>
          </div>
        )}
        {(selectedNode?.table || selectedNode?.database) && (
          <div className="space-y-3">
            <h5 className="text-xs font-medium text-gray-500 uppercase">位置信息</h5>
            {selectedNode?.database && (
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">数据库</span>
                <span className="text-sm font-mono text-gray-900">{selectedNode.database}</span>
              </div>
            )}
            {selectedNode?.table && (
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">数据表</span>
                <span className="text-sm font-mono text-gray-900">{selectedNode.table}</span>
              </div>
            )}
            {selectedNode?.depth !== undefined && (
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">影响深度</span>
                <span className="text-sm font-medium text-purple-600">第 {selectedNode.depth} 层</span>
              </div>
            )}
          </div>
        )}
        <div className="pt-2">
          <button onClick={() => setSelectedNode(null)} className="w-full btn-secondary text-sm">
            返回影响统计
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h4 className="text-sm font-semibold text-gray-700 mb-3">影响统计</h4>
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-gradient-to-br from-primary-50 to-primary-100 rounded-xl p-4">
            <div className="text-2xl font-bold text-primary-600">{analysisResult.statistics.totalDownstreamNodes}</div>
            <div className="text-xs text-primary-500">下游节点总数</div>
          </div>
          <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-4">
            <div className="text-2xl font-bold text-purple-600">{analysisResult.statistics.maxDepth}</div>
            <div className="text-xs text-purple-500">最大影响深度</div>
          </div>
          <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-xl p-4">
            <div className="text-2xl font-bold text-orange-600">{analysisResult.statistics.etlTasks}</div>
            <div className="text-xs text-orange-500">ETL任务</div>
          </div>
          <div className="bg-gradient-to-br from-pink-50 to-pink-100 rounded-xl p-4">
            <div className="text-2xl font-bold text-pink-600">{analysisResult.statistics.reports}</div>
            <div className="text-xs text-pink-500">报表看板</div>
          </div>
          <div className="bg-gradient-to-br from-teal-50 to-teal-100 rounded-xl p-4 col-span-2">
            <div className="text-2xl font-bold text-teal-600">{analysisResult.statistics.tables}</div>
            <div className="text-xs text-teal-500">数据表</div>
          </div>
        </div>
      </div>

      <div>
        <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
          <Layers className="w-4 h-4 text-purple-500" />
          按影响深度分组
        </h4>
        <div className="space-y-2">
          {analysisResult.downstreamByDepth.map((depthGroup: any) => {
            const isExpanded = expandedDepths.has(depthGroup.depth);
            const isRoot = depthGroup.depth === 0;
            return (
              <div key={depthGroup.depth} className="border border-gray-200 rounded-lg overflow-hidden">
                <button
                  onClick={() => toggleDepth(depthGroup.depth)}
                  className="w-full px-3 py-2 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    {isExpanded ? <ChevronDown className="w-4 h-4 text-gray-500" /> : <ChevronRight className="w-4 h-4 text-gray-500" />}
                    <span className="text-sm font-medium text-gray-700">{isRoot ? '根节点' : `深度 ${depthGroup.depth}`}</span>
                    <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full">{depthGroup.nodes.length} 个节点</span>
                  </div>
                </button>
                {isExpanded && (
                  <div className="p-2 space-y-1 bg-white">
                    {depthGroup.nodes.map((node: any) => (
                      <button
                        key={node.id}
                        onClick={() => setSelectedNode(node)}
                        className="w-full p-2 flex items-center gap-2 rounded-lg hover:bg-gray-50 transition-colors text-left"
                      >
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${getTypeColor(node.type)}`}>
                          {getTypeIcon(node.type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-gray-900 truncate">{node.name}</div>
                          <div className="text-xs text-gray-500">{getTypeName(node.type)}{node.table && ` · ${node.table}`}</div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {analysisResult.downstreamList.etlTasks.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <Play className="w-4 h-4 text-orange-500" />受影响的ETL任务
          </h4>
          <div className="space-y-2">
            {analysisResult.downstreamList.etlTasks.map((task: any) => (
              <div key={task.id} className="p-3 bg-gray-50 rounded-lg border border-gray-100">
                <div className="font-medium text-gray-900 text-sm">{task.name}</div>
                <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                  <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{task.schedule}</span>
                  <span className="flex items-center gap-1"><User className="w-3 h-3" />{task.owner}</span>
                </div>
                <div className="mt-2">
                  <span className={`inline-block px-2 py-0.5 text-xs rounded-full ${
                    task.status === 'success' ? 'bg-green-100 text-green-700' : task.status === 'running' ? 'bg-blue-100 text-blue-700' : 'bg-red-100 text-red-700'
                  }`}>
                    {task.status === 'success' ? '成功' : task.status === 'running' ? '运行中' : '失败'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {analysisResult.downstreamList.reports.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-pink-500" />受影响的报表
          </h4>
          <div className="space-y-2">
            {analysisResult.downstreamList.reports.map((report: any) => (
              <div key={report.id} className="p-3 bg-gray-50 rounded-lg border border-gray-100">
                <div className="font-medium text-gray-900 text-sm">{report.name}</div>
                <div className="flex items-center gap-2 mt-2">
                  <span className="px-2 py-0.5 text-xs bg-pink-100 text-pink-700 rounded-full">
                    {report.type === 'dashboard' ? '看板' : report.type === 'report' ? '报表' : '图表'}
                  </span>
                  <span className="text-xs text-gray-500 flex items-center gap-1"><User className="w-3 h-3" />{report.owner}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {analysisResult.downstreamList.tables.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <Table2 className="w-4 h-4 text-teal-500" />受影响的数据表
          </h4>
          <div className="space-y-2">
            {analysisResult.downstreamList.tables.map((table: any) => (
              <div key={table.id} className="p-3 bg-gray-50 rounded-lg border border-gray-100 flex items-center justify-between">
                <div>
                  <div className="font-medium text-gray-900 text-sm font-mono">{table.database}.{table.name}</div>
                  <div className="text-xs text-gray-500 mt-1">{table.fieldCount} 个字段</div>
                </div>
                <div className="w-2 h-2 rounded-full bg-teal-500" />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
