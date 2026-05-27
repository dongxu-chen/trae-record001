import React, { useState } from 'react';
import { Database, Settings, BarChart3, GitCompare, FileCode, Sparkles, Activity, Lightbulb, Workflow } from 'lucide-react';
import { FileUpload } from './components/FileUpload/FileUpload';
import { DataPreview } from './components/DataPreview/DataPreview';
import { RuleConfig } from './components/RuleConfig/RuleConfig';
import { CleaningControl } from './components/RuleConfig/CleaningControl';
import { ComparePreview } from './components/DataPreview/ComparePreview';
import { ScriptPreview } from './components/ScriptExport/ScriptPreview';
import { MissingHeatmapChart } from './components/charts/MissingHeatmapChart';
import { BoxplotChart } from './components/charts/BoxplotChart';
import { HistogramChart } from './components/charts/HistogramChart';
import { ComparisonChart } from './components/charts/ComparisonChart';
import { QualityAssessment } from './components/QualityAssessment/QualityAssessment';
import { RuleRecommendations } from './components/RuleRecommendations/RuleRecommendations';
import { WorkflowOrchestrator } from './components/WorkflowOrchestrator/WorkflowOrchestrator';
import { useDataStore } from './store/useDataStore';

type TabType = 'preview' | 'quality' | 'recommendations' | 'workflow' | 'rules' | 'charts' | 'compare' | 'script';

