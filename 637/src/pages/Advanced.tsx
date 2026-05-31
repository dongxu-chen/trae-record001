import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useStore } from '../store/useStore';
import { Settings, Users, RefreshCw, AlertTriangle, Check, X, Plus, Trash2, Code, Copy, Download, Upload, FileCode, Sparkles } from 'lucide-react';
import type { TeamNamingRule, VariableType, NamingStyle } from '../../shared/types';

const VARIABLE_TYPES: VariableType[] = ['variable', 'function', 'class', 'constant', 'boolean'];
const NAMING_STYLES: NamingStyle[] = ['camelCase', 'snake_case', 'PascalCase', 'kebab-case', 'SCREAMING_SNAKE_CASE'];

type TabType = 'team' | 'batch' | 'conflicts';

export default function Advanced() {
  const [activeTab, setActiveTab] = useState<TabType>('team');
  const {
    teamConfig,
    batchRenameCode,
    batchRenameItems,
    batchRenameResult,
    conflictCheckResult,
    fetchTeamConfig,
    addTeamRule,
    deleteTeamRule,
    setBatchRenameCode,
    detectVariablesInCode,
    updateBatchRenameItem,
    performBatchRename,
    clearBatchRename,
    checkNameConflicts,
    clearConflictResult
  } = useStore();

  const [newRule, setNewRule] = useState<Partial<TeamNamingRule>>({
    name: '',
    description: '',
    type: 'prefix',
    value: '',
    variableTypes: [],
    enabled: true,
    priority: 50
  });

  const [conflictCheckName, setConflictCheckName] = useState('');
  const [conflictCheckCode, setConflictCheckCode] = useState('');
  const [copiedResult, setCopiedResult] = useState(false);

  useEffect(() => {
    fetchTeamConfig();
  }, [fetchTeamConfig]);

  const handleAddRule = async () => {
    if (!newRule.name || !newRule.value) return;
    await addTeamRule(newRule as Omit<TeamNamingRule, 'id' | 'createdAt'>);
    setNewRule({
      name: '',
      description: '',
      type: 'prefix',
      value: '',
      variableTypes: [],
      enabled: true,
      priority: 50
    });
  };

  const toggleVariableType = (type: VariableType) => {
    setNewRule(prev => ({
      ...prev,
      variableTypes: prev.variableTypes?.includes(type)
        ? prev.variableTypes.filter(t => t !== type)
        : [...(prev.variableTypes || []), type]
    }));
  };

  const handleDetectVariables = () => {
    if (batchRenameCode.trim()) {
      detectVariablesInCode(batchRenameCode);
    }
  };

  const handleBatchRename = () => {
    const itemsToRename = batchRenameItems.filter(item => item.oldName !== item.newName);
    if (itemsToRename.length > 0) {
      performBatchRename(itemsToRename);
    }
  };

  const handleCheckConflicts = () => {
    if (conflictCheckName.trim()) {
      checkNameConflicts(conflictCheckName, conflictCheckCode);
    }
  };

  const copyResult = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedResult(true);
      setTimeout(() => setCopiedResult(false), 2000);
    } catch (err) {
      console.error('复制失败:', err);
    }
  };

  const tabs = [
    { id: 'team' as TabType, label: '团队规范', icon: Users },
    { id: 'batch' as TabType, label: '批量重命名', icon: RefreshCw },
    { id: 'conflicts' as TabType, label: '冲突检测', icon: AlertTriangle }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent mb-2">
            高级功能
          </h1>
          <p className="text-slate-400">团队命名规范管理、批量重命名和冲突检测</p>
        </motion.div>

        <div className="flex justify-center mb-8">
          <div className="flex bg-slate-800/50 rounded-xl p-1 gap-1">
            {tabs.map(tab => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-6 py-3 rounded-lg transition-all duration-200 ${
                    activeTab === tab.id
                      ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-lg'
                      : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {activeTab === 'team' && (
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="grid grid-cols-1 lg:grid-cols-2 gap-6"
          >
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Plus className="w-5 h-5 text-indigo-400" />
                添加命名规则
              </h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">规则名称</label>
                  <input
                    type="text"
                    value={newRule.name}
                    onChange={e => setNewRule(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="例如：React Hook前缀"
                    className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">规则描述</label>
                  <input
                    type="text"
                    value={newRule.description}
                    onChange={e => setNewRule(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="规则说明"
                    className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">规则类型</label>
                    <select
                      value={newRule.type}
                      onChange={e => setNewRule(prev => ({ ...prev, type: e.target.value as any }))}
                      className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="prefix">前缀</option>
                      <option value="suffix">后缀</option>
                      <option value="forbidden">禁用词</option>
                      <option value="required">必需包含</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">值</label>
                    <input
                      type="text"
                      value={newRule.value}
                      onChange={e => setNewRule(prev => ({ ...prev, value: e.target.value }))}
                      placeholder="例如：use"
                      className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">适用类型</label>
                  <div className="flex flex-wrap gap-2">
                    {VARIABLE_TYPES.map(type => (
                      <button
                        key={type}
                        onClick={() => toggleVariableType(type)}
                        className={`px-3 py-1 rounded-full text-sm transition-all ${
                          newRule.variableTypes?.includes(type)
                            ? 'bg-indigo-500 text-white'
                            : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                        }`}
                      >
                        {type}
                      </button>
                    ))}
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <label className="text-sm font-medium text-slate-300">优先级: {newRule.priority}</label>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={newRule.priority}
                      onChange={e => setNewRule(prev => ({ ...prev, priority: parseInt(e.target.value) }))}
                      className="w-32"
                    />
                  </div>
                  
                  <button
                    onClick={handleAddRule}
                    className="px-6 py-2 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg font-medium hover:opacity-90 transition-opacity"
                  >
                    添加规则
                  </button>
                </div>
              </div>
            </div>

            <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Settings className="w-5 h-5 text-indigo-400" />
                当前规则
              </h2>
              
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {teamConfig?.rules.length === 0 ? (
                  <div className="text-center py-8 text-slate-400">
                    <Sparkles className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>暂无自定义规则</p>
                  </div>
                ) : (
                  teamConfig?.rules.map(rule => (
                    <motion.div
                      key={rule.id}
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className={`p-4 rounded-xl border ${
                        rule.enabled
                          ? 'bg-slate-700/30 border-slate-600'
                          : 'bg-slate-800/50 border-slate-700/50 opacity-60'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{rule.name}</span>
                            <span className={`text-xs px-2 py-0.5 rounded ${
                              rule.type === 'prefix' ? 'bg-blue-500/20 text-blue-400' :
                              rule.type === 'suffix' ? 'bg-green-500/20 text-green-400' :
                              rule.type === 'forbidden' ? 'bg-red-500/20 text-red-400' :
                              'bg-yellow-500/20 text-yellow-400'
                            }`}>
                              {rule.type}
                            </span>
                            <span className="text-xs text-slate-400">优先级: {rule.priority}</span>
                          </div>
                          <p className="text-sm text-slate-400 mt-1">{rule.description}</p>
                          <p className="text-sm text-indigo-400 mt-1">值: {rule.value}</p>
                          <div className="flex gap-1 mt-2">
                            {rule.variableTypes.map(type => (
                              <span key={type} className="text-xs px-2 py-0.5 bg-slate-600/50 rounded text-slate-300">
                                {type}
                              </span>
                            ))}
                          </div>
                        </div>
                        <button
                          onClick={() => deleteTeamRule(rule.id)}
                          className="p-1 text-slate-400 hover:text-red-400 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </motion.div>
                  ))
                )}
              </div>
              
              <div className="mt-4 pt-4 border-t border-slate-700">
                <h3 className="text-sm font-medium text-slate-300 mb-2">禁用词汇</h3>
                <div className="flex flex-wrap gap-2">
                  {teamConfig?.forbiddenWords.slice(0, 10).map(word => (
                    <span key={word} className="text-xs px-2 py-1 bg-red-500/20 text-red-400 rounded">
                      {word}
                    </span>
                  ))}
                  {teamConfig && teamConfig.forbiddenWords.length > 10 && (
                    <span className="text-xs px-2 py-1 bg-slate-600/50 text-slate-400 rounded">
                      +{teamConfig.forbiddenWords.length - 10} 更多
                    </span>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {activeTab === 'batch' && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-6"
          >
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <FileCode className="w-5 h-5 text-indigo-400" />
                代码输入
              </h2>
              
              <div className="mb-4">
                <textarea
                  value={batchRenameCode}
                  onChange={e => setBatchRenameCode(e.target.value)}
                  placeholder="粘贴代码以检测变量..."
                  className="w-full h-48 px-4 py-3 bg-slate-900/50 border border-slate-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-sm"
                />
              </div>
              
              <div className="flex gap-3">
                <button
                  onClick={handleDetectVariables}
                  className="px-6 py-2 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  检测变量
                </button>
                <button
                  onClick={clearBatchRename}
                  className="px-6 py-2 bg-slate-700 rounded-lg font-medium hover:bg-slate-600 transition-colors"
                >
                  清空
                </button>
              </div>
            </div>

            {batchRenameItems.length > 0 && (
              <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold flex items-center gap-2">
                    <RefreshCw className="w-5 h-5 text-indigo-400" />
                    待重命名变量
                  </h2>
                  <button
                    onClick={handleBatchRename}
                    className="px-6 py-2 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg font-medium hover:opacity-90 transition-opacity"
                  >
                    执行重命名
                  </button>
                </div>
                
                <div className="space-y-2">
                  {batchRenameItems.map(item => (
                    <div
                      key={item.id}
                      className="flex items-center gap-4 p-3 bg-slate-700/30 rounded-lg"
                    >
                      <span className={`text-xs px-2 py-1 rounded ${
                        item.type === 'function' ? 'bg-blue-500/20 text-blue-400' :
                        item.type === 'class' ? 'bg-purple-500/20 text-purple-400' :
                        item.type === 'constant' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-slate-600/50 text-slate-300'
                      }`}>
                        {item.type}
                      </span>
                      
                      <div className="flex-1 font-mono text-sm">
                        <span className="text-red-400 line-through">{item.oldName}</span>
                        <span className="mx-2 text-slate-500">→</span>
                        <input
                          type="text"
                          value={item.newName}
                          onChange={e => updateBatchRenameItem(item.id, { newName: e.target.value })}
                          className="px-2 py-1 bg-slate-800 border border-slate-600 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500 w-48"
                        />
                      </div>
                      
                      <span className="text-sm text-slate-400">
                        {item.occurrences} 处
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {batchRenameResult && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50"
              >
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold flex items-center gap-2">
                    <Check className="w-5 h-5 text-green-400" />
                    重命名结果
                  </h2>
                  <div className="flex gap-2">
                    <button
                      onClick={() => copyResult(batchRenameResult.modifiedCode)}
                      className="px-4 py-2 bg-slate-700 rounded-lg font-medium hover:bg-slate-600 transition-colors flex items-center gap-2"
                    >
                      {copiedResult ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                      复制代码
                    </button>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div className="p-3 bg-green-500/20 rounded-lg text-center">
                    <div className="text-2xl font-bold text-green-400">{batchRenameResult.totalRenamed}</div>
                    <div className="text-sm text-slate-400">已重命名</div>
                  </div>
                  <div className="p-3 bg-orange-500/20 rounded-lg text-center">
                    <div className="text-2xl font-bold text-orange-400">{batchRenameResult.totalSkipped}</div>
                    <div className="text-sm text-slate-400">已跳过</div>
                  </div>
                </div>
                
                <div className="bg-slate-900/50 rounded-xl p-4 max-h-64 overflow-auto">
                  <pre className="text-sm font-mono whitespace-pre-wrap">{batchRenameResult.modifiedCode}</pre>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}

        {activeTab === 'conflicts' && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="grid grid-cols-1 lg:grid-cols-2 gap-6"
          >
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-indigo-400" />
                冲突检测
              </h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">待检测名称</label>
                  <input
                    type="text"
                    value={conflictCheckName}
                    onChange={e => setConflictCheckName(e.target.value)}
                    placeholder="输入变量或函数名"
                    className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">代码上下文（可选）</label>
                  <textarea
                    value={conflictCheckCode}
                    onChange={e => setConflictCheckCode(e.target.value)}
                    placeholder="粘贴代码上下文以检测作用域冲突"
                    className="w-full h-32 px-4 py-3 bg-slate-900/50 border border-slate-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-sm"
                  />
                </div>
                
                <div className="flex gap-3">
                  <button
                    onClick={handleCheckConflicts}
                    className="px-6 py-2 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
                  >
                    <AlertTriangle className="w-4 h-4" />
                    检测冲突
                  </button>
                  <button
                    onClick={clearConflictResult}
                    className="px-6 py-2 bg-slate-700 rounded-lg font-medium hover:bg-slate-600 transition-colors"
                  >
                    清空
                  </button>
                </div>
              </div>
            </div>

            <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-indigo-400" />
                检测结果
              </h2>
              
              {!conflictCheckResult ? (
                <div className="text-center py-12 text-slate-400">
                  <AlertTriangle className="w-16 h-16 mx-auto mb-4 opacity-30" />
                  <p>输入名称并点击检测</p>
                </div>
              ) : conflictCheckResult.hasConflict ? (
                <div className="space-y-4">
                  <div className="p-4 bg-red-500/20 border border-red-500/30 rounded-xl">
                    <div className="flex items-center gap-2 text-red-400 font-medium mb-2">
                      <AlertTriangle className="w-5 h-5" />
                      检测到 {conflictCheckResult.conflicts.length} 个冲突
                    </div>
                    <div className="space-y-2">
                      {conflictCheckResult.conflicts.map((conflict, index) => (
                        <div key={index} className="text-sm text-slate-300">
                          <span className={`px-2 py-0.5 rounded text-xs mr-2 ${
                            conflict.type === 'keyword' ? 'bg-orange-500/20 text-orange-400' :
                            conflict.type === 'variable' ? 'bg-blue-500/20 text-blue-400' :
                            'bg-purple-500/20 text-purple-400'
                          }`}>
                            {conflict.type}
                          </span>
                          <code className="font-mono">{conflict.name}</code>
                          <span className="text-slate-400 ml-2">- {conflict.suggestion}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  {conflictCheckResult.suggestions.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium text-slate-300 mb-2">建议的替代名称</h3>
                      <div className="flex flex-wrap gap-2">
                        {conflictCheckResult.suggestions.map((suggestion, index) => (
                          <button
                            key={index}
                            onClick={() => setConflictCheckName(suggestion)}
                            className="px-3 py-1 bg-slate-700 rounded-lg text-sm hover:bg-slate-600 transition-colors font-mono"
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-12">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-500/20 flex items-center justify-center">
                    <Check className="w-8 h-8 text-green-400" />
                  </div>
                  <p className="text-green-400 font-medium">未检测到冲突</p>
                  <p className="text-slate-400 text-sm mt-1">该名称可以安全使用</p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
