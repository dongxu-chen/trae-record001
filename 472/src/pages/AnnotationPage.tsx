import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Download,
  Users,
  Tag,
  AlertTriangle,
  TrendingUp,
  BarChart2,
  Check,
  Info,
  Sparkles,
  GitBranch,
  ShieldCheck,
  Clock,
  Play,
  Save,
  RotateCcw,
  ArrowRightLeft,
  Eye,
  EyeOff,
  CheckCircle,
  XCircle,
  History,
  Zap,
  AlertCircle,
} from 'lucide-react';
import { ChartComponent } from '../components/ChartComponent';
import { AnnotationForm } from '../components/AnnotationForm';
import { AnnotationList } from '../components/AnnotationList';
import { useStore, generateId } from '../stores/useStore';
import { wsService } from '../services/websocket';
import { getAnnotationColor, getAnnotationTypeName } from '../utils/export';
import { exportAsJSON, exportAsCSV, exportAsExcel } from '../utils/export';
import { otEngine } from '../utils/operationalTransform';
import {
  batchPreLabel,
  createAutoAnnotation,
  getTrainingStats,
  type PreLabelResult,
} from '../utils/preLabel';
import {
  createVersion,
  getProjectVersions,
  compareVersions,
  restoreVersion,
  getChangeSummary,
  formatVersionName,
  type AnnotationVersion,
  type VersionDiff,
} from '../utils/versionControl';
import {
  assessQuality,
  getQualityLevel,
  getSeverityColor,
  getConfidenceColor,
  type QualityAssessment,
} from '../utils/qualityAssessment';
import type { Annotation, AnnotationType, DataPoint } from '../types';
import type { SnapResult } from '../utils/snapToData';
import { Modal } from '../components/Modal';

type TabType = 'annotations' | 'prelabel' | 'versions' | 'quality';

