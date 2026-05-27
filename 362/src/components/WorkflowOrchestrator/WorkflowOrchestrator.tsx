import React, { useState, useEffect } from 'react';
import {
  Workflow,
  Play,
  GripVertical,
  Plus,
  Trash2,
  Settings,
  ChevronDown,
  ChevronRight,
  ListOrdered,
  Save,
  Copy,
  CircleDot,
  AlertTriangle,
  Sliders,
} from 'lucide-react';
import { useDataStore } from '../../store/useDataStore';
import { WORKFLOW_PRESETS, CLEANING_STEPS } from '../../types';
import type { CleaningWorkflow, WorkflowStep, CleaningStepType, FillMethod, OutlierMethod, NormalizeMethod } from '../../types';
import { Switch } from '../common/Switch';
import { Badge } from '../common/Badge';

const stepTypeIcons: Record<CleaningStepType, React.ReactNode> = {
  duplicates: <Copy size={18} />,
  missing: <CircleDot size={18} />,
  outliers: <AlertTriangle size={18} />,
  normalize: <Sliders size={18} />,
  custom: <Settings size={18} />,
};

const stepTypeColors: Record<CleaningStepType, string> = {
  duplicates: 'bg-primary-500/20 text-primary-400',
  missing: 'bg-success-500/20 text-success-400',
  outliers: 'bg-warning-500/20 text-warning-400',
  normalize: 'bg-accent-500/20 text-accent-400',
  custom: 'bg-bg-600 text-bg-300',
};

interface WorkflowOrchestratorProps {
  className?: string;
}

