import { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Play, Search, Check, X, FileText } from 'lucide-react';
import { useAppStore } from '@/store/appStore';
import { rulesApi } from '@/lib/api';
import type { DataQualityRule, RuleType, RuleConfig } from '../../shared/types.js';

const ruleTypeLabels: Record<RuleType, string> = {
  null_check: '非空校验',
  uniqueness: '唯一性校验',
  value_range: '值域范围校验',
  dependency: '外键依赖校验',
};

const ruleTypeColors: Record<RuleType, string> = {
  null_check: 'bg-blue-100 text-blue-700',
  uniqueness: 'bg-purple-100 text-purple-700',
  value_range: 'bg-green-100 text-green-700',
  dependency: 'bg-orange-100 text-orange-700',
};

export default function Rules() {
  const { rules, fetchRules } = useAppStore();
  const [showModal, setShowModal] = useState(false);
  const [editingRule, setEditingRule] = useState<DataQualityRule | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [testing, setTesting] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);

  const [formData, setFormData] = useState<{
    name: string;
    description: string;
    type: RuleType;
    dataSource: string;
    tableName: string;
    columnName: string;
    config: RuleConfig;
  }>({
    name: '',
    description: '',
    type: 'null_check',
    dataSource: 'default',
    tableName: '',
    columnName: '',
    config: {},
  });

  useEffect(() => {
    void fetchRules();
  }, [fetchRules]);

  const filteredRules = rules.filter(
    (rule) =>
      rule.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      rule.tableName.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSubmit = async () => {
    try {
      if (editingRule) {
        await rulesApi.update(editingRule.id, formData);
      } else {
        await rulesApi.create({ ...formData, enabled: true });
      }
      await fetchRules();
      setShowModal(false);
      resetForm();
    } catch (error) {
      console.error('Failed to save rule:', error);
    }
  };

  const handleEdit = (rule: DataQualityRule) => {
    setEditingRule(rule);
    setFormData({
      name: rule.name,
      description: rule.description,
      type: rule.type,
      dataSource: rule.dataSource,
      tableName: rule.tableName,
      columnName: rule.columnName,
      config: rule.config,
    });
    setShowModal(true);
  };

  const handleDelete = async (id: string) => {
    if (confirm('确定要删除这条规则吗？')) {
      await rulesApi.delete(id);
      await fetchRules();
    }
  };

  const handleTest = async (id: string) => {
    setTesting(id);
    setTestResult(null);
    try {
      const result = await rulesApi.test(id);
      setTestResult(
        `测试完成：共 ${result.totalRecords} 条记录，发现 ${result.failedRecords} 条问题`
      );
    } catch (error) {
      setTestResult('测试失败');
    } finally {
      setTesting(null);
      setTimeout(() => setTestResult(null), 3000);
    }
  };

  const handleToggleEnabled = async (rule: DataQualityRule) => {
    await rulesApi.update(rule.id, { enabled: !rule.enabled });
    await fetchRules();
  };

  const resetForm = () => {
    setEditingRule(null);
    setFormData({
      name: '',
      description: '',
      type: 'null_check',
      dataSource: 'default',
      tableName: '',
      columnName: '',
      config: {},
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="搜索规则..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
        <button
          onClick={() => {
            resetForm();
            setShowModal(true);
          }}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          <Plus className="w-5 h-5" />
          新建规则
        </button>
      </div>

      {testResult && (
        <div className="p-4 bg-blue-50 text-blue-700 rounded-lg flex items-center gap-2">
          <FileText className="w-5 h-5" />
          {testResult}
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                规则名称
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                类型
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                表/列
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                状态
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                创建时间
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                操作
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filteredRules.map((rule) => (
              <tr key={rule.id} className="hover:bg-gray-50">
                <td className="px-6 py-4">
                  <div className="font-medium text-gray-900">{rule.name}</div>
                  <div className="text-sm text-gray-500">{rule.description}</div>
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${ruleTypeColors[rule.type]}`}>
                    {ruleTypeLabels[rule.type]}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-900">{rule.tableName}</div>
                  <div className="text-xs text-gray-500">{rule.columnName}</div>
                </td>
                <td className="px-6 py-4">
                  <button
                    onClick={() => handleToggleEnabled(rule)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      rule.enabled ? 'bg-primary-600' : 'bg-gray-200'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        rule.enabled ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {new Date(rule.createdAt).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => handleTest(rule.id)}
                      disabled={testing === rule.id}
                      className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      title="测试规则"
                    >
                      <Play className={`w-4 h-4 ${testing === rule.id ? 'animate-pulse' : ''}`} />
                    </button>
                    <button
                      onClick={() => handleEdit(rule)}
                      className="p-2 text-gray-500 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                      title="编辑"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(rule.id)}
                      className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="删除"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredRules.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <FileText className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p>暂无规则数据</p>
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b">
              <h3 className="text-lg font-semibold text-gray-900">
                {editingRule ? '编辑规则' : '新建规则'}
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="p-2 text-gray-500 hover:text-gray-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">规则名称</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="输入规则名称"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">规则描述</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
                  rows={2}
                  placeholder="输入规则描述"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">规则类型</label>
                <select
                  value={formData.type}
                  onChange={(e) =>
                    setFormData({ ...formData, type: e.target.value as RuleType, config: {} })
                  }
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="null_check">非空校验</option>
                  <option value="uniqueness">唯一性校验</option>
                  <option value="value_range">值域范围校验</option>
                  <option value="dependency">外键依赖校验</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">表名</label>
                <input
                  type="text"
                  value={formData.tableName}
                  onChange={(e) => setFormData({ ...formData, tableName: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="例如: users"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">列名</label>
                <input
                  type="text"
                  value={formData.columnName}
                  onChange={(e) => setFormData({ ...formData, columnName: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="例如: email"
                />
              </div>

              {formData.type === 'value_range' && (
                <div className="p-4 bg-gray-50 rounded-lg space-y-3">
                  <label className="block text-sm font-medium text-gray-700">值域配置</label>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">最小值</label>
                      <input
                        type="number"
                        value={formData.config.valueRange?.min ?? ''}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            config: {
                              ...formData.config,
                              valueRange: {
                                ...formData.config.valueRange,
                                min: e.target.value ? Number(e.target.value) : undefined,
                              },
                            },
                          })
                        }
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">最大值</label>
                      <input
                        type="number"
                        value={formData.config.valueRange?.max ?? ''}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            config: {
                              ...formData.config,
                              valueRange: {
                                ...formData.config.valueRange,
                                max: e.target.value ? Number(e.target.value) : undefined,
                              },
                            },
                          })
                        }
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </div>
                  </div>
                </div>
              )}

              {formData.type === 'dependency' && (
                <div className="p-4 bg-gray-50 rounded-lg space-y-3">
                  <label className="block text-sm font-medium text-gray-700">外键配置</label>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">目标表</label>
                    <input
                      type="text"
                      value={formData.config.dependency?.targetTable ?? ''}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          config: {
                            ...formData.config,
                            dependency: {
                              ...formData.config.dependency,
                              sourceColumn: formData.columnName,
                              targetTable: e.target.value,
                              targetColumn: formData.config.dependency?.targetColumn ?? '',
                            },
                          },
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                      placeholder="例如: departments"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">目标列</label>
                    <input
                      type="text"
                      value={formData.config.dependency?.targetColumn ?? ''}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          config: {
                            ...formData.config,
                            dependency: {
                              ...formData.config.dependency,
                              sourceColumn: formData.columnName,
                              targetTable: formData.config.dependency?.targetTable ?? '',
                              targetColumn: e.target.value,
                            },
                          },
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                      placeholder="例如: id"
                    />
                  </div>
                </div>
              )}
            </div>
            <div className="flex items-center justify-end gap-3 p-6 border-t">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleSubmit}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
              >
                <Check className="w-4 h-4" />
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