export const AnnotationPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const {
    currentProject,
    setCurrentProject,
    projects,
       annotations,
    setAnnotations,
    addAnnotation,
    updateAnnotation,
    deleteAnnotation,
    currentUser,
    onlineUsers,
    setOnlineUsers,
  } = useStore();

  const [selectedDataPoint, setSelectedDataPoint] = useState<{ index: number; point: DataPoint } | null>(null);
  const [editingAnnotation, setEditingAnnotation] = useState<Annotation | null>(null);
  const [highlightedIndex, setHighlightedIndex] = useState<number | null>(null);
  const [showExportModal, setShowExportModal] = useState(false);
  const [filterType, setFilterType] = useState<AnnotationType | 'all'>('all');
  const [snappedPoint, setSnappedPoint] = useState<SnapResult | null>(null);
  const [mergeNotification, setMergeNotification] = useState<{
    show: boolean;
    type: 'merge' | 'conflict';
    message: string;
  } | null>(null);

  const [activeTab, setActiveTab] = useState<TabType>('annotations');
  const [preLabelResults, setPreLabelResults] = useState<PreLabelResult[]>([]);
  const [preLabelThreshold, setPreLabelThreshold] = useState(0.6);
  const [isPreLabeling, setIsPreLabeling] = useState(false);
  const [showAutoLabels, setShowAutoLabels] = useState(true);

  const [versions, setVersions] = useState<AnnotationVersion[]>([]);
  const [showVersionModal, setShowVersionModal] = useState(false);
  const [newVersionName, setNewVersionName] = useState('');
  const [newVersionDesc, setNewVersionDesc] = useState('');
  const [compareVersionA, setCompareVersionA] = useState<string | null>(null);
  const [compareVersionB, setCompareVersionB] = useState<string | null>(null);
  const [versionDiff, setVersionDiff] = useState<VersionDiff | null>(null);

  const [qualityAssessment, setQualityAssessment] = useState<QualityAssessment | null>(null);
  const [showQualityModal, setShowQualityModal] = useState(false);

  useEffect(() => {
    const project = projects.find((p) => p.id === id);
    if (project) {
      setCurrentProject(project);
      wsService.connect(project.id, currentUser.id, currentUser.name);
      otEngine.resetProject(project.id);
      setVersions(getProjectVersions(project.id));

      wsService.onOperation((operation) => {
        const result = otEngine.applyOperation(operation, annotations);
        setAnnotations(result.annotations);

        if (result.conflict) {
          setMergeNotification({
            show: true,
            type: result.merged ? 'merge' : 'conflict',
            message: result.merged ? '标注已自动合并' : '检测到标注冲突',
          });
          setTimeout(() => setMergeNotification(null), 3000);
        }
      });

      wsService.onAnnotationAdded((annotation) => {
        if (annotation.projectId === project.id) {
          addAnnotation(annotation);
        }
      });

      wsService.onAnnotationDeleted((annotationId) => {
        deleteAnnotation(annotationId);
      });

      wsService.onConflictResolved((result) => {
        setAnnotations(result.annotations);
        setMergeNotification({
          show: true,
          type: 'merge',
          message: '远程标注已合并',
        });
        setTimeout(() => setMergeNotification(null), 3000);
      });

      wsService.onOnlineUsers((users) => {
        setOnlineUsers(users);
      });
    } else {
      navigate('/');
    }

    return () => {
      wsService.disconnect();
    };
  }, [id]);

  useEffect(() => {
    if (activeTab === 'versions' && currentProject) {
      setVersions(getProjectVersions(currentProject.id));
    }
  }, [activeTab, currentProject]);

  useEffect(() => {
    if (activeTab === 'quality' && currentProject) {
      const projectAnnotations = annotations.filter((a) => a.projectId === currentProject.id);
      const assessment = assessQuality(currentProject.dataPoints, projectAnnotations);
      setQualityAssessment(assessment);
    }
  }, [activeTab, currentProject, annotations]);

  if (!currentProject) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  const projectAnnotations = annotations.filter((a) => a.projectId === currentProject.id);
  const filteredAnnotations =
    filterType === 'all'
      ? projectAnnotations
      : projectAnnotations.filter((a) => a.type === filterType);

  const trainingStats = getTrainingStats(projectAnnotations);

  const handleDataPointClick = (index: number, point: DataPoint) => {
    setSelectedDataPoint({ index, point });
    setEditingAnnotation(null);
  };

  const handleSnapChange = (snapResult: SnapResult | null) => {
    setSnappedPoint(snapResult);
  };

  const handleAddAnnotation = (data: { type: AnnotationType; label: string; description: string }) => {
    if (!selectedDataPoint) return;

    const newAnnotation: Annotation = {
      id: generateId(),
      projectId: currentProject.id,
      type: data.type,
      dataPointIndex: selectedDataPoint.index,
      label: data.label,
      description: data.description,
      color: getAnnotationColor(data.type),
      createdBy: currentUser.name,
      createdAt: new Date().toISOString(),
    };

    const operation = otEngine.createOperation(
      'add',
      currentUser.id,
      currentProject.id,
      newAnnotation
    );

    const result = otEngine.applyOperation(operation, annotations);
    setAnnotations(result.annotations);
    wsService.emitAnnotationOperation(operation);

    if (result.conflict) {
      setMergeNotification({
        show: true,
        type: result.merged ? 'merge' : 'conflict',
        message: result.merged ? '标注已自动合并' : '检测到标注冲突',
      });
      setTimeout(() => setMergeNotification(null), 3000);
    }

    setSelectedDataPoint(null);
  };

  const handleEditAnnotation = (annotation: Annotation) => {
    setEditingAnnotation(annotation);
    setSelectedDataPoint({
      index: annotation.dataPointIndex,
      point: currentProject.dataPoints[annotation.dataPointIndex],
    });
  };

  const handleDeleteAnnotation = (annotationId: string) => {
    const operation = otEngine.createOperation(
      'delete',
      currentUser.id,
      currentProject.id,
      undefined,
      annotationId
    );

    const result = otEngine.applyOperation(operation, annotations);
    setAnnotations(result.annotations);
    wsService.emitAnnotationOperation(operation);
  };

  const handleSelectAnnotation = (dataPointIndex: number) => {
    setHighlightedIndex(dataPointIndex);
    setTimeout(() => setHighlightedIndex(null), 2000);
  };

  const handleExport = (format: 'json' | 'csv' | 'excel') => {
    if (format === 'json') {
      exportAsJSON(projectAnnotations, currentProject.dataPoints);
    } else if (format === 'csv') {
      exportAsCSV(projectAnnotations, currentProject.dataPoints);
    } else {
      exportAsExcel(projectAnnotations, currentProject.dataPoints);
    }
    setShowExportModal(false);
  };

  const runPreLabeling = () => {
    setIsPreLabeling(true);
    setTimeout(() => {
      const results = batchPreLabel(
        currentProject.dataPoints,
        projectAnnotations,
        preLabelThreshold,
        5
      );
      setPreLabelResults(results);
      setIsPreLabeling(false);
    }, 500);
  };

  const applyPreLabel = (result: PreLabelResult) => {
    const newAnnotation = createAutoAnnotation(currentProject.id, result, currentUser.name);
    addAnnotation(newAnnotation);
    setPreLabelResults(preLabelResults.filter((r) => r.dataPointIndex !== result.dataPointIndex));

    const operation = otEngine.createOperation(
      'add',
      currentUser.id,
      currentProject.id,
      newAnnotation
    );
    wsService.emitAnnotationOperation(operation);
  };

  const applyAllPreLabels = () => {
    preLabelResults.forEach((result) => {
      const newAnnotation = createAutoAnnotation(currentProject.id, result, currentUser.name);
      addAnnotation(newAnnotation);

      const operation = otEngine.createOperation(
        'add',
        currentUser.id,
        currentProject.id,
        newAnnotation
      );
      wsService.emitAnnotationOperation(operation);
    });
    setPreLabelResults([]);
  };

  const handleCreateVersion = () => {
    if (!newVersionName.trim()) return;

    const version = createVersion(
      currentProject.id,
      projectAnnotations,
      newVersionName,
      newVersionDesc,
      currentUser.name
    );
    setVersions([...versions, version]);
    setNewVersionName('');
    setNewVersionDesc('');
    setShowVersionModal(false);

    setMergeNotification({
      show: true,
      type: 'merge',
      message: `版本 ${formatVersionName(version.version)} 已保存`,
    });
    setTimeout(() => setMergeNotification(null), 3000);
  };

  const handleRestoreVersion = (versionId: string) => {
    const restored = restoreVersion(currentProject.id, versionId, projectAnnotations);
    setAnnotations([...annotations.filter((a) => a.projectId !== currentProject.id), ...restored]);

    setMergeNotification({
      show: true,
      type: 'merge',
      message: '版本已恢复',
    });
    setTimeout(() => setMergeNotification(null), 3000);
  };

  const handleCompareVersions = () => {
    if (!compareVersionA || !compareVersionB) return;

    const versionA = versions.find((v) => v.id === compareVersionA);
    const versionB = versions.find((v) => v.id === compareVersionB);

    if (versionA && versionB) {
      const diff = compareVersions(versionA, versionB);
      setVersionDiff(diff);
    }
  };

  const stats = {
    total: projectAnnotations.length,
    classification: projectAnnotations.filter((a) => a.type === 'classification').length,
    anomaly: projectAnnotations.filter((a) => a.type === 'anomaly').length,
    trend: projectAnnotations.filter((a) => a.type === 'trend').length,
  };

  const preLabelChartAnnotations = showAutoLabels
    ? [
        ...projectAnnotations,
        ...preLabelResults.map((r) => ({
          id: `pre_${r.dataPointIndex}`,
          projectId: currentProject.id,
          type: r.predictedType,
          dataPointIndex: r.dataPointIndex,
          label: `[预标注] ${r.predictedLabel}`,
          color: getAnnotationColor(r.predictedType) + '99',
          createdBy: 'AI',
          createdAt: new Date().toISOString(),
          isAutoLabeled: true,
          confidence: r.confidence,
        })),
      ]
    : projectAnnotations;

  const tabs: { id: TabType; label: string; icon: any }[] = [
    { id: 'annotations', label: '标注', icon: Tag },
    { id: 'prelabel', label: '智能预标注', icon: Sparkles },
    { id: 'versions', label: '版本管理', icon: GitBranch },
    { id: 'quality', label: '质量评估', icon: ShieldCheck },
  ];

  return (
    <div className="h-screen flex flex-col">
      {mergeNotification?.show && (
        <div
          className={`fixed top-4 right-4 z-50 flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg ${
            mergeNotification.type === 'merge'
              ? 'bg-green-600 text-white'
              : 'bg-amber-600 text-white'
          }`}
        >
          {mergeNotification.type === 'merge' ? (
            <Check className="w-5 h-5" />
          ) : (
            <Info className="w-5 h-5" />
          )}
          <span>{mergeNotification.message}</span>
        </div>
      )}

      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-700 bg-slate-800/50">
        <div className="flex items-center gap-6">
          <div>
            <h1 className="text-xl font-bold text-white">{currentProject.name}</h1>
            <p className="text-sm text-slate-400">{currentProject.dataPoints.length} 个数据点</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 rounded-lg">
              <Tag className="w-4 h-4 text-blue-400" />
              <span className="text-sm text-slate-300">{stats.classification}</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 rounded-lg">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              <span className="text-sm text-slate-300">{stats.anomaly}</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 rounded-lg">
              <TrendingUp className="w-4 h-4 text-green-400" />
              <span className="text-sm text-slate-300">{stats.trend}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-2 bg-slate-700 rounded-lg">
            <Users className="w-4 h-4 text-slate-400" />
            <span className="text-sm text-slate-300">{onlineUsers.length} 在线</span>
          </div>
          <button
            onClick={() => navigate(`/project/${id}/statistics`)}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <BarChart2 className="w-4 h-4" />
            统计
          </button>
          <button
            onClick={() => setShowExportModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Download className="w-4 h-4" />
            导出
          </button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 p-6 overflow-hidden">
          <ChartComponent
            chartType={currentProject.chartType}
            dataPoints={currentProject.dataPoints}
            annotations={preLabelChartAnnotations}
            onDataPointClick={handleDataPointClick}
            highlightedIndex={highlightedIndex}
            onSnapChange={handleSnapChange}
          />

          {selectedDataPoint && (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
              onClick={() => {
                setSelectedDataPoint(null);
                setEditingAnnotation(null);
              }}
            >
              <div onClick={(e) => e.stopPropagation()}>
                <AnnotationForm
                  dataPointIndex={selectedDataPoint.index}
                  dataPoint={selectedDataPoint.point}
                  onSubmit={handleAddAnnotation}
                  onCancel={() => {
                    setSelectedDataPoint(null);
                    setEditingAnnotation(null);
                  }}
                  editAnnotation={editingAnnotation}
                />
              </div>
            </div>
          )}
        </div>

        <aside className="w-96 border-l border-slate-700 bg-slate-800/30 flex flex-col">
          <div className="flex border-b border-slate-700">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-3 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'text-blue-400 border-b-2 border-blue-400 bg-slate-700/50'
                    : 'text-slate-400 hover:text-white hover:bg-slate-700/30'
                }`}
                title={tab.label}
              >
                <tab.icon className="w-4 h-4" />
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            ))}
          </div>

          {activeTab === 'annotations' && (
            <>
              <div className="p-4 border-b border-slate-700">
                <div className="flex gap-2">
                  <button
                    onClick={() => setFilterType('all')}
                    className={`flex-1 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                      filterType === 'all'
                        ? 'bg-slate-600 text-white'
                        : 'bg-slate-700 text-slate-400 hover:text-white'
                    }`}
                  >
                    全部 ({stats.total})
                  </button>
                  <button
                    onClick={() => setFilterType('classification')}
                    className={`flex-1 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                      filterType === 'classification'
                        ? 'bg-blue-600 text-white'
                        : 'bg-slate-700 text-slate-400 hover:text-white'
                    }`}
                  >
                    分类
                  </button>
                  <button
                    onClick={() => setFilterType('anomaly')}
                    className={`flex-1 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                      filterType === 'anomaly'
                        ? 'bg-red-600 text-white'
                        : 'bg-slate-700 text-slate-400 hover:text-white'
                    }`}
                  >
                    异常
                  </button>
                  <button
                    onClick={() => setFilterType('trend')}
                    className={`flex-1 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                      filterType === 'trend'
                        ? 'bg-green-600 text-white'
                        : 'bg-slate-700 text-slate-400 hover:text-white'
                    }`}
                  >
                    趋势
                  </button>
                </div>
              </div>

              <div className="flex-1 p-4 overflow-hidden">
                <AnnotationList
                  annotations={filteredAnnotations}
                  onEdit={handleEditAnnotation}
                  onDelete={handleDeleteAnnotation}
                  onSelect={handleSelectAnnotation}
                />
              </div>
            </>
          )}

          {activeTab === 'prelabel' && (
            <div className="flex-1 p-4 overflow-y-auto">
              <div className="space-y-4">
                <div className="bg-slate-700/50 rounded-xl p-4">
                  <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                    <Zap className="w-4 h-4 text-yellow-400" />
                    训练数据状态
                  </h4>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-slate-400">样本数量</p>
                      <p className="text-white font-medium">{trainingStats.totalSamples}</p>
                    </div>
                    <div>
                      <p className="text-slate-400">标签类别</p>
                      <p className="text-white font-medium">{trainingStats.uniqueLabels.length}</p>
                    </div>
                  </div>
                  {!trainingStats.canPreLabel && (
                    <p className="text-amber-400 text-xs mt-3">
                      需要至少 5 个标注样本才能进行预标注
                    </p>
                  )}
                </div>

                <div className="bg-slate-700/50 rounded-xl p-4">
                  <h4 className="text-white font-medium mb-3">置信度阈值</h4>
                  <input
                    type="range"
                    min="0.3"
                    max="0.9"
                    step="0.05"
                    value={preLabelThreshold}
                    onChange={(e) => setPreLabelThreshold(parseFloat(e.target.value))}
                    className="w-full accent-blue-500"
                  />
                  <p className="text-center text-slate-400 text-sm mt-2">
                    {(preLabelThreshold * 100).toFixed(0)}%
                  </p>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={runPreLabeling}
                    disabled={!trainingStats.canPreLabel || isPreLabeling}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 disabled:from-slate-600 disabled:to-slate-600 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-all"
                  >
                    {isPreLabeling ? (
                      <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                    ) : (
                      <Sparkles className="w-4 h-4" />
                    )}
                    运行预标注
                  </button>
                  <button
                    onClick={() => setShowAutoLabels(!showAutoLabels)}
                    className="px-3 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded-lg transition-colors"
                    title={showAutoLabels ? '隐藏预标注' : '显示预标注'}
                  >
                    {showAutoLabels ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                  </button>
                </div>

                {preLabelResults.length > 0 && (
                  <>
                    <div className="flex items-center justify-between">
                      <p className="text-slate-400 text-sm">
                        找到 {preLabelResults.length} 个高置信度预标注
                      </p>
                      <button
                        onClick={applyAllPreLabels}
                        className="text-sm text-blue-400 hover:text-blue-300"
                      >
                        全部应用
                      </button>
                    </div>

                    <div className="space-y-2 max-h-80 overflow-y-auto">
                      {preLabelResults.map((result) => (
                        <div
                          key={result.dataPointIndex}
                          className="bg-slate-700/50 rounded-lg p-3"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-white text-sm font-medium">
                              #{result.dataPointIndex}
                            </span>
                            <span
                              className="text-xs px-2 py-0.5 rounded-full"
                              style={{
                                backgroundColor: getAnnotationColor(result.predictedType) + '30',
                                color: getAnnotationColor(result.predictedType),
                              }}
                            >
                              {getAnnotationTypeName(result.predictedType)}
                            </span>
                          </div>
                          <p className="text-slate-300 text-sm mb-2">{result.predictedLabel}</p>
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <div className="w-20 h-1.5 bg-slate-600 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-blue-500 rounded-full"
                                  style={{ width: `${result.confidence * 100}%` }}
                                />
                              </div>
                              <span className="text-xs text-slate-400">
                                {(result.confidence * 100).toFixed(0)}%
                              </span>
                            </div>
                            <button
                              onClick={() => applyPreLabel(result)}
                              className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded transition-colors"
                            >
                              应用
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {activeTab === 'versions' && (
            <div className="flex-1 p-4 overflow-y-auto">
              <div className="space-y-4">
                <button
                  onClick={() => setShowVersionModal(true)}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  <Save className="w-4 h-4" />
                  保存当前版本
                </button>

                <div className="bg-slate-700/50 rounded-xl p-4">
                  <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                    <ArrowRightLeft className="w-4 h-4 text-cyan-400" />
                    版本对比
                  </h4>
                  <div className="space-y-3">
                    <select
                      value={compareVersionA || ''}
                      onChange={(e) => setCompareVersionA(e.target.value || null)}
                      className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm"
                    >
                      <option value="">选择版本 A</option>
                      {versions.map((v) => (
                        <option key={v.id} value={v.id}>
                          {formatVersionName(v.version)} - {v.name}
                        </option>
                      ))}
                    </select>
                    <select
                      value={compareVersionB || ''}
                      onChange={(e) => setCompareVersionB(e.target.value || null)}
                      className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm"
                    >
                      <option value="">选择版本 B</option>
                      {versions.map((v) => (
                        <option key={v.id} value={v.id}>
                          {formatVersionName(v.version)} - {v.name}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={handleCompareVersions}
                      disabled={!compareVersionA || !compareVersionB}
                      className="w-full px-4 py-2 bg-slate-600 hover:bg-slate-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm rounded-lg transition-colors"
                    >
                      对比版本
                    </button>
                  </div>
                </div>

                {versionDiff && (
                  <div className="bg-slate-700/50 rounded-xl p-4">
                    <h4 className="text-white font-medium mb-3">差异分析</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="text-green-400">新增</span>
                        <span className="text-white font-medium">{versionDiff.added.length}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-red-400">删除</span>
                        <span className="text-white font-medium">{versionDiff.removed.length}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-yellow-400">修改</span>
                        <span className="text-white font-medium">{versionDiff.modified.length}</span>
                      </div>
                    </div>
                    <button
                      onClick={() => setVersionDiff(null)}
                      className="w-full mt-3 px-4 py-2 bg-slate-600 hover:bg-slate-500 text-white text-sm rounded-lg transition-colors"
                    >
                      关闭对比
                    </button>
                  </div>
                )}

                <div className="space-y-2">
                  <h4 className="text-white font-medium flex items-center gap-2">
                    <History className="w-4 h-4" />
                    历史版本
                  </h4>
                  {versions.length === 0 ? (
                    <p className="text-slate-400 text-sm text-center py-4">暂无版本记录</p>
                  ) : (
                    versions
                      .slice()
                      .reverse()
                      .map((version) => (
                        <div
                          key={version.id}
                          className="bg-slate-700/50 rounded-lg p-3"
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-white font-medium">
                              {formatVersionName(version.version)}
                            </span>
                            <span className="text-xs text-slate-400">
                              {new Date(version.createdAt).toLocaleDateString()}
                            </span>
                          </div>
                          <p className="text-slate-300 text-sm mb-2">{version.name}</p>
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-slate-400">
                              {version.annotations.length} 个标注
                            </span>
                            <button
                              onClick={() => handleRestoreVersion(version.id)}
                              className="text-xs flex items-center gap-1 text-blue-400 hover:text-blue-300"
                            >
                              <RotateCcw className="w-3 h-3" />
                              恢复
                            </button>
                          </div>
                        </div>
                      ))
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'quality' && qualityAssessment && (
            <div className="flex-1 p-4 overflow-y-auto">
              <div className="space-y-4">
                <div
                  className="rounded-xl p-4 border-2"
                  style={{
                    backgroundColor: getQualityLevel(qualityAssessment.overallQuality).color + '20',
                    borderColor: getQualityLevel(qualityAssessment.overallQuality).color,
                  }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-white font-medium">总体质量</h4>
                    <span
                      className="text-2xl font-bold"
                      style={{ color: getQualityLevel(qualityAssessment.overallQuality).color }}
                    >
                      {(qualityAssessment.overallQuality * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="text-sm" style={{ color: getQualityLevel(qualityAssessment.overallQuality).color }}>
                    {getQualityLevel(qualityAssessment.overallQuality).level}
                  </p>
                  <p className="text-slate-400 text-xs mt-1">
                    {getQualityLevel(qualityAssessment.overallQuality).description}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-slate-700/50 rounded-xl p-3">
                    <p className="text-slate-400 text-xs">覆盖率</p>
                    <p className="text-white text-xl font-bold">
                      {(qualityAssessment.coverageScore * 100).toFixed(1)}%
                    </p>
                  </div>
                  <div className="bg-slate-700/50 rounded-xl p-3">
                    <p className="text-slate-400 text-xs">一致性</p>
                    <p className="text-white text-xl font-bold">
                      {(qualityAssessment.consistencyScore * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>

                {qualityAssessment.missingAnnotations.length > 0 && (
                  <div>
                    <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 text-amber-400" />
                      潜在漏标 ({qualityAssessment.missingAnnotations.length})
                    </h4>
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {qualityAssessment.missingAnnotations.slice(0, 10).map((item, idx) => (
                        <div
                          key={idx}
                          className="bg-slate-700/50 rounded-lg p-3"
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-white text-sm">数据点 #{item.dataPointIndex}</span>
                            <span
                              className="text-xs px-2 py-0.5 rounded-full"
                              style={{
                                backgroundColor: getSeverityColor(item.severity) + '30',
                                color: getSeverityColor(item.severity),
                              }}
                            >
                              {item.severity === 'high' ? '高' : item.severity === 'medium' ? '中' : '低'}
                            </span>
                          </div>
                          <p className="text-slate-400 text-xs">{item.reason}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {qualityAssessment.suspiciousAnnotations.length > 0 && (
                  <div>
                    <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-red-400" />
                      可疑标注 ({qualityAssessment.suspiciousAnnotations.length})
                    </h4>
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {qualityAssessment.suspiciousAnnotations.slice(0, 10).map((item, idx) => (
                        <div
                          key={idx}
                          className="bg-slate-700/50 rounded-lg p-3"
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-white text-sm">#{item.dataPointIndex}</span>
                            <span
                              className="text-xs px-2 py-0.5 rounded-full"
                              style={{
                                backgroundColor: getConfidenceColor(item.confidence) + '30',
                                color: getConfidenceColor(item.confidence),
                              }}
                            >
                              {(item.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                          <p className="text-slate-400 text-xs">{item.reason}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {qualityAssessment.missingAnnotations.length === 0 &&
                  qualityAssessment.suspiciousAnnotations.length === 0 && (
                    <div className="text-center py-8">
                      <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-3" />
                      <p className="text-white font-medium">质量检查通过</p>
                      <p className="text-slate-400 text-sm">未发现明显问题</p>
                    </div>
                  )}
              </div>
            </div>
          )}

          <div className="p-4 border-t border-slate-700">
            <h4 className="text-sm font-medium text-slate-400 mb-3">在线协作者</h4>
            <div className="flex flex-wrap gap-2">
              {onlineUsers.map((user) => (
                <div key={user.id} className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 rounded-lg">
                  <div
                    className="w-6 h-6 rounded-full flex items-center justify-center text-xs text-white font-bold"
                    style={{ backgroundColor: user.color }}
                  >
                    {user.name.charAt(0)}
                  </div>
                  <span className="text-sm text-slate-300">{user.name}</span>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>

      <Modal isOpen={showExportModal} onClose={() => setShowExportModal(false)} title="导出自定义">
        <div className="space-y-3">
          <button
            onClick={() => handleExport('json')}
            className="w-full flex items-center gap-4 p-4 bg-slate-700 hover:bg-slate-600 rounded-xl transition-colors text-left"
          >
            <div className="w-12 h-12 bg-blue-600/20 rounded-xl flex items-center justify-center">
              <span className="text-blue-400 font-bold">JSON</span>
            </div>
            <div>
              <p className="text-white font-medium">导出为 JSON</p>
              <p className="text-sm text-slate-400">完整的数据结构，适合程序处理</p>
            </div>
          </button>

          <button
            onClick={() => handleExport('csv')}
            className="w-full flex items-center gap-4 p-4 bg-slate-700 hover:bg-slate-600 rounded-xl transition-colors text-left"
          >
            <div className="w-12 h-12 bg-green-600/20 rounded-xl flex items-center justify-center">
              <span className="text-green-400 font-bold">CSV</span>
            </div>
            <div>
              <p className="text-white font-medium">导出为 CSV</p>
              <p className="text-sm text-slate-400">表格格式，可在 Excel 中打开</p>
            </div>
          </button>

          <button
            onClick={() => handleExport('excel')}
            className="w-full flex items-center gap-4 p-4 bg-slate-700 hover:bg-slate-600 rounded-xl transition-colors text-left"
          >
            <div className="w-12 h-12 bg-orange-600/20 rounded-xl flex items-center justify-center">
              <span className="text-orange-400 font-bold">XLSX</span>
            </div>
            <div>
              <p className="text-white font-medium">导出为 Excel</p>
              <p className="text-sm text-slate-400">包含数据点和标注的完整工作簿</p>
            </div>
          </button>
        </div>
      </Modal>

      <Modal isOpen={showVersionModal} onClose={() => setShowVersionModal(false)} title="保存版本">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">版本名称</label>
            <input
              type="text"
              value={newVersionName}
              onChange={(e) => setNewVersionName(e.target.value)}
              placeholder="如：初始标注、第一轮审核"
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">版本描述</label>
            <textarea
              value={newVersionDesc}
              onChange={(e) => setNewVersionDesc(e.target.value)}
              placeholder="描述此版本的内容..."
              rows={3}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 resize-none"
            />
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setShowVersionModal(false)}
              className="flex-1 px-4 py-2 bg-slate-600 hover:bg-slate-500 text-white rounded-lg transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleCreateVersion}
              disabled={!newVersionName.trim()}
              className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 disabled:text-slate-400 text-white rounded-lg transition-colors"
            >
              保存版本
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
