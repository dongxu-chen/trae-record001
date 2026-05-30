import React, { useState } from 'react';
import { X, Plus, Trash2, Play, Code, AlertTriangle, Shield, Eye, EyeOff } from 'lucide-react';
import { CustomAggregation, AlertRule, PermissionConfig, DataRow } from '@/types';
import { validateCustomAggregation } from '@/utils/customAggregations';
import { getConditionLabel, getLevelColor } from '@/utils/alertRules';
import { getRoleLabel, getRolePermissions, formatHiddenRowKey } from '@/utils/permissions';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  customAggregations: CustomAggregation[];
  alertRules: AlertRule[];
  permissions: PermissionConfig;
  data: DataRow[];
  onAddCustomAggregation: (agg: CustomAggregation) => void;
  onUpdateCustomAggregation: (id: string, updates: Partial<CustomAggregation>) => void;
  onRemoveCustomAggregation: (id: string) => void;
  onAddAlertRule: (rule: AlertRule) => void;
  onUpdateAlertRule: (id: string, updates: Partial<AlertRule>) => void;
  onRemoveAlertRule: (id: string) => void;
  onUpdatePermissions: (updates: Partial<PermissionConfig>) => void;
}

type TabType = 'aggregations' | 'alerts' | 'permissions';

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  customAggregations,
  alertRules,
  permissions,
  data,
  onAddCustomAggregation,
  onUpdateCustomAggregation,
  onRemoveCustomAggregation,
  onAddAlertRule,
  onUpdateAlertRule,
  onRemoveAlertRule,
  onUpdatePermissions,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('aggregations');
  const [editingAgg, setEditingAgg] = useState<CustomAggregation | null>(null);
  const [editingAlert, setEditingAlert] = useState<AlertRule | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);

  if (!isOpen) return null;

  const tabs: { id: TabType; label: string; icon: React.ReactNode }[] = [
    { id: 'aggregations', label: '自定义聚合', icon: <Code size={18} /> },
    { id: 'alerts', label: '数据预警', icon: <AlertTriangle size={18} /> },
    { id: 'permissions', label: '权限控制', icon: <Shield size={18} /> },
  ];

  const handleSaveAggregation = () => {
    if (!editingAgg) return;

    const validation = validateCustomAggregation(editingAgg.code);
    if (!validation.valid) {
      setTestResult(`错误: ${validation.error}`);
      return;
    }

    if (editingAgg.id.startsWith('new_')) {
      onAddCustomAggregation({
        ...editingAgg,
        id: `custom_${Date.now()}`,
      });
    } else {
      onUpdateCustomAggregation(editingAgg.id, editingAgg);
    }

    setEditingAgg(null);
    setTestResult(null);
  };

  const handleTestAggregation = () => {
    if (!editingAgg) return;

    const validation = validateCustomAggregation(editingAgg.code);
    if (validation.valid) {
      setTestResult('✅ 代码验证通过！');
    } else {
      setTestResult(`❌ 验证失败: ${validation.error}`);
    }
  };

  const handleSaveAlertRule = () => {
    if (!editingAlert) return;

    if (editingAlert.id.startsWith('new_')) {
      onAddAlertRule({
        ...editingAlert,
        id: `alert_${Date.now()}`,
      });
    } else {
      onUpdateAlertRule(editingAlert.id, editingAlert);
    }

    setEditingAlert(null);
  };

  const measureFields = data.length > 0
    ? Object.entries(data[0])
        .filter(([_, v]) => typeof v === 'number')
        .map(([k]) => k)
    : [];

  const allRowValues = (() => {
    const values: { field: string; value: string; key: string }[] = [];
    const fieldSet = new Set<string>();
    
    data.forEach(row => {
      Object.entries(row).forEach(([field, value]) => {
        if (typeof value === 'string') {
          const key = formatHiddenRowKey(field, value);
          if (!fieldSet.has(key)) {
            fieldSet.add(key);
            values.push({ field, value, key });
          }
        }
      });
    });
    
    return values.slice(0, 100);
  })();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      <div className="relative w-full max-w-4xl max-h-[85vh] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-xl font-semibold text-gray-800">系统设置</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="flex border-b border-gray-100">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-colors
                ${activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
                }
              `}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-auto p-6">
          {activeTab === 'aggregations' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-medium text-gray-700">自定义聚合函数</h3>
                <button
                  onClick={() =>
                    setEditingAgg({
                      id: 'new_',
                      name: '新函数',
                      code: `// 可用变量: values(数值数组), data(原始数据), field(字段名)