export default function App() {
  const { uploadedData, cleaningResult } = useDataStore();
  const [activeTab, setActiveTab] = useState<TabType>('preview');
  const [selectedChartColumn, setSelectedChartColumn] = useState<string | undefined>();

  const tabs: { key: TabType; label: string; icon: React.ReactNode; disabled?: boolean }[] = [
    { key: 'preview', label: '数据预览', icon: <Database size={16} /> },
    { key: 'quality', label: '质量评估', icon: <Activity size={16} /> },
    { key: 'recommendations', label: '智能推荐', icon: <Lightbulb size={16} /> },
    { key: 'workflow', label: '流程编排', icon: <Workflow size={16} /> },
    { key: 'rules', label: '清洗规则', icon: <Settings size={16} /> },
    { key: 'charts', label: '可视化', icon: <BarChart3 size={16} /> },
    {
      key: 'compare',
      label: '对比预览',
      icon: <GitCompare size={16} />,
      disabled: !cleaningResult,
    },
    {
      key: 'script',
      label: '清洗脚本',
      icon: <FileCode size={16} />,
      disabled: !cleaningResult,
    },
  ];

  const numericColumns = uploadedData?.stats?.columns
    .filter((c) => c.type === 'numeric')
    .map((c) => c.name);

  return (
    <div className="min-h-screen bg-bg-950 text-bg-100">
      {/* Header */}
      <header className="border-b border-bg-800 bg-bg-950/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-lg shadow-primary-500/20">
                <Sparkles size={22} className="text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-primary-400 to-accent-400 bg-clip-text text-transparent">
                  DataCleaner Pro
                </h1>
                <p className="text-xs text-bg-500">Web端数据清洗工具</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              {uploadedData && (
                <div className="hidden md:flex items-center gap-4 text-sm text-bg-400">
                  <span>{uploadedData.columns.length} 列</span>
                  <span className="text-bg-700">|</span>
                  <span>{uploadedData.data.length.toLocaleString()} 行</span>
                  {uploadedData.fileName && (
                    <>
                      <span className="text-bg-700">|</span>
                      <span className="font-mono text-xs">{uploadedData.fileName}</span>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {!uploadedData ? (
          <FileUpload />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Sidebar - Rule Config & Control */}
            <div className="lg:col-span-4 space-y-6">
              <RuleConfig />
              <CleaningControl />
            </div>

            {/* Right Content - Tabs */}
            <div className="lg:col-span-8 space-y-6">
              {/* Tab Navigation */}
              <div className="card">
                <div className="card-body !py-2">
                  <div className="flex flex-wrap gap-1">
                    {tabs.map((tab) => (
                      <button
                        key={tab.key}
                        onClick={() => !tab.disabled && setActiveTab(tab.key)}
                        disabled={tab.disabled}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                          activeTab === tab.key
                            ? 'bg-primary-500/10 text-primary-400 shadow-inner'
                            : tab.disabled
                            ? 'text-bg-600 cursor-not-allowed'
                            : 'text-bg-400 hover:text-bg-200 hover:bg-bg-800'
                        }`}
                      >
                        {tab.icon}
                        {tab.label}
                        {tab.disabled && (
                          <span className="ml-1 text-xs bg-bg-700 px-1.5 py-0.5 rounded">
                            待完成
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Tab Content */}
              <div className="animate-fade-in">
                {activeTab === 'preview' && <DataPreview />}

                {activeTab === 'quality' && <QualityAssessment />}

                {activeTab === 'recommendations' && <RuleRecommendations />}

                {activeTab === 'workflow' && <WorkflowOrchestrator />}

                {activeTab === 'rules' && (
                  <div className="card">
                    <div className="card-header">
                      <h3 className="font-semibold text-bg-100">规则配置说明</h3>
                    </div>
                    <div className="card-body text-bg-400 text-sm space-y-4">
                      <p>
                        请在左侧面板配置数据清洗规则。您可以为每列设置独立的处理策略，包括：
                      </p>
                      <ul className="list-disc list-inside space-y-2 pl-2">
                        <li>
                          <span className="text-bg-200">重复值处理</span>：检测并删除重复数据行
                        </li>
                        <li>
                          <span className="text-bg-200">缺失值填充</span>：使用均值、中位数、众数等方法填充缺失值
                        </li>
                        <li>
                          <span className="text-bg-200">异常值检测</span>：通过Z-score或IQR方法识别异常值
                        </li>
                        <li>
                          <span className="text-bg-200">数据标准化</span>：将数据缩放到标准范围
                        </li>
                      </ul>
                      <p className="text-primary-400">
                        💡 提示：也可以使用"智能推荐"和"流程编排"功能来快速配置清洗规则。
                      </p>
                    </div>
                  </div>
                )}

                {activeTab === 'charts' && uploadedData?.stats && (
                  <div className="space-y-6">
                    {/* Charts Header - Column Selector */}
                    {numericColumns && numericColumns.length > 0 && (
                      <div className="card">
                        <div className="card-body">
                          <label className="text-sm text-bg-400 block mb-2">
                            选择列查看数值分布
                          </label>
                          <select
                            value={selectedChartColumn || ''}
                            onChange={(e) => setSelectedChartColumn(e.target.value || undefined)}
                            className="input-select w-full max-w-md"
                          >
                            <option value="">{numericColumns[0]}</option>
                            {numericColumns.map((col) => (
                              <option key={col} value={col}>
                                {col}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                    )}

                    {/* Charts Grid */}
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                      <div className="card min-h-[300px]">
                        <div className="card-body !p-4">
                          <MissingHeatmapChart columns={uploadedData.stats.columns} />
                        </div>
                      </div>

                      <div className="card min-h-[300px]">
                        <div className="card-body !p-4">
                          <BoxplotChart columns={uploadedData.stats.columns} />
                        </div>
                      </div>

                      <div className="card min-h-[300px] xl:col-span-2">
                        <div className="card-body !p-4">
                          <HistogramChart
                            columns={uploadedData.stats.columns}
                            selectedColumn={selectedChartColumn}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === 'compare' &&
                  uploadedData?.stats &&
                  cleaningResult?.stats && (
                    <div className="space-y-6">
                      <div className="card">
                        <div className="card-body !p-4">
                          <ComparisonChart
                            originalStats={uploadedData.stats}
                            cleanedStats={cleaningResult.stats}
                          />
                        </div>
                      </div>
                      <ComparePreview />
                    </div>
                  )}

                {activeTab === 'script' && <ScriptPreview />}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-bg-800 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-bg-500">
            <p>DataCleaner Pro - 基于 React + TypeScript + Web Worker 构建</p>
            <div className="flex items-center gap-4">
              <span>支持 CSV / Excel 文件上传</span>
              <span className="text-bg-700">|</span>
              <span>最大 50MB</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
