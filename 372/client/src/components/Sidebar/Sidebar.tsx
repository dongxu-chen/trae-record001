import React, { useState, useMemo, useEffect } from 'react';
import { useAnnotationStore } from '@/store/useAnnotationStore';
import { 
  ExportFormat, 
  ExportFormatInfo, 
  exportByFormat, 
  clearSAMCache,
  checkAnnotationQuality,
  getVersions,
  saveVersion,
  rollbackToVersion,
  compareVersions,
  deleteVersion,
  uploadVideo,
  getVideos,
  extractKeyframes,
  getVideoFrame,
  interpolateAnnotations
} from '@/services/api';
import type { Annotation, QualityReport, AnnotationVersion, VideoInfo, VideoFrameInfo } from '@/types/annotation';

const EXPORT_FORMATS: ExportFormatInfo[] = [
  { id: 'json', name: 'JSON', description: '自定义JSON格式，包含完整标注数据', extension: '.json' },
  { id: 'mask', name: 'Mask PNG', description: '彩色分割掩码图像，用于语义分割', extension: '.png' },
  { id: 'yolo', name: 'YOLO', description: 'YOLO目标检测格式，归一化坐标', extension: '.txt' },
  { id: 'labelme', name: 'LabelMe', description: 'LabelMe标注格式，多边形区域', extension: '.json' },
  { id: 'voc', name: 'Pascal VOC', description: 'Pascal VOC XML格式，边界框', extension: '.xml' },
  { id: 'coco', name: 'COCO', description: 'COCO JSON格式，目标检测/分割', extension: '.json' },
];

type TabType = 'annotations' | 'labels' | 'export' | 'quality' | 'versions' | 'video' | 'stats';

