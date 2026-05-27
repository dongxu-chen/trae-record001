import { useState } from 'react';
import { 
  ArrowRight, 
  Plus, 
  Trash2, 
  Play, 
  Settings, 
  X,
  GripVertical,
  ChevronUp,
  ChevronDown,
  CheckCircle2,
  Loader2
} from 'lucide-react';
import { useAppStore } from '@/store';

interface PipelinePanelProps {
  onClose: () => void;
}

export default function PipelinePanel({ onClose }: PipelinePanelProps) {
  const { 
    mappingSteps, 
    addMappingStep, 
    updateMappingStep, 
    removeMappingStep,
    reorderMappingSteps,
    runPipeline,
    pipelineResult,
    isRunningPipeline
  } = useAppStore();

  const [editingStep, setEditingStep] = useState<number | null>(null);
  const [stepName, setStepName] = useState('');
  const [stepDescription, setStepDescription] = useState('');

  const handleAddStep = () => {
    const newStep = addMappingStep();
    setEditingStep(newStep.id);
    setStepName(newStep.name);
    setStepDescription(newStep.description || '');
  };

  const handleSaveStep = () => {
    if (editingStep !== null) {
      updateMappingStep(editingStep, {
        name: stepName || '未命名步骤',
        description: stepDescription
      });
      setEditingStep(null);
    }
  };

  const handleEditStep = (step: typeof mappingSteps[0]) => {
    setEditingStep(step.id);
    setStepName(step.name);
    setStepDescription(step.description || '');
  };

  const handleMoveStep = (index: number, direction: 'up' | 'down') => {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex >= 0 && newIndex < mappingSteps.length) {
      reorderMappingSteps(index, newIndex);
    }
  };

  const handleRunPipeline = () => {
    runPipeline();
  };

  const getStepStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'border-emerald-300 bg-emerald-50';
      case 'running': return 'border-blue-300 bg-blue-50';
      case 'error': return 'border-red-300 bg-red-50';
      default: return 'border-slate-200 bg-white';
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-cyan-100 rounded-lg flex items-center justify-center">
              <ArrowRight className="w-5 h-5 text-cyan-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-800">多轮映射流水线</h2>
              <p className="text-sm text-slate-500">数据流经多个映射步骤处理</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-auto p-6">
          {pipelineResult && (
            <div className="mb-6 p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
              <div className="flex items-center gap-2 text-emerald-700 font-medium mb-2">
                <CheckCircle2 className="w-5 h-5" />
                流水线执行完成
              </div>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-emerald-600">执行步骤</span>
                  <div className="font-semibold text-emerald-800">{pipelineResult.stepsExecuted} 步</div>
                </div>
                <div>
                  <span className="text-emerald-600">处理数据</span>
                  <div className="font-semibold text-emerald-800">{pipelineResult.totalRecords} 条</div>
                </div>
                <div>
                  <span className="text-emerald-600">总耗时</span>
                  <div className="font-semibold text-emerald-800">{pipelineResult.executionTime}ms</div>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-medium text-slate-700">映射步骤</h3>
              <button
                onClick={handleAddStep}
                className="flex items-center gap-2 px-4 py-2 bg-cyan-500 text-white text-sm rounded-lg hover:bg-cyan-600 transition-colors"
              >
                <Plus className="w-4 h-4" />
                添加步骤
              </button>
            </div>

            {mappingSteps.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                <Settings className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>暂无映射步骤</p>
                <p className="text-sm mt-1">点击"添加步骤"创建多轮映射流水线</p>
              </div>
            ) : (
              <div className="space-y-3">
                {mappingSteps.map((step, index) => (
                  <div key={step.id}>
                    <div
                      className={`p-4 rounded-xl border-2 transition-all ${getStepStatusColor(step.status)}`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="flex flex-col items-center gap-1">
                          <GripVertical className="w-5 h-5 text-slate-400 cursor-grab" />
                          <div className="flex flex-col gap-0.5">
                            <button
                              onClick={() => handleMoveStep(index, 'up')}
                              disabled={index === 0}
                              className="p-1 text-slate-400 hover:text-slate-600 disabled:opacity-30"
                            >
                              <ChevronUp className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleMoveStep(index, 'down')}
                              disabled={index === mappingSteps.length - 1}
                              className="p-1 text-slate-400 hover:text-slate-600 disabled:opacity-30"
                            >
                              <ChevronDown className="w-4 h-4" />
                            </button>
                          </div>
                        </div>

                        <div className="flex-1 min-w-0">
                          {editingStep === step.id ? (
                            <div className="space-y-2">
                              <input
                                type="text"
                                value={stepName}
                                onChange={(e) => setStepName(e.target.value)}
                                placeholder="步骤名称"
                                className="w-full px-3 py-1.5 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                              />
                              <input
                                type="text"
                                value={stepDescription}
                                onChange={(e) => setStepDescription(e.target.value)}
                                placeholder="步骤描述（可选）"
                                className="w-full px-3 py-1.5 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                              />
                              <div className="flex gap-2">
                                <button
                                  onClick={handleSaveStep}
                                  className="px-3 py-1 bg-cyan-500 text-white text-sm rounded-lg hover:bg-cyan-600"
                                >
                                  保存
                                </button>
                                <button
                                  onClick={() => setEditingStep(null)}
                                  className="px-3 py-1 bg-slate-100 text-slate-600 text-sm rounded-lg hover:bg-slate-200"
                                >
                                  取消
                                </button>
                              </div>
                            </div>
                          ) : (
                            <>
                              <div className="flex items-center gap-2">
                                <span className="w-6 h-6 bg-cyan-100 text-cyan-700 rounded-full flex items-center justify-center text-sm font-medium">
                                  {index + 1}
                                </span>
                                <span className="font-medium text-slate-800">{step.name}</span>
                                {step.status === 'running' && (
                                  <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                                )}
                                {step.status === 'completed' && (
                                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                                )}
                              </div>
                              {step.description && (
                                <p className="text-sm text-slate-500 mt-1 ml-8">{step.description}</p>
                              )}
                              <div className="flex items-center gap-4 mt-2 ml-8 text-xs text-slate-400">
                                <span>字段映射: {step.fieldMappings.length}</span>
                                <span>创建于: {new Date(step.createdAt).toLocaleDateString('zh-CN')}</span>
                              </div>
                            </>
                          )}
                        </div>

                        {editingStep !== step.id && (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => handleEditStep(step)}
                              className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                            >
                              <Settings className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => removeMappingStep(step.id)}
                              className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        )}
                      </div>
                    </div>

                    {index < mappingSteps.length - 1 && (
                      <div className="flex justify-center py-1">
                        <ArrowRight className="w-5 h-5 text-slate-300" />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 rounded-b-2xl">
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleRunPipeline}
              disabled={mappingSteps.length === 0 || isRunningPipeline}
              className="flex-1 px-4 py-2 bg-cyan-500 text-white rounded-lg hover:bg-cyan-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {isRunningPipeline ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  执行中...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  执行流水线
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