return values.reduce((a, b) => a + b, 0);`.trim(),
                      description: '',
                    })
                  }
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-primary-500 rounded-lg hover:bg-primary-600 transition-colors"
                >
                  <Plus size={16} />
                  新建
                </button>
              </div>

              {editingAgg ? (
                <div className="bg-gray-50 rounded-xl p-4 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        函数名称
                      </label>
                      <input
                        type="text"
                        value={editingAgg.name}
                        onChange={(e) =>
                          setEditingAgg({ ...editingAgg, name: e.target.value })
                        }
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-primary-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        描述
                      </label>
                      <input
                        type="text"
                        value={editingAgg.description || ''}
                        onChange={(e) =>
                          setEditingAgg({ ...editingAgg, description: e.target.value })
                        }
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-primary-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      JavaScript 代码
                    </label>
                    <textarea
                      value={editingAgg.code}
                      onChange={(e) =>
                        setEditingAgg({ ...editingAgg, code: e.target.value })
                      }
                      rows={10}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-primary-500 font-mono text-sm"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      可用变量: <code className="bg-gray-100 px-1 rounded">values</code> (数值数组),{' '}
                      <code className="bg-gray-100 px-1 rounded">data</code> (原始数据行数组),{' '}
                      <code className="bg-gray-100 px-1 rounded">field</code> (当前字段名)
                    </p>
                  </div>

                  {testResult && (
                    <div
                      className={`p-3 rounded-lg text-sm ${
                        testResult.startsWith('✅')
                          ? 'bg-green-50 text-green-700'
                          : 'bg-red-50 text-red-700'
                      }`}
                    >
                      {testResult}
                    </div>
                  )}

                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => {
                        setEditingAgg(null);
                        setTestResult(null);
                      }}
                      className="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                    >
                      取消
                    </button>
                    <button
                      onClick={handleTestAggregation}
                      className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
                    >
                      <Play size={14} />
                      测试
                    </button>
                    <button
                      onClick={handleSaveAggregation}
                      className="px-4 py-2 text-sm font-medium text-white bg-primary-500 rounded-lg hover:bg-primary-600 transition-colors"
                    >
                      保存
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  {customAggregations.map((agg) => (
                    <div
                      key={agg.id}
                      className="flex items-center justify-between p-4 bg-white border border-gray-100 rounded-xl hover:shadow-md transition-all"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <Code size={16} className="text-primary-500" />
                          <span className="font-medium text-gray-800">{agg.name}</span>
                          {agg.description && (
                            <span className="text-sm text-gray-500">
                              - {agg.description}
                            </span>
                          )}
                        </div>
                        <pre className="mt-2 p-2 bg-gray-50 rounded text-xs text-gray-600 overflow-x-auto max-h-16">
                          {agg.code}
                        </pre>
                      </div>
                      <div className="flex items-center gap-2 ml-4">
                        <button
                          onClick={() => setEditingAgg({ ...agg })}
                          className="p-2 text-gray-400 hover:text-primary-500 hover:bg-primary-50 rounded-lg transition-colors"
                        >
                          <Code size={16} />
                        </button>
                        <button
                          onClick={() => onRemoveCustomAggregation(agg.id)}
                          className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'alerts' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-medium text-gray-700">数据预警规则</h3>
                <button
                  onClick={() =>
                    setEditingAlert({
                      id: 'new_',
                      name: '新规则',
                      field: measureFields[0] || '',
                      condition: 'gt',
                      value1: 0,
                      level: 'warning',
                      enabled: true,
                    })
                  }
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-primary-500 rounded-lg hover:bg-primary-600 transition-colors"
                >
                  <Plus size={16} />
                  新建
                </button>
              </div>

              {editingAlert ? (
                <div className="bg-gray-50 rounded-xl p-4 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        规则名称
                      </label>
                      <input
                        type="text"
                        value={editingAlert.name}
                        onChange={(e) =>
                          setEditingAlert({ ...editingAlert, name: e.target.value })
                        }
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-primary-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        字段
                      </label>
                      <select
                        value={editingAlert.field}
                        onChange={(e) =>
                          setEditingAlert({ ...editingAlert, field: e.target.value })
                        }
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-primary-500"
                      >
                        {measureFields.map((f) => (
                          <option key={f} value={f}>
                            {f}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        条件
                      </label>
                      <select
                        value={editingAlert.condition}
                        onChange={(e) =>
                          setEditingAlert({
                            ...editingAlert,
                            condition: e.target.value as any,
                          })
                        }
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-primary-500"
                      >
                        {(['gt', 'gte', 'lt', 'lte', 'eq', 'ne', 'between'] as const).map(
                          (c) => (
                            <option key={c} value={c}>
                              {getConditionLabel(c)}
                            </option>
                          )
                        )}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        阈值1
                      </label>
                      <input
                        type="number"
                        value={editingAlert.value1}
                        onChange={(e) =>
                          setEditingAlert({
                            ...editingAlert,
                            value1: Number(e.target.value),
                          })
                        }
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-primary-500"
                      />
                    </div>
                    {editingAlert.condition === 'between' && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          阈值2
                        </label>
                        <input
                          type="number"
                          value={editingAlert.value2 || 0}
                          onChange={(e) =>
                            setEditingAlert({
                              ...editingAlert,
                              value2: Number(e.target.value),
                            })
                          }
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-primary-500"
                        />
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        预警等级
                      </label>
                      <select
                        value={editingAlert.level}
                        onChange={(e) =>
                          setEditingAlert({
                            ...editingAlert,
                            level: e.target.value as any,
                          })
                        }
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-primary-500"
                      >
                        <option value="info">信息 (蓝色)</option>
                        <option value="warning">警告 (黄色)</option>
                        <option value="danger">危险 (红色)</option>
                      </select>
                    </div>
                    <div className="flex items-end">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={editingAlert.enabled}
                          onChange={(e) =>
                            setEditingAlert({
                              ...editingAlert,
                              enabled: e.target.checked,
                            })
                          }
                          className="w-4 h-4 text-primary-500 rounded focus:ring-primary-500"
                        />
                        <span className="text-sm text-gray-700">启用规则</span>
                      </label>
                    </div>
                  </div>

                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => setEditingAlert(null)}
                      className="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                    >
                      取消
                    </button>
                    <button
                      onClick={handleSaveAlertRule}
                      className="px-4 py-2 text-sm font-medium text-white bg-primary-500 rounded-lg hover:bg-primary-600 transition-colors"
                    >
                      保存
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  {alertRules.map((rule) => (
                    <div
                      key={rule.id}
                      className="flex items-center justify-between p-4 bg-white border border-gray-100 rounded-xl hover:shadow-md transition-all"
                    >
                      <div className="flex items-center gap-4">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: getLevelColor(rule.level) }}
                        />
                        <div>
                          <div className="font-medium text-gray-800">{rule.name}</div>
                          <div className="text-sm text-gray-500">
                            {rule.field} {getConditionLabel(rule.condition)} {rule.value1}
                            {rule.condition === 'between' && ` - ${rule.value2}`}
                            {!rule.enabled && (
                              <span className="ml-2 text-gray-400">(已禁用)</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={rule.enabled}
                            onChange={(e) =>
                              onUpdateAlertRule(rule.id, { enabled: e.target.checked })
                            }
                            className="w-4 h-4 text-primary-500 rounded focus:ring-primary-500"
                          />
                        </label>
                        <button
                          onClick={() => setEditingAlert({ ...rule })}
                          className="p-2 text-gray-400 hover:text-primary-500 hover:bg-primary-50 rounded-lg transition-colors"
                        >
                          <Code size={16} />
                        </button>
                        <button
                          onClick={() => onRemoveAlertRule(rule.id)}
                          className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'permissions' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium text-gray-700 mb-3">角色权限</h3>
                <div className="grid grid-cols-3 gap-4">
                  {(['admin', 'user', 'viewer'] as const).map((role) => {
                    const rolePerms = getRolePermissions(role);
                    return (
                      <button
                        key={role}
                        onClick={() => onUpdatePermissions({ role })}
                        className={`
                          p-4 rounded-xl border-2 text-left transition-all
                          ${permissions.role === role
                            ? 'border-primary-500 bg-primary-50'
                            : 'border-gray-100 hover:border-gray-200'
                          }
                        `}
                      >
                        <div className="font-medium text-gray-800">
                          {getRoleLabel(role)}
                        </div>
                        <div className="mt-2 space-y-1 text-xs text-gray-500">
                          <div className={rolePerms.canEditConfig ? 'text-green-600' : 'text-gray-400'}>
                            {rolePerms.canEditConfig ? '✓' : '✗'} 编辑配置
                          </div>
                          <div className={rolePerms.canExportData ? 'text-green-600' : 'text-gray-400'}>
                            {rolePerms.canExportData ? '✓' : '✗'} 导出数据
                          </div>
                          <div className={rolePerms.canViewSensitiveData ? 'text-green-600' : 'text-gray-400'}>
                            {rolePerms.canViewSensitiveData ? '✓' : '✗'} 查看敏感数据
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <h3 className="text-lg font-medium text-gray-700 mb-3">隐藏字段</h3>
                <div className="flex flex-wrap gap-2">
                  {data.length > 0 &&
                    Object.keys(data[0]).map((field) => {
                      const isHidden = permissions.hiddenFields.includes(field);
                      return (
                        <button
                          key={field}
                          onClick={() => {
                            if (isHidden) {
                              onUpdatePermissions({
                                hiddenFields: permissions.hiddenFields.filter(
                                  (f) => f !== field
                                ),
                              });
                            } else {
                              onUpdatePermissions({
                                hiddenFields: [...permissions.hiddenFields, field],
                              });
                            }
                          }}
                          className={`
                            flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-all
                            ${isHidden
                              ? 'bg-red-100 text-red-700'
                              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                            }
                          `}
                        >
                          {isHidden ? <EyeOff size={14} /> : <Eye size={14} />}
                          {field}
                        </button>
                      );
                    })}
                </div>
              </div>

              <div>
                <h3 className="text-lg font-medium text-gray-700 mb-3">
                  隐藏行（点击切换）
                </h3>
                <div className="max-h-48 overflow-auto border border-gray-100 rounded-lg">
                  {allRowValues.map((item) => {
                    const isHidden = permissions.hiddenRows.includes(item.key);
                    return (
                      <button
                        key={item.key}
                        onClick={() => {
                          if (isHidden) {
                            onUpdatePermissions({
                              hiddenRows: permissions.hiddenRows.filter(
                                (k) => k !== item.key
                              ),
                            });
                          } else {
                            onUpdatePermissions({
                              hiddenRows: [...permissions.hiddenRows, item.key],
                            });
                          }
                        }}
                        className={`
                          w-full flex items-center justify-between px-4 py-2 text-sm transition-all
                          ${isHidden ? 'bg-red-50' : 'hover:bg-gray-50'}
                          border-b border-gray-50 last:border-b-0
                        `}
                      >
                        <span>
                          <span className="text-gray-500">{item.field}:</span>{' '}
                          <span className={isHidden ? 'text-red-700 line-through' : 'text-gray-700'}>
                            {item.value}
                          </span>
                        </span>
                        {isHidden ? (
                          <EyeOff size={14} className="text-red-500" />
                        ) : (
                          <Eye size={14} className="text-gray-400" />
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