const Sidebar: React.FC = () => {
  const { annotations, labels, deleteAnnotation, addLabel, deleteLabel, updateAnnotationLabel, samStats, setAnnotations } = useAnnotationStore();
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('json');
  const [newLabelName, setNewLabelName] = useState('');
  const [newLabelColor, setNewLabelColor] = useState('#3b82f6');
  const [isExporting, setIsExporting] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>('annotations');
  
  const [qualityReport, setQualityReport] = useState<QualityReport | null>(null);
  const [isCheckingQuality, setIsCheckingQuality] = useState(false);
  
  const [versions, setVersions] = useState<AnnotationVersion[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null);
  const [versionDescription, setVersionDescription] = useState('');
  const [isSavingVersion, setIsSavingVersion] = useState(false);
  
  const [videos, setVideos] = useState<VideoInfo[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<VideoInfo | null>(null);
  const [keyframes, setKeyframes] = useState<VideoFrameInfo[]>([]);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [isExtractingKeyframes, setIsExtractingKeyframes] = useState(false);

  const currentImageId = useAnnotationStore(state => state.currentImageId);

  const labelStats = useMemo(() => {
    const stats: Record<string, number> = {};
    annotations.forEach(ann => {
      const label = ann.label || 'unlabeled';
      stats[label] = (stats[label] || 0) + 1;
    });
    return stats;
  }, [annotations]);

  const totalPixels = useMemo(() => {
    return annotations.reduce((sum, ann) => sum + (ann.pixelArea || 0), 0);
  }, [annotations]);

  useEffect(() => {
    loadVideos();
  }, []);

  useEffect(() => {
    if (currentImageId) {
      loadVersions(currentImageId);
    }
  }, [currentImageId]);

  const loadVideos = async () => {
    try {
      const videoList = await getVideos();
      setVideos(videoList);
    } catch (error) {
      console.error('Failed to load videos:', error);
    }
  };

  const loadVersions = async (imageId: string) => {
    try {
      const versionList = await getVersions(imageId);
      setVersions(versionList);
    } catch (error) {
      console.error('Failed to load versions:', error);
    }
  };

  const handleExport = async () => {
    if (!currentImageId || annotations.length === 0) return;
    setIsExporting(true);
    try {
      await exportByFormat(selectedFormat, currentImageId, annotations);
    } catch (error) {
      console.error('Export failed:', error);
      alert('导出失败，请重试');
    } finally {
      setIsExporting(false);
    }
  };

  const handleAddLabel = () => {
    if (newLabelName.trim()) {
      addLabel(newLabelName.trim(), newLabelColor);
      setNewLabelName('');
    }
  };

  const handleClearCache = async () => {
    if (currentImageId) {
      await clearSAMCache(currentImageId);
    }
  };

  const handleCheckQuality = async () => {
    if (!currentImageId || annotations.length === 0) return;
    setIsCheckingQuality(true);
    try {
      const report = await checkAnnotationQuality(currentImageId, annotations);
      setQualityReport(report);
    } catch (error) {
      console.error('Quality check failed:', error);
      alert('质量检查失败');
    } finally {
      setIsCheckingQuality(false);
    }
  };

  const handleSaveVersion = async () => {
    if (!currentImageId || annotations.length === 0) return;
    setIsSavingVersion(true);
    try {
      await saveVersion(currentImageId, annotations, versionDescription);
      setVersionDescription('');
      await loadVersions(currentImageId);
      alert('版本保存成功');
    } catch (error) {
      console.error('Failed to save version:', error);
      alert('版本保存失败');
    } finally {
      setIsSavingVersion(false);
    }
  };

  const handleRollbackVersion = async (versionId: string) => {
    if (!currentImageId) return;
    try {
      const rolledBackAnnotations = await rollbackToVersion(currentImageId, versionId);
      setAnnotations(rolledBackAnnotations);
      alert('已回滚到选中版本');
    } catch (error) {
      console.error('Failed to rollback version:', error);
      alert('回滚失败');
    }
  };

  const handleDeleteVersion = async (versionId: string) => {
    if (!currentImageId) return;
    if (!confirm('确定要删除这个版本吗？')) return;
    try {
      await deleteVersion(currentImageId, versionId);
      await loadVersions(currentImageId);
    } catch (error) {
      console.error('Failed to delete version:', error);
    }
  };

  const handleVideoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const videoInfo = await uploadVideo(file);
      setVideos([...videos, videoInfo]);
      setSelectedVideo(videoInfo);
    } catch (error) {
      console.error('Failed to upload video:', error);
      alert('视频上传失败');
    }
  };

  const handleExtractKeyframes = async () => {
    if (!selectedVideo) return;
    setIsExtractingKeyframes(true);
    try {
      const frames = await extractKeyframes(selectedVideo.id, 30, 50);
      setKeyframes(frames);
    } catch (error) {
      console.error('Failed to extract keyframes:', error);
      alert('关键帧提取失败');
    } finally {
      setIsExtractingKeyframes(false);
    }
  };

  const formatArea = (pixels: number) => {
    if (pixels >= 1000000) {
      return `${(pixels / 1000000).toFixed(2)}M px`;
    } else if (pixels >= 1000) {
      return `${(pixels / 1000).toFixed(1)}K px`;
    }
    return `${pixels} px`;
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleString('zh-CN');
  };

  const getTypeIcon = (type: Annotation['type']) => {
    const icons = {
      polygon: '⬡',
      point: '●',
      rectangle: '▭',
      brush: '✎',
      sam: '✦',
    };
    return icons[type] || '○';
  };

  const getTypeColor = (type: Annotation['type']) => {
    const colors = {
      polygon: '#3b82f6',
      point: '#10b981',
      rectangle: '#f59e0b',
      brush: '#8b5cf6',
      sam: '#ec4899',
    };
    return colors[type] || '#6b7280';
  };

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      critical: '#ef4444',
      warning: '#f59e0b',
      info: '#3b82f6',
    };
    return colors[severity] || '#6b7280';
  };

  const tabs = [
    { id: 'annotations', label: '标注', icon: '📝' },
    { id: 'labels', label: '标签', icon: '🏷️' },
    { id: 'export', label: '导出', icon: '💾' },
    { id: 'quality', label: '质量', icon: '✅' },
    { id: 'versions', label: '版本', icon: '📚' },
    { id: 'video', label: '视频', icon: '🎬' },
    { id: 'stats', label: '统计', icon: '📊' },
  ];

  return (
    <div className="w-80 bg-slate-800 flex flex-col h-full border-l border-slate-700">
      <div className="p-2 border-b border-slate-700">
        <div className="grid grid-cols-4 gap-1">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabType)}
              className={`py-2 text-xs font-medium rounded transition-colors ${
                activeTab === tab.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
              title={tab.label}
            >
              {tab.icon}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {activeTab === 'annotations' && (
          <div className="p-3">
            <h3 className="text-sm font-semibold text-slate-200 mb-3">
              标注列表 ({annotations.length})
            </h3>
            
            {annotations.length === 0 ? (
              <div className="text-slate-500 text-sm text-center py-8">
                暂无标注数据
              </div>
            ) : (
              <div className="space-y-2">
                {annotations.map((ann, index) => (
                  <div
                    key={ann.id}
                    className="bg-slate-700/50 rounded-lg p-3 group hover:bg-slate-700 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: getTypeColor(ann.type) }}
                        />
                        <span className="text-sm text-slate-200 font-medium">
                          {getTypeIcon(ann.type)} #{index + 1}
                        </span>
                      </div>
                      <button
                        onClick={() => deleteAnnotation(ann.id)}
                        className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 transition-opacity text-lg leading-none"
                      >
                        ×
                      </button>
                    </div>
                    
                    <div className="flex items-center gap-2 text-xs text-slate-400 mb-2">
                      <span>{ann.type}</span>
                      <span>·</span>
                      <span>{formatArea(ann.pixelArea || 0)}</span>
                    </div>
                    
                    <select
                      value={ann.label || ''}
                      onChange={(e) => updateAnnotationLabel(ann.id, e.target.value)}
                      className="w-full bg-slate-600 border border-slate-500 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                    >
                      <option value="">选择标签...</option>
                      {labels.map(label => (
                        <option key={label.id} value={label.name}>
                          {label.name}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'labels' && (
          <div className="p-3">
            <h3 className="text-sm font-semibold text-slate-200 mb-3">
              标签管理 ({labels.length})
            </h3>
            
            <div className="bg-slate-700/50 rounded-lg p-3 mb-4">
              <div className="flex gap-2 mb-2">
                <input
                  type="color"
                  value={newLabelColor}
                  onChange={(e) => setNewLabelColor(e.target.value)}
                  className="w-8 h-8 rounded cursor-pointer border-0"
                />
                <input
                  type="text"
                  value={newLabelName}
                  onChange={(e) => setNewLabelName(e.target.value)}
                  placeholder="标签名称"
                  className="flex-1 bg-slate-600 border border-slate-500 rounded px-2 py-1 text-sm text-slate-200 placeholder-slate-400 focus:outline-none focus:border-blue-500"
                  onKeyPress={(e) => e.key === 'Enter' && handleAddLabel()}
                />
              </div>
              <button
                onClick={handleAddLabel}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white py-1.5 rounded text-sm font-medium transition-colors"
              >
                添加标签
              </button>
            </div>
            
            {labels.length === 0 ? (
              <div className="text-slate-500 text-sm text-center py-8">
                暂无标签
              </div>
            ) : (
              <div className="space-y-2">
                {labels.map(label => (
                  <div
                    key={label.id}
                    className="bg-slate-700/50 rounded-lg p-3 flex items-center justify-between group"
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className="w-4 h-4 rounded"
                        style={{ backgroundColor: label.color }}
                      />
                      <span className="text-sm text-slate-200">{label.name}</span>
                      {labelStats[label.name] && (
                        <span className="text-xs text-slate-500">
                          ({labelStats[label.name]})
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => deleteLabel(label.id)}
                      className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 transition-opacity"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'export' && (
          <div className="p-3">
            <h3 className="text-sm font-semibold text-slate-200 mb-3">导出标注</h3>
            
            <div className="space-y-2 mb-4">
              {EXPORT_FORMATS.map(format => (
                <button
                  key={format.id}
                  onClick={() => setSelectedFormat(format.id)}
                  className={`w-full text-left p-3 rounded-lg border transition-all ${
                    selectedFormat === format.id
                      ? 'bg-blue-600/20 border-blue-500'
                      : 'bg-slate-700/50 border-slate-600 hover:border-slate-500'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-slate-200">
                      {format.name}
                    </span>
                    <span className="text-xs text-slate-500">{format.extension}</span>
                  </div>
                  <p className="text-xs text-slate-400">{format.description}</p>
                </button>
              ))}
            </div>
            
            <button
              onClick={handleExport}
              disabled={!currentImageId || annotations.length === 0 || isExporting}
              className={`w-full py-3 rounded-lg font-medium transition-colors ${
                currentImageId && annotations.length > 0 && !isExporting
                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                  : 'bg-slate-600 text-slate-400 cursor-not-allowed'
              }`}
            >
              {isExporting ? '导出中...' : `导出为 ${EXPORT_FORMATS.find(f => f.id === selectedFormat)?.name}`}
            </button>
            
            {(!currentImageId || annotations.length === 0) && (
              <p className="text-xs text-slate-500 text-center mt-2">
                {!currentImageId ? '请先上传图片' : '请先添加标注'}
              </p>
            )}
          </div>
        )}

        {activeTab === 'quality' && (
          <div className="p-3">
            <h3 className="text-sm font-semibold text-slate-200 mb-3">质量检查</h3>
            
            <button
              onClick={handleCheckQuality}
              disabled={!currentImageId || annotations.length === 0 || isCheckingQuality}
              className={`w-full py-2 rounded-lg font-medium transition-colors mb-4 ${
                currentImageId && annotations.length > 0 && !isCheckingQuality
                  ? 'bg-green-600 hover:bg-green-700 text-white'
                  : 'bg-slate-600 text-slate-400 cursor-not-allowed'
              }`}
            >
              {isCheckingQuality ? '检查中...' : '开始质量检查'}
            </button>

            {qualityReport && (
              <>
                <div className="bg-slate-700/50 rounded-lg p-4 mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-slate-400">质量评分</span>
                    <span className={`text-2xl font-bold ${
                      qualityReport.quality_score >= 80 ? 'text-green-400' :
                      qualityReport.quality_score >= 60 ? 'text-yellow-400' : 'text-red-400'
                    }`}>
                      {qualityReport.quality_score.toFixed(1)}
                    </span>
                  </div>
                  <div className="h-2 bg-slate-600 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all ${
                        qualityReport.quality_score >= 80 ? 'bg-green-500' :
                        qualityReport.quality_score >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${qualityReport.quality_score}%` }}
                    />
                  </div>
                </div>

                {qualityReport.details && (
                  <div className="bg-slate-700/50 rounded-lg p-3 mb-4">
                    <h4 className="text-xs font-semibold text-slate-400 mb-2">统计</h4>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-slate-400">严重问题: </span>
                        <span className="text-red-400">{qualityReport.details.critical_count}</span>
                      </div>
                      <div>
                        <span className="text-slate-400">警告: </span>
                        <span className="text-yellow-400">{qualityReport.details.warning_count}</span>
                      </div>
                    </div>
                  </div>
                )}

                {qualityReport.issues.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-slate-400 mb-2">问题列表</h4>
                    <div className="space-y-2">
                      {qualityReport.issues.slice(0, 10).map((issue, idx) => (
                        <div
                          key={idx}
                          className="bg-slate-700/50 rounded-lg p-2 border-l-2"
                          style={{ borderColor: getSeverityColor(issue.severity) }}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-medium" style={{ color: getSeverityColor(issue.severity) }}>
                              {issue.severity.toUpperCase()}
                            </span>
                            <span className="text-xs text-slate-500">{issue.type}</span>
                          </div>
                          <p className="text-xs text-slate-300">{issue.description}</p>
                        </div>
                      ))}
                    </div>
                    {qualityReport.issues.length > 10 && (
                      <p className="text-xs text-slate-500 text-center mt-2">
                        还有 {qualityReport.issues.length - 10} 个问题...
                      </p>
                    )}
                  </div>
                )}

                {qualityReport.overlap_regions.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-xs font-semibold text-slate-400 mb-2">重叠区域</h4>
                    <div className="space-y-1 text-xs">
                      {qualityReport.overlap_regions.map((region, idx) => (
                        <div key={idx} className="text-slate-300">
                          区域 {idx + 1}: IoU {region.iou.toFixed(2)}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {qualityReport.missing_regions.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-xs font-semibold text-slate-400 mb-2">潜在漏标区域</h4>
                    <div className="space-y-1 text-xs">
                      {qualityReport.missing_regions.slice(0, 5).map((region, idx) => (
                        <div key={idx} className="text-slate-300">
                          ({region.x}, {region.y}) - {region.width}x{region.height}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {!qualityReport && (
              <div className="text-slate-500 text-sm text-center py-8">
                点击上方按钮开始质量检查
              </div>
            )}
          </div>
        )}

        {activeTab === 'versions' && (
          <div className="p-3">
            <h3 className="text-sm font-semibold text-slate-200 mb-3">版本管理</h3>
            
            <div className="bg-slate-700/50 rounded-lg p-3 mb-4">
              <input
                type="text"
                value={versionDescription}
                onChange={(e) => setVersionDescription(e.target.value)}
                placeholder="版本描述（可选）"
                className="w-full bg-slate-600 border border-slate-500 rounded px-2 py-1 text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-blue-500 mb-2"
              />
              <button
                onClick={handleSaveVersion}
                disabled={!currentImageId || annotations.length === 0 || isSavingVersion}
                className={`w-full py-2 rounded font-medium transition-colors ${
                  currentImageId && annotations.length > 0 && !isSavingVersion
                    ? 'bg-blue-600 hover:bg-blue-700 text-white'
                    : 'bg-slate-600 text-slate-400 cursor-not-allowed'
                }`}
              >
                {isSavingVersion ? '保存中...' : '保存当前版本'}
              </button>
            </div>

            {versions.length === 0 ? (
              <div className="text-slate-500 text-sm text-center py-8">
                暂无历史版本
              </div>
            ) : (
              <div className="space-y-2">
                {versions.map((version, idx) => (
                  <div
                    key={version.version_id}
                    className={`bg-slate-700/50 rounded-lg p-3 border ${
                      selectedVersion === version.version_id
                        ? 'border-blue-500 bg-blue-900/20'
                        : 'border-slate-600'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-slate-200">
                        版本 {versions.length - idx}
                      </span>
                      <span className="text-xs text-slate-500">
                        {formatDate(version.created_at)}
                      </span>
                    </div>
                    
                    {version.description && (
                      <p className="text-xs text-slate-400 mb-2">{version.description}</p>
                    )}
                    
                    <div className="flex items-center gap-2 text-xs text-slate-500 mb-2">
                      <span>{version.author}</span>
                      <span>·</span>
                      <span>{version.annotations.length} 个标注</span>
                      {version.metadata?.labels && (
                        <>
                          <span>·</span>
                          <span>{version.metadata.labels.length} 个标签</span>
                        </>
                      )}
                    </div>
                    
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleRollbackVersion(version.version_id)}
                        className="flex-1 py-1 bg-green-600 hover:bg-green-700 text-white text-xs rounded transition-colors"
                      >
                        回滚
                      </button>
                      <button
                        onClick={() => setSelectedVersion(
                          selectedVersion === version.version_id ? null : version.version_id
                        )}
                        className="flex-1 py-1 bg-slate-600 hover:bg-slate-500 text-slate-300 text-xs rounded transition-colors"
                      >
                        {selectedVersion === version.version_id ? '取消' : '查看'}
                      </button>
                      <button
                        onClick={() => handleDeleteVersion(version.version_id)}
                        className="py-1 px-2 bg-red-600/20 hover:bg-red-600/40 text-red-400 text-xs rounded transition-colors"
                      >
                        ×
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'video' && (
          <div className="p-3">
            <h3 className="text-sm font-semibold text-slate-200 mb-3">视频标注</h3>
            
            <div className="bg-slate-700/50 rounded-lg p-3 mb-4">
              <label className="block w-full py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm text-center rounded font-medium transition-colors cursor-pointer">
                上传视频
                <input
                  type="file"
                  accept="video/*"
                  onChange={handleVideoUpload}
                  className="hidden"
                />
              </label>
            </div>

            {videos.length > 0 && (
              <div className="mb-4">
                <h4 className="text-xs font-semibold text-slate-400 mb-2">视频列表</h4>
                <div className="space-y-2">
                  {videos.map(video => (
                    <div
                      key={video.id}
                      className={`bg-slate-700/50 rounded-lg p-2 border cursor-pointer ${
                        selectedVideo?.id === video.id
                          ? 'border-blue-500'
                          : 'border-slate-600 hover:border-slate-500'
                      }`}
                      onClick={() => setSelectedVideo(video)}
                    >
                      <div className="text-sm text-slate-200 truncate">{video.filename}</div>
                      <div className="text-xs text-slate-500">
                        {video.width}x{video.height} · {video.total_frames}帧 · {video.fps.toFixed(1)}fps
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selectedVideo && (
              <>
                <div className="bg-slate-700/50 rounded-lg p-3 mb-4">
                  <div className="text-xs text-slate-400 mb-2">
                    时长: {selectedVideo.duration.toFixed(1)}秒
                  </div>
                  <button
                    onClick={handleExtractKeyframes}
                    disabled={isExtractingKeyframes}
                    className={`w-full py-2 rounded font-medium transition-colors ${
                      !isExtractingKeyframes
                        ? 'bg-amber-600 hover:bg-amber-700 text-white'
                        : 'bg-slate-600 text-slate-400 cursor-not-allowed'
                    }`}
                  >
                    {isExtractingKeyframes ? '提取中...' : '提取关键帧'}
                  </button>
                </div>

                {keyframes.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-slate-400 mb-2">
                      关键帧 ({keyframes.length})
                    </h4>
                    <div className="max-h-48 overflow-y-auto space-y-1">
                      {keyframes.slice(0, 20).map((frame, idx) => (
                        <div
                          key={idx}
                          className={`bg-slate-700/50 rounded p-2 cursor-pointer hover:bg-slate-700 transition-colors ${
                            currentFrame === frame.frame_index ? 'border-l-2 border-blue-500' : ''
                          }`}
                          onClick={() => setCurrentFrame(frame.frame_index)}
                        >
                          <div className="text-xs text-slate-300">
                            帧 {frame.frame_index}
                          </div>
                          <div className="text-xs text-slate-500">
                            {frame.timestamp.toFixed(2)}s
                          </div>
                        </div>
                      ))}
                    </div>
                    {keyframes.length > 20 && (
                      <p className="text-xs text-slate-500 text-center mt-2">
                        还有 {keyframes.length - 20} 个关键帧...
                      </p>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === 'stats' && (
          <div className="p-3">
            <h3 className="text-sm font-semibold text-slate-200 mb-3">标注统计</h3>
            
            <div className="bg-slate-700/50 rounded-lg p-4 mb-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-400">{annotations.length}</div>
                  <div className="text-xs text-slate-400">标注总数</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-400">{labels.length}</div>
                  <div className="text-xs text-slate-400">标签数量</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-amber-400">{formatArea(totalPixels)}</div>
                  <div className="text-xs text-slate-400">总像素数</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-pink-400">
                    {annotations.filter(a => a.type === 'sam').length}
                  </div>
                  <div className="text-xs text-slate-400">SAM标注</div>
                </div>
              </div>
            </div>
            
            {samStats && (
              <div className="bg-slate-700/50 rounded-lg p-4 mb-4">
                <h4 className="text-xs font-semibold text-slate-400 mb-2">SAM 模型状态</h4>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">设备:</span>
                    <span className="text-slate-200">{samStats.device || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">模型:</span>
                    <span className="text-slate-200">{samStats.modelType || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">缓存命中率:</span>
                    <span className="text-green-400">
                      {samStats.cacheHitRate ? `${(samStats.cacheHitRate * 100).toFixed(1)}%` : 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">缓存数量:</span>
                    <span className="text-slate-200">{samStats.cacheSize || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">平均预测时间:</span>
                    <span className="text-slate-200">
                      {samStats.avgPredictionTime ? `${samStats.avgPredictionTime.toFixed(0)}ms` : 'N/A'}
                    </span>
                  </div>
                </div>
                <button
                  onClick={handleClearCache}
                  className="w-full mt-3 py-1.5 bg-slate-600 hover:bg-slate-500 text-slate-300 text-xs rounded transition-colors"
                >
                  清除缓存
                </button>
              </div>
            )}
            
            <div className="bg-slate-700/50 rounded-lg p-4">
              <h4 className="text-xs font-semibold text-slate-400 mb-3">按类型分布</h4>
              <div className="space-y-2">
                {['polygon', 'point', 'rectangle', 'brush', 'sam'].map(type => {
                  const count = annotations.filter(a => a.type === type).length;
                  const percentage = annotations.length > 0 
                    ? (count / annotations.length) * 100 
                    : 0;
                  return (
                    <div key={type}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-slate-400 capitalize">{type}</span>
                        <span className="text-slate-200">{count}</span>
                      </div>
                      <div className="h-1.5 bg-slate-600 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${percentage}%`,
                            backgroundColor: getTypeColor(type as any),
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar;
