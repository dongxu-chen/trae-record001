import { useState } from 'react';
import { AutomationRule, RuleCondition, RuleAction } from '@/types';
import { defaultRules, getConditionLabel, getActionLabel } from '@/utils/automationEngine';
import { Switch } from '@headlessui/react';

const AutomationRules = () => {
  const [rules, setRules] = useState<AutomationRule[]>(defaultRules);
  const [selectedRule, setSelectedRule] = useState<AutomationRule | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const toggleRule = (ruleId: string) => {
    setRules(rules.map(rule =>
      rule._id === ruleId ? { ...rule, enabled: !rule.enabled, updatedAt: new Date().toISOString() } : rule
    ));
  };

  const deleteRule = (ruleId: string) => {
    setRules(rules.filter(rule => rule._id !== ruleId));
    if (selectedRule?._id === ruleId) {
      setSelectedRule(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">自动化规则</h1>
              <p className="mt-1 text-sm text-gray-500">配置规则，实现任务自动处理</p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              + 创建规则
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="p-4 border-b border-gray-100">
                <h2 className="font-semibold text-gray-900">规则列表</h2>
              </div>
              <div className="divide-y divide-gray-100">
                {rules.map(rule => (
                  <div
                    key={rule._id}
                    className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${
                      selectedRule?._id === rule._id ? 'bg-blue-50' : ''
                    }`}
                    onClick={() => setSelectedRule(rule)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <h3 className={`font-medium truncate ${rule.enabled ? 'text-gray-900' : 'text-gray-400'}`}>
                          {rule.name}
                        </h3>
                        <p className="text-sm text-gray-500 truncate">{rule.description}</p>
                      </div>
                      <Switch
                        checked={rule.enabled}
                        onChange={(e) => {
                          e.stopPropagation();
                          toggleRule(rule._id);
                        }}
                        className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                          rule.enabled ? 'bg-blue-600' : 'bg-gray-200'
                        }`}
                      >
                        <span className="sr-only">启用规则</span>
                        <span
                          className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                            rule.enabled ? 'translate-x-4' : 'translate-x-0'
                          }`}
                        />
                      </Switch>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="lg:col-span-2">
            {selectedRule ? (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                <div className="p-6 border-b border-gray-100">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900">{selectedRule.name}</h2>
                      <p className="text-sm text-gray-500 mt-1">{selectedRule.description}</p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => deleteRule(selectedRule._id)}
                        className="px-3 py-1.5 text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
                      >
                        删除
                      </button>
                    </div>
                  </div>
                </div>

                <div className="p-6 space-y-6">
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2">
                      <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
                      触发条件
                    </h3>
                    <div className="space-y-3">
                      {selectedRule.conditions.map((condition, index) => (
                        <div
                          key={index}
                          className="flex items-center gap-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg"
                        >
                          <span className="w-6 h-6 bg-yellow-500 text-white text-sm rounded-full flex items-center justify-center">
                            {index + 1}
                          </span>
                          <span className="font-medium text-gray-900">{getConditionLabel(condition.type)}</span>
                          {condition.value && (
                            <span className="text-sm text-gray-500">= {condition.value}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2">
                      <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                      执行动作
                    </h3>
                    <div className="space-y-3">
                      {selectedRule.actions.map((action, index) => (
                        <div
                          key={index}
                          className="flex items-center gap-3 p-3 bg-green-50 border border-green-200 rounded-lg"
                        >
                          <span className="w-6 h-6 bg-green-500 text-white text-sm rounded-full flex items-center justify-center">
                            {index + 1}
                          </span>
                          <span className="font-medium text-gray-900">{getActionLabel(action.type)}</span>
                          <span className="text-sm text-gray-500">→ {String(action.value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="pt-4 border-t border-gray-100">
                    <h3 className="text-sm font-medium text-gray-500 mb-2">规则信息</h3>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">创建时间：</span>
                        <span className="text-gray-900">
                          {new Date(selectedRule.createdAt).toLocaleString('zh-CN')}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500">更新时间：</span>
                        <span className="text-gray-900">
                          {new Date(selectedRule.updatedAt).toLocaleString('zh-CN')}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">选择一个规则查看详情</h3>
                <p className="text-gray-500">或者点击创建按钮添加新的自动化规则</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default AutomationRules;