export const WorkflowOrchestrator: React.FC<WorkflowOrchestratorProps> = ({ className = '' }) => {
  const {
    uploadedData,
    currentWorkflow,
    setCurrentWorkflow,
    updateWorkflowStep,
    reorderWorkflowSteps,
    addWorkflowStep,
    removeWorkflowStep,
    executeWorkflow,
    isCleaning,
  } = useDataStore();

  const [expandedStep, setExpandedStep] = useState<string | null>(null);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

  useEffect(() => {
    if (uploadedData && !currentWorkflow) {
      const defaultPreset = WORKFLOW_PRESETS[0];
      setCurrentWorkflow({
        ...defaultPreset,
        id: `workflow_${Date.now()}`,
        createdAt: new Date(),
        updatedAt: new Date(),
      });
    }
  }, [uploadedData, currentWorkflow, setCurrentWorkflow]);

  if (!uploadedData) {
    return null;
  }

  const handlePresetSelect = (presetIndex: number) => {
    const preset = WORKFLOW_PRESETS[presetIndex];
    setCurrentWorkflow({
      ...preset,
      id: `workflow_${Date.now()}`,
      createdAt: new Date(),
      updatedAt: new Date(),
    });
    setExpandedStep(null);
  };

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    setDragOverIndex(index);
  };

  const handleDrop = (index: number) => {
    if (draggedIndex !== null && draggedIndex !== index) {
      reorderWorkflowSteps(draggedIndex, index);
    }
    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  const handleAddStep = (type: CleaningStepType) => {
    const stepInfo = CLEANING_STEPS.find((s) => s.id === type);
    addWorkflowStep({
      type,
      name: stepInfo?.name || '自定义步骤',
      description: stepInfo?.description || '自定义清洗步骤',
      enabled: true,
      order: currentWorkflow?.steps.length || 0,
    });
  };

  const canExecute =
    currentWorkflow &&
    currentWorkflow.steps.some((s) => s.enabled) &&
    !isCleaning;

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h3 className="font-semibold text-bg-100 flex items-center gap-2">
            <Workflow size={18} className="text-primary-400" />
            清洗流程编排
          </h3>
          {canExecute && (
            <button
              onClick={executeWorkflow}
              className="btn btn-success text-sm flex items-center gap-2"
            >
              <Play size={16} />
              执行工作流
            </button>
          )}
        </div>
      </div>

      {/* Preset Selection */}
      <div className="card">
        <div className="card-header">
          <h4 className="font-medium text-bg-100 flex items-center gap-2">
            <ListOrdered size={16} className="text-primary-400" />
            预设工作流
          </h4>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {WORKFLOW_PRESETS.map((preset, idx) => (
              <button
                key={idx}
                onClick={() => handlePresetSelect(idx)}
                className={`p-4 rounded-lg border text-left transition-all ${
                  currentWorkflow?.name === preset.name
                    ? 'border-primary-500 bg-primary-500/10'
                    : 'border-bg-700 bg-bg-800/50 hover:border-primary-500/50 hover:bg-bg-800'
                }`}
              >
                <div className="font-medium text-bg-100 mb-1">{preset.name}</div>
                <p className="text-xs text-bg-400 mb-3">{preset.description}</p>
                <div className="flex items-center gap-1">
                  {preset.steps.map((step, stepIdx) => (
                    <React.Fragment key={stepIdx}>
                      <div
                        className={`p-1.5 rounded ${stepTypeColors[step.type]}`}
                        title={step.name}
                      >
                        {stepTypeIcons[step.type]}
                      </div>
                      {stepIdx < preset.steps.length - 1 && (
                        <div className="text-bg-600">→</div>
                      )}
                    </React.Fragment>
                  ))}
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Workflow Steps */}
      {currentWorkflow && (
        <>
          <div className="card">
            <div className="card-header flex items-center justify-between">
              <h4 className="font-medium text-bg-100">
                工作流步骤
                <Badge type="numeric" className="ml-2">
                  {currentWorkflow.steps.length}
                </Badge>
              </h4>
              <div className="flex items-center gap-2">
                <span className="text-xs text-bg-500">添加步骤:</span>
                {(['duplicates', 'missing', 'outliers', 'normalize'] as CleaningStepType[]).map(
                  (type) => (
                    <button
                      key={type}
                      onClick={() => handleAddStep(type)}
                      className={`p-2 rounded ${stepTypeColors[type]} hover:opacity-80 transition-opacity`}
                      title={`添加${CLEANING_STEPS.find((s) => s.id === type)?.name}`}
                    >
                      <Plus size={14} />
                    </button>
                  )
                )}
              </div>
            </div>
            <div className="card-body p-0">
              {currentWorkflow.steps.length === 0 ? (
                <div className="text-center py-12 text-bg-500">
                  <Workflow size={48} className="mx-auto mb-4 opacity-30" />
                  <p>暂无步骤，点击上方按钮添加</p>
                </div>
              ) : (
                <div className="divide-y divide-bg-700">
                  {currentWorkflow.steps
                    .sort((a, b) => a.order - b.order)
                    .map((step, idx) => (
                      <WorkflowStepCard
                        key={step.id}
                        step={step}
                        index={idx}
                        isExpanded={expandedStep === step.id}
                        isDragging={draggedIndex === idx}
                        isDragOver={dragOverIndex === idx}
                        onToggleExpand={() =>
                          setExpandedStep(expandedStep === step.id ? null : step.id)
                        }
                        onToggleEnabled={(enabled) =>
                          updateWorkflowStep(step.id, { enabled })
                        }
                        onUpdateConfig={(config) =>
                          updateWorkflowStep(step.id, { config })
                        }
                        onRemove={() => removeWorkflowStep(step.id)}
                        onDragStart={() => handleDragStart(idx)}
                        onDragOver={(e) => handleDragOver(e, idx)}
                        onDrop={() => handleDrop(idx)}
                        onDragEnd={handleDragEnd}
                      />
                    ))}
                </div>
              )}
            </div>
          </div>

          {/* Summary */}
          <div className="card">
            <div className="card-body">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-bg-100 mb-1">{currentWorkflow.name}</h4>
                  <p className="text-sm text-bg-400">{currentWorkflow.description}</p>
                  <div className="flex items-center gap-4 mt-3 text-xs text-bg-500">
                    <span>
                      步骤数:{' '}
                      <span className="text-bg-200 font-mono">
                        {currentWorkflow.steps.length}
                      </span>
                    </span>
                    <span>
                      已启用:{' '}
                      <span className="text-success-400 font-mono">
                        {currentWorkflow.steps.filter((s) => s.enabled).length}
                      </span>
                    </span>
                  </div>
                </div>
                {canExecute && (
                  <button
                    onClick={executeWorkflow}
                    className="btn btn-success flex items-center gap-2"
                  >
                    <Play size={18} />
                    执行工作流
                  </button>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

interface WorkflowStepCardProps {
  step: WorkflowStep;
  index: number;
  isExpanded: boolean;
  isDragging: boolean;
  isDragOver: boolean;
  onToggleExpand: () => void;
  onToggleEnabled: (enabled: boolean) => void;
  onUpdateConfig: (config: any) => void;
  onRemove: () => void;
  onDragStart: () => void;
  onDragOver: (e: React.DragEvent) => void;
  onDrop: () => void;
  onDragEnd: () => void;
}

const WorkflowStepCard: React.FC<WorkflowStepCardProps> = ({
  step,
  index,
  isExpanded,
  isDragging,
  isDragOver,
  onToggleExpand,
  onToggleEnabled,
  onUpdateConfig,
  onRemove,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
}) => {
  return (
    <div
      className={`relative ${
        isDragging ? 'opacity-50' : ''
      } ${isDragOver ? 'border-t-2 border-primary-500' : ''} transition-all`}
      draggable
      onDragStart={onDragStart}
      onDragOver={onDragOver}
      onDrop={onDrop}
      onDragEnd={onDragEnd}
    >
      <div className="flex items-stretch">
        {/* Drag Handle */}
        <div className="flex items-center px-3 cursor-grab active:cursor-grabbing text-bg-600 hover:text-bg-400 border-r border-bg-700">
          <GripVertical size={18} />
        </div>

        {/* Main Content */}
        <div className="flex-1 p-4">
          <div className="flex items-center gap-4">
            {/* Step Number */}
            <div className="w-8 h-8 rounded-full bg-bg-700 flex items-center justify-center text-sm font-mono text-bg-300">
              {index + 1}
            </div>

            {/* Icon */}
            <div
              className={`p-2 rounded-lg ${stepTypeColors[step.type]} ${
                !step.enabled ? 'opacity-50' : ''
              }`}
            >
              {stepTypeIcons[step.type]}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span
                  className={`font-medium ${
                    step.enabled ? 'text-bg-100' : 'text-bg-500'
                  }`}
                >
                  {step.name}
                </span>
                {!step.enabled && <Badge type="warning">已禁用</Badge>}
              </div>
              <p className="text-xs text-bg-500">{step.description}</p>
            </div>

            {/* Controls */}
            <div className="flex items-center gap-2">
              <Switch
                checked={step.enabled}
                onChange={onToggleEnabled}
                disabled={false}
              />
              <button
                onClick={onToggleExpand}
                className="p-2 hover:bg-bg-700 rounded transition-colors"
              >
                {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              </button>
              <button
                onClick={onRemove}
                className="p-2 hover:bg-danger-500/20 text-bg-400 hover:text-danger-400 rounded transition-colors"
                title="删除步骤"
              >
                <Trash2 size={16} />
              </button>
            </div>
          </div>

          {/* Expanded Config */}
          {isExpanded && (
            <StepConfigPanel
              step={step}
              onUpdateConfig={onUpdateConfig}
            />
          )}
        </div>
      </div>
    </div>
  );
};

interface StepConfigPanelProps {
  step: WorkflowStep;
  onUpdateConfig: (config: any) => void;
}

const StepConfigPanel: React.FC<StepConfigPanelProps> = ({ step, onUpdateConfig }) => {
  const { uploadedData } = useDataStore();
  const columns = uploadedData?.columns || [];

  const currentConfig = step.config || {};

  const renderConfig = () => {
    switch (step.type) {
      case 'duplicates':
        return (
          <div className="space-y-4 mt-4 pt-4 border-t border-bg-700">
            <div>
              <label className="block text-sm font-medium text-bg-300 mb-2">
                保留策略
              </label>
              <select
                value={currentConfig.keep || 'first'}
                onChange={(e) =>
                  onUpdateConfig({ ...currentConfig, keep: e.target.value })
                }
                className="select"
              >
                <option value="first">保留第一条</option>
                <option value="last">保留最后一条</option>
                <option value={false as any}>删除所有重复</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-bg-300 mb-2">
                检查列（留空表示检查所有列）
              </label>
              <div className="flex flex-wrap gap-2">
                {columns.map((col) => (
                  <label
                    key={col}
                    className="flex items-center gap-2 text-sm text-bg-400"
                  >
                    <input
                      type="checkbox"
                      checked={
                        currentConfig.targetColumns?.includes(col) ?? true
                      }
                      onChange={(e) => {
                        const currentTargets =
                          currentConfig.targetColumns || [...columns];
                        const newTargets = e.target.checked
                          ? [...currentTargets, col]
                          : currentTargets.filter((c: string) => c !== col);
                        onUpdateConfig({
                          ...currentConfig,
                          targetColumns: newTargets,
                        });
                      }}
                      className="checkbox"
                    />
                    {col}
                  </label>
                ))}
              </div>
            </div>
          </div>
        );

      case 'missing':
        return (
          <div className="space-y-4 mt-4 pt-4 border-t border-bg-700">
            <div>
              <label className="block text-sm font-medium text-bg-300 mb-2">
                默认填充方法
              </label>
              <select
                value={currentConfig.method || 'mean'}
                onChange={(e) =>
                  onUpdateConfig({
                    ...currentConfig,
                    method: e.target.value as FillMethod,
                  })
                }
                className="select"
              >
                <option value="mean">均值填充</option>
                <option value="median">中位数填充</option>
                <option value="mode">众数填充</option>
                <option value="interpolate">线性插值</option>
                <option value="ffill">前向填充</option>
                <option value="bfill">后向填充</option>
              </select>
            </div>
            {currentConfig.method === 'constant' && (
              <div>
                <label className="block text-sm font-medium text-bg-300 mb-2">
                  固定值
                </label>
                <input
                  type="text"
                  value={currentConfig.value || ''}
                  onChange={(e) =>
                    onUpdateConfig({ ...currentConfig, value: e.target.value })
                  }
                  className="input"
                  placeholder="输入填充值"
                />
              </div>
            )}
          </div>
        );

      case 'outliers':
        return (
          <div className="space-y-4 mt-4 pt-4 border-t border-bg-700">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-bg-300 mb-2">
                  检测方法
                </label>
                <select
                  value={currentConfig.method || 'zscore'}
                  onChange={(e) =>
                    onUpdateConfig({
                      ...currentConfig,
                      method: e.target.value as OutlierMethod,
                    })
                  }
                  className="select"
                >
                  <option value="zscore">Z-score</option>
                  <option value="iqr">IQR</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-bg-300 mb-2">
                  处理方式
                </label>
                <select
                  value={currentConfig.action || 'remove'}
                  onChange={(e) =>
                    onUpdateConfig({
                      ...currentConfig,
                      action: e.target.value as 'remove' | 'cap' | 'mark',
                    })
                  }
                  className="select"
                >
                  <option value="remove">删除</option>
                  <option value="cap">盖帽</option>
                  <option value="mark">标记</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-bg-300 mb-2">
                阈值: {currentConfig.threshold || (currentConfig.method === 'iqr' ? 1.5 : 3)}
              </label>
              <input
                type="range"
                min={currentConfig.method === 'iqr' ? 1 : 1}
                max={currentConfig.method === 'iqr' ? 3 : 5}
                step={0.1}
                value={currentConfig.threshold || (currentConfig.method === 'iqr' ? 1.5 : 3)}
                onChange={(e) =>
                  onUpdateConfig({
                    ...currentConfig,
                    threshold: parseFloat(e.target.value),
                  })
                }
                className="w-full"
              />
            </div>
          </div>
        );

      case 'normalize':
        return (
          <div className="space-y-4 mt-4 pt-4 border-t border-bg-700">
            <div>
              <label className="block text-sm font-medium text-bg-300 mb-2">
                标准化方法
              </label>
              <select
                value={currentConfig.method || 'minmax'}
                onChange={(e) =>
                  onUpdateConfig({
                    ...currentConfig,
                    method: e.target.value as NormalizeMethod,
                  })
                }
                className="select"
              >
                <option value="minmax">Min-Max 归一化</option>
                <option value="zscore">Z-score 标准化</option>
                <option value="robust">Robust 标准化</option>
              </select>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return <div className="ml-12">{renderConfig()}</div>;
};
