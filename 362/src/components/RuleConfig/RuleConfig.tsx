import React, { useState } from 'react';
import { Settings, Copy, CircleDot, AlertTriangle, Sliders, ChevronDown, ChevronUp } from 'lucide-react';
import { useDataStore } from '../../store/useDataStore';
import { Switch } from '../common/Switch';
import { FILL_METHODS, OUTLIER_METHODS, NORMALIZE_METHODS } from '../../types';
import type { FillMethod, OutlierMethod, NormalizeMethod } from '../../types';

interface RuleConfigProps {
  className?: string;
}

type AccordionPanel = 'duplicates' | 'missing' | 'outliers' | 'normalize' | null;

export const RuleConfig: React.FC<RuleConfigProps> = ({ className = '' }) => {
  const { uploadedData, cleaningRules, setCleaningRules, isCleaning } = useDataStore();
  const [expandedPanel, setExpandedPanel] = useState<AccordionPanel>('duplicates');

  const togglePanel = (panel: AccordionPanel) => {
    setExpandedPanel(expandedPanel === panel ? null : panel);
  };

  const renderPanelHeader = (
    id: AccordionPanel,
    icon: React.ReactNode,
    title: string,
    enabled: boolean
  ) => (
    <button
      className="accordion-trigger"
      onClick={() => togglePanel(id)}
      disabled={!uploadedData}
    >
      <div className="flex items-center gap-3">
        <div className={`p-1.5 rounded-md ${enabled ? 'bg-primary-500/20 text-primary-400' : 'bg-bg-700 text-bg-500'}`}>
          {icon}
        </div>
        <span className={enabled ? 'text-bg-100' : 'text-bg-500'}>{title}</span>
      </div>
      <div className="flex items-center gap-3">
        <Switch
          checked={enabled}
          onChange={(checked) => {
            if (id === 'duplicates') {
              setCleaningRules({ removeDuplicates: { ...cleaningRules.removeDuplicates, enabled: checked } });
            } else if (id === 'missing') {
              setCleaningRules({ handleMissing: { ...cleaningRules.handleMissing, enabled: checked } });
            } else if (id === 'outliers') {
              setCleaningRules({ detectOutliers: { ...cleaningRules.detectOutliers, enabled: checked } });
            } else if (id === 'normalize') {
              setCleaningRules({ normalize: { ...cleaningRules.normalize, enabled: checked } });
            }
          }}
          disabled={!uploadedData || isCleaning}
        />
        {expandedPanel === id ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
      </div>
    </button>
  );

  if (!uploadedData) {
    return (
      <div className={`card ${className}`}>
        <div className="card-header">
          <h3 className="font-semibold text-bg-100 flex items-center gap-2">
            <Settings size={18} className="text-primary-400" />
            清洗规则配置
          </h3>
        </div>
        <div className="card-body flex items-center justify-center h-64">
          <p className="text-bg-500">请先上传数据文件以配置清洗规则</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`card ${className}`}>
      <div className="card-header">
        <h3 className="font-semibold text-bg-100 flex items-center gap-2">
          <Settings size={18} className="text-primary-400" />
          清洗规则配置
        </h3>
      </div>

      <div className="divide-y divide-bg-700">
        <div className="accordion-item">
          {renderPanelHeader('duplicates', <Copy size={16} />, '重复值处理', cleaningRules.removeDuplicates.enabled)}
          {expandedPanel === 'duplicates' && cleaningRules.removeDuplicates.enabled && (
            <div className="p-4 space-y-4 animate-slide-down">
              <div>
                <label className="block text-sm text-bg-300 mb-2">保留方式</label>
                <select
                  className="select"
                  value={cleaningRules.removeDuplicates.keep || 'first'}
                  onChange={(e) =>
                    setCleaningRules({
                      removeDuplicates: {
                        ...cleaningRules.removeDuplicates,
                        keep: e.target.value as 'first' | 'last' | false,
                      },
                    })
                  }
                  disabled={isCleaning}
                >
                  <option value="first">保留第一条</option>
                  <option value="last">保留最后一条</option>
                  <option value="false">删除所有重复</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-bg-300 mb-2">检查列（可选，留空检查所有列）</label>
                <div className="flex flex-wrap gap-2">
                  {uploadedData.columns.map((col, idx) => (
                    <label key={idx} className="flex items-center gap-2 text-sm text-bg-200 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={cleaningRules.removeDuplicates.columns?.includes(col) || false}
                        onChange={(e) => {
                          const currentCols = cleaningRules.removeDuplicates.columns || [];
                          const newCols = e.target.checked
                            ? [...currentCols, col]
                            : currentCols.filter((c) => c !== col);
                          setCleaningRules({
                            removeDuplicates: {
                              ...cleaningRules.removeDuplicates,
                              columns: newCols.length > 0 ? newCols : undefined,
                            },
                          });
                        }}
                        disabled={isCleaning}
                        className="w-4 h-4 rounded border-bg-600 bg-bg-900 text-primary-500 focus:ring-primary-500"
                      />
                      {col}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="accordion-item">
          {renderPanelHeader('missing', <CircleDot size={16} />, '缺失值填充', cleaningRules.handleMissing.enabled)}
          {expandedPanel === 'missing' && cleaningRules.handleMissing.enabled && (
            <div className="p-4 space-y-4 animate-slide-down">
              <div>
                <label className="block text-sm text-bg-300 mb-2">默认填充方法</label>
                <select
                  className="select"
                  value={cleaningRules.handleMissing.defaultMethod}
                  onChange={(e) =>
                    setCleaningRules({
                      handleMissing: {
                        ...cleaningRules.handleMissing,
                        defaultMethod: e.target.value as FillMethod,
                      },
                    })
                  }
                  disabled={isCleaning}
                >
                  {FILL_METHODS.map((m) => (
                    <option key={m.value} value={m.value}>
                      {m.label} - {m.description}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-3">
                <p className="text-sm text-bg-400">各列配置（可选，未配置则使用默认方法）</p>
                {uploadedData.stats.columns
                  .filter((col) => col.missingCount > 0)
                  .map((col, idx) => (
                    <div key={idx} className="bg-bg-900 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-bg-200">{col.name}</span>
                        <span className="text-xs text-warning-400">
                          {col.missingCount} 个缺失值 ({col.missingPercent.toFixed(1)}%)
                        </span>
                      </div>
                      <div className="flex gap-2">
                        <select
                          className="select flex-1 text-sm"
                          value={cleaningRules.handleMissing.columns[col.name]?.method || cleaningRules.handleMissing.defaultMethod}
                          onChange={(e) =>
                            setCleaningRules({
                              handleMissing: {
                                ...cleaningRules.handleMissing,
                                columns: {
                                  ...cleaningRules.handleMissing.columns,
                                  [col.name]: {
                                    method: e.target.value as FillMethod,
                                    value: cleaningRules.handleMissing.columns[col.name]?.value,
                                  },
                                },
                              },
                            })
                          }
                          disabled={isCleaning}
                        >
                          {FILL_METHODS.map((m) => (
                            <option key={m.value} value={m.value}>
                              {m.label}
                            </option>
                          ))}
                        </select>
                        {cleaningRules.handleMissing.columns[col.name]?.method === 'constant' && (
                          <input
                            type="text"
                            placeholder="填充值"
                            className="input w-24 text-sm"
                            value={cleaningRules.handleMissing.columns[col.name]?.value || ''}
                            onChange={(e) =>
                              setCleaningRules({
                                handleMissing: {
                                  ...cleaningRules.handleMissing,
                                  columns: {
                                    ...cleaningRules.handleMissing.columns,
                                    [col.name]: {
                                      ...cleaningRules.handleMissing.columns[col.name],
                                      value: e.target.value,
                                    },
                                  },
                                },
                              })
                            }
                            disabled={isCleaning}
                          />
                        )}
                      </div>
                    </div>
                  ))}
                {uploadedData.stats.columns.filter((col) => col.missingCount > 0).length === 0 && (
                  <p className="text-sm text-success-400">✓ 没有检测到缺失值</p>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="accordion-item">
          {renderPanelHeader('outliers', <AlertTriangle size={16} />, '异常值检测', cleaningRules.detectOutliers.enabled)}
          {expandedPanel === 'outliers' && cleaningRules.detectOutliers.enabled && (
            <div className="p-4 space-y-4 animate-slide-down">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-bg-300 mb-2">默认检测方法</label>
                  <select
                    className="select"
                    value={cleaningRules.detectOutliers.defaultMethod}
                    onChange={(e) =>
                      setCleaningRules({
                        detectOutliers: {
                          ...cleaningRules.detectOutliers,
                          defaultMethod: e.target.value as OutlierMethod,
                        },
                      })
                    }
                    disabled={isCleaning}
                  >
                    {OUTLIER_METHODS.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-bg-300 mb-2">默认阈值</label>
                  <input
                    type="number"
                    step="0.1"
                    className="input"
                    value={cleaningRules.detectOutliers.defaultThreshold}
                    onChange={(e) =>
                      setCleaningRules({
                        detectOutliers: {
                          ...cleaningRules.detectOutliers,
                          defaultThreshold: parseFloat(e.target.value),
                        },
                      })
                    }
                    disabled={isCleaning}
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm text-bg-300 mb-2">处理方式</label>
                <div className="flex gap-2">
                  {(['remove', 'cap', 'mark'] as const).map((action) => (
                    <label key={action} className="flex items-center gap-2 text-sm text-bg-200 cursor-pointer">
                      <input
                        type="radio"
                        name="outlierAction"
                        value={action}
                        checked={Object.values(cleaningRules.detectOutliers.columns)[0]?.action === action || action === 'remove'}
                        onChange={() => {
                          const newColumns = { ...cleaningRules.detectOutliers.columns };
                          uploadedData.columns.forEach((col) => {
                            newColumns[col] = {
                              ...newColumns[col],
                              method: newColumns[col]?.method || cleaningRules.detectOutliers.defaultMethod,
                              threshold: newColumns[col]?.threshold || cleaningRules.detectOutliers.defaultThreshold,
                              action,
                            };
                          });
                          setCleaningRules({
                            detectOutliers: { ...cleaningRules.detectOutliers, columns: newColumns },
                          });
                        }}
                        disabled={isCleaning}
                        className="w-4 h-4 border-bg-600 bg-bg-900 text-primary-500 focus:ring-primary-500"
                      />
                      {action === 'remove' ? '删除' : action === 'cap' ? '盖帽' : '标记'}
                    </label>
                  ))}
                </div>
              </div>
              <div className="space-y-3">
                <p className="text-sm text-bg-400">各列配置（仅数值型列）</p>
                {uploadedData.stats.columns
                  .filter((col) => col.type === 'numeric')
                  .map((col, idx) => (
                    <div key={idx} className="bg-bg-900 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-bg-200">{col.name}</span>
                        <span className="text-xs text-bg-400">
                          范围: {col.min?.toFixed(2)} - {col.max?.toFixed(2)}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2">
                        <select
                          className="select text-sm"
                          value={cleaningRules.detectOutliers.columns[col.name]?.method || cleaningRules.detectOutliers.defaultMethod}
                          onChange={(e) =>
                            setCleaningRules({
                              detectOutliers: {
                                ...cleaningRules.detectOutliers,
                                columns: {
                                  ...cleaningRules.detectOutliers.columns,
                                  [col.name]: {
                                    method: e.target.value as OutlierMethod,
                                    threshold: cleaningRules.detectOutliers.columns[col.name]?.threshold || cleaningRules.detectOutliers.defaultThreshold,
                                    action: cleaningRules.detectOutliers.columns[col.name]?.action || 'remove',
                                  },
                                },
                              },
                            })
                          }
                          disabled={isCleaning}
                        >
                          {OUTLIER_METHODS.map((m) => (
                            <option key={m.value} value={m.value}>
                              {m.label}
                            </option>
                          ))}
                        </select>
                        <input
                          type="number"
                          step="0.1"
                          placeholder="阈值"
                          className="input text-sm"
                          value={cleaningRules.detectOutliers.columns[col.name]?.threshold || cleaningRules.detectOutliers.defaultThreshold}
                          onChange={(e) =>
                            setCleaningRules({
                              detectOutliers: {
                                ...cleaningRules.detectOutliers,
                                columns: {
                                  ...cleaningRules.detectOutliers.columns,
                                  [col.name]: {
                                    ...cleaningRules.detectOutliers.columns[col.name],
                                    threshold: parseFloat(e.target.value),
                                  },
                                },
                              },
                            })
                          }
                          disabled={isCleaning}
                        />
                        <select
                          className="select text-sm"
                          value={cleaningRules.detectOutliers.columns[col.name]?.action || 'remove'}
                          onChange={(e) =>
                            setCleaningRules({
                              detectOutliers: {
                                ...cleaningRules.detectOutliers,
                                columns: {
                                  ...cleaningRules.detectOutliers.columns,
                                  [col.name]: {
                                    ...cleaningRules.detectOutliers.columns[col.name],
                                    action: e.target.value as 'remove' | 'cap' | 'mark',
                                  },
                                },
                              },
                            })
                          }
                          disabled={isCleaning}
                        >
                          <option value="remove">删除</option>
                          <option value="cap">盖帽</option>
                          <option value="mark">标记</option>
                        </select>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>

        <div className="accordion-item">
          {renderPanelHeader('normalize', <Sliders size={16} />, '数据标准化', cleaningRules.normalize.enabled)}
          {expandedPanel === 'normalize' && cleaningRules.normalize.enabled && (
            <div className="p-4 space-y-4 animate-slide-down">
              <div>
                <label className="block text-sm text-bg-300 mb-2">默认标准化方法</label>
                <select
                  className="select"
                  value={cleaningRules.normalize.defaultMethod}
                  onChange={(e) =>
                    setCleaningRules({
                      normalize: {
                        ...cleaningRules.normalize,
                        defaultMethod: e.target.value as NormalizeMethod,
                      },
                    })
                  }
                  disabled={isCleaning}
                >
                  {NORMALIZE_METHODS.map((m) => (
                    <option key={m.value} value={m.value}>
                      {m.label} - {m.description}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-3">
                <p className="text-sm text-bg-400">各列配置（仅数值型列）</p>
                <div className="flex flex-wrap gap-2">
                  {uploadedData.stats.columns
                    .filter((col) => col.type === 'numeric')
                    .map((col, idx) => (
                      <label key={idx} className="flex items-center gap-2 text-sm text-bg-200 cursor-pointer bg-bg-900 rounded-lg px-3 py-2">
                        <input
                          type="checkbox"
                          checked={col.name in cleaningRules.normalize.columns}
                          onChange={(e) => {
                            const newColumns = { ...cleaningRules.normalize.columns };
                            if (e.target.checked) {
                              newColumns[col.name] = {
                                method: cleaningRules.normalize.defaultMethod,
                              };
                            } else {
                              delete newColumns[col.name];
                            }
                            setCleaningRules({
                              normalize: {
                                ...cleaningRules.normalize,
                                columns: newColumns,
                              },
                            });
                          }}
                          disabled={isCleaning}
                          className="w-4 h-4 rounded border-bg-600 bg-bg-900 text-primary-500 focus:ring-primary-500"
                        />
                        <span>{col.name}</span>
                        {col.name in cleaningRules.normalize.columns && (
                          <select
                            className="select text-xs py-1 px-2 ml-2"
                            value={cleaningRules.normalize.columns[col.name].method}
                            onChange={(e) =>
                              setCleaningRules({
                                normalize: {
                                  ...cleaningRules.normalize,
                                  columns: {
                                    ...cleaningRules.normalize.columns,
                                    [col.name]: {
                                      method: e.target.value as NormalizeMethod,
                                    },
                                  },
                                },
                              })
                            }
                            disabled={isCleaning}
                          >
                            {NORMALIZE_METHODS.map((m) => (
                              <option key={m.value} value={m.value}>
                                {m.label.split(' ')[0]}
                              </option>
                            ))}
                          </select>
                        )}
                      </label>
                    ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
