import { useCallback, useEffect, useState } from 'react';
import { ReactFlowProvider } from 'reactflow';
import 'reactflow/dist/style.css';
import { Upload, Database, GitBranch, Table, Download, Settings, Trash2, Save, Clock, FolderOpen, Gauge, ArrowRight } from 'lucide-react';
import FileUpload from '@/components/FileUpload';
import SourcePanel from '@/components/SourcePanel';
import TargetPanel from '@/components/TargetPanel';
import MappingCanvas from '@/components/MappingCanvas';
import TransformPanel from '@/components/TransformPanel';
import DataPreview from '@/components/DataPreview';
import ExportPanel from '@/components/ExportPanel';
import TemplateManager from '@/components/TemplateManager';
import QualityPanel from '@/components/QualityPanel';
import PipelinePanel from '@/components/PipelinePanel';
import { useAppStore, loadLastProject } from '@/store';
import type { TargetField } from '@/types';

function App() {
  const [activeTab, setActiveTab] = useState<'upload' | 'mapping' | 'preview'>('upload');
  const { sourceFields, sourceData, targetFields, mappings, clearAll, setTargetFields, lastSaved, projectId } = useAppStore();
  const [showTargetConfig, setShowTargetConfig] = useState(false);
  const [targetConfigText, setTargetConfigText] = useState('');
  const [restored, setRestored] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const [showQuality, setShowQuality] = useState(false);
  const [showPipeline, setShowPipeline] = useState(false);

  useEffect(() => {
    const restore = async () => {
      await loadLastProject();
      setRestored(true);
    };
    restore();
  }, []);

  const handleTargetConfigSave = useCallback(() => {
    try {
      const config = JSON.parse(targetConfigText);
      if (Array.isArray(config)) {
        const fields: TargetField[] = config.map((item, index) => ({
          id: `target-${index}`,
          name: item.name || `field_${index}`,
          type: item.type || 'string',
          required: item.required || false,
          description: item.description || '',
        }));
        setTargetFields(fields);
        setShowTargetConfig(false);
      }
    } catch {
      alert('JSON格式错误，请检查');
    }
  }, [targetConfigText, setTargetFields]);

  const hasData = sourceFields.length > 0;
  const hasTarget = targetFields.length > 0;
  const hasMappings = mappings.length > 0;

  useEffect(() => {
    if (hasData && hasTarget && activeTab === 'upload') {
      setActiveTab('mapping');
    }
  }, [hasData, hasTarget, activeTab]);

  return (
    <ReactFlowProvider>
      <div className="h-screen flex flex-col bg-slate-50">
        <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl flex items-center justify-center">
              <GitBranch className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-800">数据映射工具</h1>
              <p className="text-sm text-slate-500">可视化字段映射与数据转换</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {lastSaved && (
              <div className="flex items-center gap-2 text-xs text-slate-500 bg-slate-50 px-3 py-1.5 rounded-lg">
                <Save className="w-3.5 h-3.5 text-emerald-500" />
                <span>已保存</span>
                <Clock className="w-3.5 h-3.5" />
                <span>{new Date(lastSaved).toLocaleTimeString('zh-CN')}</span>
              </div>
            )}
            {projectId && (
              <span className="text-xs text-slate-400">
                项目 #{projectId}
              </span>
            )}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowPipeline(true)}
                className="flex items-center gap-2 px-3 py-2 text-cyan-600 hover:bg-cyan-50 rounded-lg transition-colors"
                title="多轮映射流水线"
              >
                <ArrowRight className="w-4 h-4" />
                <span className="hidden sm:inline">流水线</span>
              </button>
              <button
                onClick={() => setShowTemplates(true)}
                className="flex items-center gap-2 px-3 py-2 text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
                title="映射模板库"
              >
                <FolderOpen className="w-4 h-4" />
                <span className="hidden sm:inline">模板</span>
              </button>
              <button
                onClick={() => setShowQuality(true)}
                className="flex items-center gap-2 px-3 py-2 text-amber-600 hover:bg-amber-50 rounded-lg transition-colors"
                title="质量评估"
              >
                <Gauge className="w-4 h-4" />
                <span className="hidden sm:inline">质检</span>
              </button>
              <div className="w-px h-6 bg-slate-200" />
              <button
                onClick={clearAll}
                className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                清空
              </button>
            </div>
          </div>
        </header>

        <div className="bg-white border-b border-slate-200 px-6">
          <div className="flex gap-1">
            {[
              { id: 'upload', label: '数据导入', icon: Upload, disabled: false },
              { id: 'mapping', label: '字段映射', icon: GitBranch, disabled: !hasData || !hasTarget },
              { id: 'preview', label: '预览导出', icon: Download, disabled: !hasMappings },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => !tab.disabled && setActiveTab(tab.id as typeof activeTab)}
                disabled={tab.disabled}
                className={`flex items-center gap-2 px-5 py-3 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : tab.disabled
                    ? 'border-transparent text-slate-300 cursor-not-allowed'
                    : 'border-transparent text-slate-600 hover:text-slate-800 hover:border-slate-300'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <main className="flex-1 overflow-hidden">
          {activeTab === 'upload' && (
            <div className="h-full p-6 overflow-auto">
              <div className="max-w-5xl mx-auto space-y-6">
                <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                      <Database className="w-5 h-5 text-blue-600" />
                    </div>
                    <div>
                      <h2 className="text-lg font-semibold text-slate-800">导入源数据</h2>
                      <p className="text-sm text-slate-500">支持 Excel (.xlsx/.xls)、CSV、JSON 格式</p>
                    </div>
                  </div>
                  <FileUpload />
                </div>

                <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
                        <Settings className="w-5 h-5 text-emerald-600" />
                      </div>
                      <div>
                        <h2 className="text-lg font-semibold text-slate-800">配置目标模型</h2>
                        <p className="text-sm text-slate-500">定义目标数据结构的字段</p>
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        setShowTargetConfig(!showTargetConfig);
                        if (!showTargetConfig && targetFields.length === 0) {
                          setTargetConfigText(JSON.stringify([
                            { name: 'id', type: 'string', required: true, description: '唯一标识' },
                            { name: 'name', type: 'string', required: true, description: '名称' },
                            { name: 'description', type: 'string', required: false, description: '描述' },
                          ], null, 2));
                        }
                      }}
                      className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors"
                    >
                      <Settings className="w-4 h-4" />
                      {targetFields.length > 0 ? '编辑配置' : '快速配置'}
                    </button>
                  </div>

                  {showTargetConfig && (
                    <div className="mb-6 space-y-4">
                      <textarea
                        value={targetConfigText}
                        onChange={(e) => setTargetConfigText(e.target.value)}
                        className="w-full h-48 p-4 font-mono text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                        placeholder="输入JSON格式的目标字段配置..."
                      />
                      <div className="flex gap-3">
                        <button
                          onClick={handleTargetConfigSave}
                          className="px-4 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors"
                        >
                          保存配置
                        </button>
                        <button
                          onClick={() => setShowTargetConfig(false)}
                          className="px-4 py-2 bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 transition-colors"
                        >
                          取消
                        </button>
                      </div>
                    </div>
                  )}

                  {targetFields.length > 0 && (
                    <div className="border border-slate-200 rounded-lg overflow-hidden">
                      <table className="w-full">
                        <thead className="bg-slate-50">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">字段名</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">类型</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">必填</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">描述</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-200">
                          {targetFields.map((field) => (
                            <tr key={field.id}>
                              <td className="px-4 py-3 text-sm font-medium text-slate-800">{field.name}</td>
                              <td className="px-4 py-3">
                                <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                                  field.type === 'string' ? 'bg-blue-100 text-blue-700' :
                                  field.type === 'number' ? 'bg-emerald-100 text-emerald-700' :
                                  field.type === 'date' ? 'bg-amber-100 text-amber-700' :
                                  'bg-purple-100 text-purple-700'
                                }`}>
                                  {field.type}
                                </span>
                              </td>
                              <td className="px-4 py-3">
                                <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                                  field.required ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'
                                }`}>
                                  {field.required ? '是' : '否'}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-sm text-slate-500">{field.description || '-'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {targetFields.length === 0 && !showTargetConfig && (
                    <div className="text-center py-12 border-2 border-dashed border-slate-200 rounded-lg">
                      <Settings className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                      <p className="text-slate-500">点击"快速配置"按钮定义目标数据模型</p>
                    </div>
                  )}
                </div>

                {hasData && hasTarget && (
                  <div className="text-center">
                    <button
                      onClick={() => setActiveTab('mapping')}
                      className="inline-flex items-center gap-2 px-8 py-3 bg-blue-500 text-white font-medium rounded-xl hover:bg-blue-600 transition-colors shadow-lg shadow-blue-500/30"
                    >
                      <GitBranch className="w-5 h-5" />
                      开始字段映射
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'mapping' && (
            <div className="h-full flex">
              <div className="w-72 border-r border-slate-200 bg-white flex flex-col">
                <div className="p-4 border-b border-slate-200">
                  <h3 className="font-semibold text-slate-800 flex items-center gap-2">
                    <Database className="w-4 h-4 text-blue-500" />
                    源字段
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">{sourceFields.length} 个字段</p>
                </div>
                <div className="flex-1 overflow-auto">
                  <SourcePanel />
                </div>
              </div>

              <div className="flex-1 flex flex-col">
                <div className="flex-1 relative bg-slate-50">
                  <MappingCanvas />
                </div>
                <div className="h-64 border-t border-slate-200 bg-white">
                  <TransformPanel />
                </div>
              </div>

              <div className="w-72 border-l border-slate-200 bg-white flex flex-col">
                <div className="p-4 border-b border-slate-200">
                  <h3 className="font-semibold text-slate-800 flex items-center gap-2">
                    <Table className="w-4 h-4 text-emerald-500" />
                    目标字段
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">{targetFields.length} 个字段</p>
                </div>
                <div className="flex-1 overflow-auto">
                  <TargetPanel />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'preview' && (
            <div className="h-full p-6 overflow-auto">
              <div className="max-w-full mx-auto space-y-6">
                <DataPreview />
                <ExportPanel />
              </div>
            </div>
          )}
        </main>

        {showTemplates && (
          <TemplateManager onClose={() => setShowTemplates(false)} />
        )}
        {showQuality && (
          <QualityPanel onClose={() => setShowQuality(false)} />
        )}
        {showPipeline && (
          <PipelinePanel onClose={() => setShowPipeline(false)} />
        )}
      </div>
    </ReactFlowProvider>
  );
}

export default App;
