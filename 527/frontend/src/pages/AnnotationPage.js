import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import { taskApi, documentApi, annotationApi, preAnnotateApi, qualityApi, achievementApi } from '../services/api';

const PageHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
`;

const PageTitle = styled.h1`
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
`;

const BackButton = styled.button`
  padding: 8px 16px;
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  
  &:hover {
    background-color: var(--accent-secondary);
  }
`;

const AnnotationContainer = styled.div`
  display: grid;
  grid-template-columns: 280px 1fr 300px;
  gap: 20px;
  height: calc(100vh - 180px);
`;

const LabelPanel = styled.div`
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  overflow-y: auto;
`;

const PanelTitle = styled.h3`
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--text-primary);
`;

const LabelSection = styled.div`
  margin-bottom: 24px;
`;

const SectionTitle = styled.h4`
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
`;

const LabelButton = styled.button`
  width: 100%;
  padding: 10px 14px;
  margin-bottom: 8px;
  background-color: ${props => props.selected ? props.color : 'var(--bg-tertiary)'};
  color: ${props => props.selected ? 'white' : 'var(--text-primary)'};
  border: 2px solid ${props => props.selected ? props.color : 'transparent'};
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    border-color: ${props => props.color};
  }
  
  .color-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background-color: ${props => props.color};
    margin-right: 10px;
  }
`;

const MainPanel = styled.div`
  display: flex;
  flex-direction: column;
  gap: 16px;
`;

const TextContainer = styled.div`
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 24px;
  flex: 1;
  overflow-y: auto;
`;

const TextContent = styled.div`
  font-size: 16px;
  line-height: 2;
  color: var(--text-primary);
  user-select: text;
  position: relative;
`;

const Toolbar = styled.div`
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
`;

const ToolbarLeft = styled.div`
  display: flex;
  gap: 8px;
`;

const ToolbarRight = styled.div`
  display: flex;
  gap: 8px;
`;

const ToolButton = styled.button`
  padding: 10px 16px;
  background-color: ${props => props.primary ? 'var(--accent-primary)' : 'var(--bg-tertiary)'};
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  
  &:hover {
    opacity: 0.9;
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const ModeSelector = styled.div`
  display: flex;
  background-color: var(--bg-tertiary);
  border-radius: 6px;
  padding: 4px;
  gap: 4px;
`;

const ModeButton = styled.button`
  padding: 8px 16px;
  background-color: ${props => props.active ? 'var(--accent-primary)' : 'transparent'};
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  
  &:hover {
    background-color: ${props => props.active ? 'var(--accent-primary)' : 'var(--bg-secondary)'};
  }
`;

const AnnotationsPanel = styled.div`
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  overflow-y: auto;
`;

const AnnotationItem = styled.div`
  padding: 12px;
  background-color: var(--bg-tertiary);
  border-radius: 6px;
  margin-bottom: 10px;
  border-left: 3px solid ${props => props.color};
  
  .entity-text {
    font-size: 13px;
    font-weight: 500;
    margin-bottom: 4px;
  }
  
  .entity-label {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 4px;
    background-color: ${props => props.color}40;
    color: ${props => props.color};
    display: inline-block;
  }
  
  .delete-btn {
    float: right;
    background: none;
    border: none;
    color: var(--error);
    cursor: pointer;
    font-size: 14px;
  }
`;

const ProgressBar = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background-color: var(--bg-secondary);
  border-radius: 6px;
  margin-bottom: 16px;
`;

const ProgressText = styled.span`
  font-size: 13px;
  color: var(--text-secondary);
`;

const ProgressFill = styled.div`
  flex: 1;
  height: 6px;
  background-color: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
  
  .fill {
    height: 100%;
    background-color: var(--accent-primary);
    transition: width 0.3s ease;
  }
`;

const RelationModeOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  padding: 12px;
  background-color: var(--accent-primary);
  color: white;
  text-align: center;
  font-size: 14px;
  font-weight: 500;
  z-index: 100;
`;

const UncertaintyIndicator = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background-color: ${props => {
    if (props.level === 'high') return 'var(--error)20';
    if (props.level === 'medium') return 'var(--warning)20';
    return 'var(--success)20';
  }};
  border-radius: 6px;
  border: 1px solid ${props => {
    if (props.level === 'high') return 'var(--error)';
    if (props.level === 'medium') return 'var(--warning)';
    return 'var(--success)';
  }};
  
  .label {
    font-size: 12px;
    font-weight: 500;
    color: ${props => {
      if (props.level === 'high') return 'var(--error)';
      if (props.level === 'medium') return 'var(--warning)';
      return 'var(--success)';
    }};
  }
  
  .value {
    font-size: 12px;
    color: var(--text-secondary);
    font-family: monospace;
  }
`;

const ModelInfoPanel = styled.div`
  background-color: var(--bg-tertiary);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
  
  .model-title {
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .model-version {
    font-size: 11px;
    color: var(--text-secondary);
    font-family: monospace;
  }
  
  .model-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    font-size: 11px;
  }
  
  .stat-item {
    display: flex;
    justify-content: space-between;
    color: var(--text-secondary);
  }
  
  .stat-value {
    color: var(--text-primary);
    font-weight: 500;
  }
`;

const SliderContainer = styled.div`
  margin-bottom: 16px;
  
  label {
    display: block;
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: 6px;
  }
  
  input[type="range"] {
    width: 100%;
    accent-color: var(--accent-primary);
  }
  
  .slider-value {
    float: right;
    color: var(--accent-primary);
    font-weight: 600;
  }
`;

const ToggleSwitch = styled.label`
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-size: 13px;
  
  input {
    display: none;
    
    &:checked + .slider {
      background-color: var(--accent-primary);
      
      &::before {
        transform: translateX(20px);
      }
    }
  }
  
  .slider {
    width: 44px;
    height: 24px;
    background-color: var(--bg-tertiary);
    border-radius: 12px;
    position: relative;
    transition: background-color 0.2s;
    
    &::before {
      content: '';
      position: absolute;
      width: 20px;
      height: 20px;
      background-color: white;
      border-radius: 50%;
      top: 2px;
      left: 2px;
      transition: transform 0.2s;
    }
  }
`;

const AnnotationPage = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const textRef = useRef(null);
  
  const [task, setTask] = useState(null);
  const [currentDocument, setCurrentDocument] = useState(null);
  const [annotations, setAnnotations] = useState({
    entities: [],
    relations: [],
    events: []
  });
  const [selectedLabel, setSelectedLabel] = useState(null);
  const [mode, setMode] = useState('entity');
  const [relationSource, setRelationSource] = useState(null);
  const [saving, setSaving] = useState(false);
  const [stats, setStats] = useState({ total: 0, annotated: 0 });
  
  const [activeLearningEnabled, setActiveLearningEnabled] = useState(true);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.3);
  const [samplingStrategy, setSamplingStrategy] = useState('uncertainty');
  const [uncertainty, setUncertainty] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);
  const [fineTuning, setFineTuning] = useState(false);
  const [modelInfoLoading, setModelInfoLoading] = useState(false);
  const [documentStartTime, setDocumentStartTime] = useState(Date.now());
  const [preAnnotateActions, setPreAnnotateActions] = useState({ accepted: 0, modified: 0, rejected: 0 });
  const [achievementToast, setAchievementToast] = useState(null);

  useEffect(() => {
    loadTask();
  }, [taskId]);

  useEffect(() => {
    if (task) {
      loadNextDocument();
      loadStats();
      loadModelInfo();
    }
  }, [task]);

  const loadTask = async () => {
    try {
      const response = await taskApi.getById(taskId);
      setTask(response.data);
      if (response.data.entityTypes?.length > 0) {
        setSelectedLabel(response.data.entityTypes[0]);
      }
    } catch (error) {
      console.error('Error loading task:', error);
    }
  };

  const loadModelInfo = async () => {
    setModelInfoLoading(true);
    try {
      const response = await preAnnotateApi.getModelInfo(taskId);
      setModelInfo(response.data);
    } catch (error) {
      console.error('Error loading model info:', error);
    }
    setModelInfoLoading(false);
  };

  const loadStats = async () => {
    try {
      const response = await exportApi.getStats(taskId);
      setStats({
        total: response.data.total || 0,
        annotated: response.data.annotated || 0
      });
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const loadNextDocument = async (currentId = '') => {
    try {
      let response;
      if (activeLearningEnabled) {
        response = await preAnnotateApi.getNextUncertainDocument(taskId, {
          sampleSize: 20,
          strategy: samplingStrategy
        });
        if (response.data) {
          setUncertainty(response.data.uncertainty);
        }
      } else {
        response = await documentApi.getNext(taskId, currentId);
        setUncertainty(null);
      }
      
      if (response.data) {
        setCurrentDocument(response.data);
        loadAnnotations(response.data._id);
      } else {
        alert('没有更多待标注的文档了！');
      }
    } catch (error) {
      console.error('Error loading document:', error);
    }
  };

  const handleFineTune = async () => {
    if (!confirm('确定要使用已标注数据微调模型吗？')) return;
    
    setFineTuning(true);
    try {
      const response = await preAnnotateApi.fineTune(taskId);
      alert(`模型微调成功！\n版本: ${response.data.version}\n学习了 ${response.data.learnedLabels.length} 种标签\n新增 ${response.data.newKeywordsCount} 个关键词`);
      loadModelInfo();
    } catch (error) {
      console.error('Error fine-tuning:', error);
      alert('模型微调失败: ' + error.response?.data?.error || error.message);
    }
    setFineTuning(false);
  };

  const loadAnnotations = async (documentId) => {
    try {
      const response = await annotationApi.getByDocument(documentId, taskId);
      setAnnotations({
        entities: response.data.entities || [],
        relations: response.data.relations || [],
        events: response.data.events || []
      });
    } catch (error) {
      setAnnotations({ entities: [], relations: [], events: [] });
    }
  };

  const handleTextSelection = useCallback(() => {
    if (mode !== 'entity' || !selectedLabel) return;
    
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) return;
    
    const range = selection.getRangeAt(0);
    const text = selection.toString().trim();
    
    if (!text || text.length < 1) return;

    const container = textRef.current;
    if (!container) return;

    const preSelectionRange = document.createRange();
    preSelectionRange.selectNodeContents(container);
    preSelectionRange.setEnd(range.startContainer, range.startOffset);
    const start = preSelectionRange.toString().length;
    const end = start + text.length;

    const overlaps = annotations.entities.some(e => 
      (start >= e.start && start < e.end) || 
      (end > e.start && end <= e.end) ||
      (start < e.start && end > e.end)
    );

    if (overlaps) {
      alert('不能与已有实体重叠！');
      selection.removeAllRanges();
      return;
    }

    const newEntity = {
      id: `entity-${Date.now()}`,
      start,
      end,
      text,
      label: selectedLabel.label,
      color: selectedLabel.color,
      isPreAnnotated: false
    };

    setAnnotations(prev => ({
      ...prev,
      entities: [...prev.entities, newEntity]
    }));

    selection.removeAllRanges();
  }, [mode, selectedLabel, annotations.entities]);

  const handleEntityClick = (entity, e) => {
    e.stopPropagation();
    
    if (mode === 'entity') {
      if (confirm(`删除实体 "${entity.text}"?`)) {
        setAnnotations(prev => ({
          ...prev,
          entities: prev.entities.filter(en => en.id !== entity.id),
          relations: prev.relations.filter(r => 
            r.sourceId !== entity.id && r.targetId !== entity.id
          )
        }));
      }
    } else if (mode === 'relation') {
      if (!relationSource) {
        setRelationSource(entity);
      } else if (relationSource.id !== entity.id) {
        const label = prompt('请输入关系类型:');
        if (label) {
          const newRelation = {
            id: `relation-${Date.now()}`,
            sourceId: relationSource.id,
            targetId: entity.id,
            label,
            color: '#9b59b6'
          };
          setAnnotations(prev => ({
            ...prev,
            relations: [...prev.relations, newRelation]
          }));
        }
        setRelationSource(null);
      } else {
        setRelationSource(null);
      }
    }
  };

  const renderAnnotatedText = () => {
    if (!currentDocument) return null;
    
    const text = currentDocument.text;
    const sortedEntities = [...annotations.entities].sort((a, b) => a.start - b.start);
    
    let lastIndex = 0;
    const parts = [];
    
    sortedEntities.forEach((entity, idx) => {
      if (entity.start > lastIndex) {
        parts.push({
          type: 'text',
          content: text.slice(lastIndex, entity.start)
        });
      }
      
      parts.push({
        type: 'entity',
        content: text.slice(entity.start, entity.end),
        entity
      });
      
      lastIndex = entity.end;
    });
    
    if (lastIndex < text.length) {
      parts.push({
        type: 'text',
        content: text.slice(lastIndex)
      });
    }
    
    return parts.map((part, idx) => {
      if (part.type === 'text') {
        return <span key={idx}>{part.content}</span>;
      } else {
        return (
          <span
            key={idx}
            className={`entity-highlight ${part.entity.isPreAnnotated ? 'pre-annotated' : ''}`}
            style={{
              backgroundColor: `${part.entity.color}40`,
              borderBottom: `2px solid ${part.entity.color}`,
              outline: relationSource?.id === part.entity.id ? '2px solid white' : 'none'
            }}
            onClick={(e) => handleEntityClick(part.entity, e)}
          >
            {part.content}
          </span>
        );
      }
    });
  };

  const updateQualityAndAchievements = async () => {
    try {
      const timeSpent = Math.round((Date.now() - documentStartTime) / 1000);
      
      const annotationStats = {
        entities: annotations.entities?.length || 0,
        relations: annotations.relations?.length || 0,
        events: annotations.events?.length || 0
      };
      
      await qualityApi.update({
        annotator: 'default_user',
        taskId,
        annotationStats,
        timeSpent,
        preAnnotateActions
      });
      
      const updates = [
        { type: 'annotations', value: annotationStats.entities + annotationStats.relations + annotationStats.events },
        { type: 'entities', value: annotationStats.entities },
        { type: 'relations', value: annotationStats.relations }
      ];
      
      const achRes = await achievementApi.updateProgress({
        annotator: 'default_user',
        taskId,
        updates
      });
      
      if (achRes.data.newlyUnlocked?.length > 0) {
        const achievement = achRes.data.newlyUnlocked[0];
        setAchievementToast(achievement);
        setTimeout(() => setAchievementToast(null), 3000);
      }
      
      setDocumentStartTime(Date.now());
      setPreAnnotateActions({ accepted: 0, modified: 0, rejected: 0 });
    } catch (error) {
      console.error('Error updating quality:', error);
    }
  };

  const handleSave = async () => {
    if (!currentDocument) return;
    
    setSaving(true);
    try {
      await annotationApi.save(currentDocument._id, {
        ...annotations,
        taskId,
        annotator: 'user'
      });
      await updateQualityAndAchievements();
      loadStats();
      alert('保存成功！');
    } catch (error) {
      console.error('Error saving:', error);
      alert('保存失败');
    }
    setSaving(false);
  };

  const handleNext = async () => {
    if (!currentDocument) return;
    
    try {
      await annotationApi.save(currentDocument._id, {
        ...annotations,
        taskId,
        annotator: 'user'
      });
      await updateQualityAndAchievements();
      loadNextDocument(currentDocument._id);
      loadStats();
    } catch (error) {
      console.error('Error saving:', error);
    }
  };

  const handlePreAnnotate = async () => {
    if (!currentDocument) return;
    
    try {
      const response = await preAnnotateApi.preAnnotateDocument(
        currentDocument._id,
        {
          useActiveLearning: activeLearningEnabled,
          confidenceThreshold
        }
      );
      setAnnotations(prev => ({
        ...prev,
        entities: [...prev.entities, ...response.data.entities]
      }));
      setUncertainty(response.data.uncertainty);
    } catch (error) {
      console.error('Error pre-annotating:', error);
      alert('预标注失败');
    }
  };

  const getUncertaintyLevel = (value) => {
    if (value === null || value === undefined) return 'low';
    if (value > 0.7) return 'high';
    if (value > 0.4) return 'medium';
    return 'low';
  };

  const getUncertaintyText = (value) => {
    const level = getUncertaintyLevel(value);
    if (level === 'high') return '高不确定性 ⚠️';
    if (level === 'medium') return '中等不确定性';
    return '低不确定性 ✅';
  };

  const handleSkip = () => {
    if (currentDocument) {
      loadNextDocument(currentDocument._id);
    }
  };

  const deleteRelation = (relationId) => {
    setAnnotations(prev => ({
      ...prev,
      relations: prev.relations.filter(r => r.id !== relationId)
    }));
  };

  const getEntityById = (id) => annotations.entities.find(e => e.id === id);

  return (
    <div>
      {mode === 'relation' && relationSource && (
        <RelationModeOverlay>
          关系标注模式 - 已选择源实体: {relationSource.text} - 点击目标实体完成关系
        </RelationModeOverlay>
      )}
      
      <PageHeader>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16px }}>
          <BackButton onClick={() => navigate('/tasks')}>
            <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
              <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/>
            </svg>
            返回
          </BackButton>
          <PageTitle>{task?.name || '标注工具'}</PageTitle>
        </div>
      </PageHeader>

      <ProgressBar>
        <ProgressText>
          进度: {stats.annotated} / {stats.total}
        </ProgressText>
        <ProgressFill>
          <div 
            className="fill" 
            style={{ width: `${stats.total > 0 ? (stats.annotated / stats.total * 100) : 0}%` }}
          />
        </ProgressFill>
        {uncertainty !== null && (
          <UncertaintyIndicator level={getUncertaintyLevel(uncertainty)}>
            <span className="label">{getUncertaintyText(uncertainty)}</span>
            <span className="value">{(uncertainty * 100).toFixed(1)}%</span>
          </UncertaintyIndicator>
        )}
      </ProgressBar>

      <AnnotationContainer>
        <LabelPanel>
          <PanelTitle>主动学习</PanelTitle>
          
          <ModelInfoPanel>
            <div className="model-title">
              <span>模型状态</span>
              <span className="model-version">v{modelInfo?.version || '1.0.0'}</span>
            </div>
            <div className="model-stats">
              <div className="stat-item">
                <span>已标注:</span>
                <span className="stat-value">{modelInfo?.totalAnnotations || 0}</span>
              </div>
              <div className="stat-item">
                <span>学习标签:</span>
                <span className="stat-value">{modelInfo?.learnedLabels?.length || 0}</span>
              </div>
            </div>
            <button
              onClick={handleFineTune}
              disabled={fineTuning || (modelInfo?.totalAnnotations || 0) < 5}
              style={{
                width: '100%',
                padding: '8px',
                marginTop: '10px',
                backgroundColor: (modelInfo?.totalAnnotations || 0) < 5 ? 'var(--bg-tertiary)' : 'var(--accent-secondary)',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                fontSize: '12px',
                cursor: (modelInfo?.totalAnnotations || 0) < 5 ? 'not-allowed' : 'pointer',
                opacity: (modelInfo?.totalAnnotations || 0) < 5 ? 0.5 : 1
              }}
            >
              {fineTuning ? '🔄 微调中...' : '🔧 微调模型'}
            </button>
            {(modelInfo?.totalAnnotations || 0) < 5 && (
              <p style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '6px' }}>
                至少需要 5 条标注数据
              </p>
            )}
          </ModelInfoPanel>

          <LabelSection>
            <SectionTitle>主动学习设置</SectionTitle>
            
            <ToggleSwitch style={{ marginBottom: '16px' }}>
              <input
                type="checkbox"
                checked={activeLearningEnabled}
                onChange={(e) => setActiveLearningEnabled(e.target.checked)}
              />
              <span className="slider" />
              <span>启用主动学习</span>
            </ToggleSwitch>

            <SliderContainer>
              <label>
                置信度阈值
                <span className="slider-value">{confidenceThreshold}</span>
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={confidenceThreshold}
                onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                disabled={!activeLearningEnabled}
              />
            </SliderContainer>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                采样策略
              </label>
              <select
                value={samplingStrategy}
                onChange={(e) => setSamplingStrategy(e.target.value)}
                disabled={!activeLearningEnabled}
                style={{
                  width: '100%',
                  padding: '8px 10px',
                  backgroundColor: 'var(--bg-primary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '4px',
                  color: 'var(--text-primary)',
                  fontSize: '13px'
                }}
              >
                <option value="uncertainty">不确定性优先</option>
                <option value="diversity">多样性优先</option>
                <option value="hybrid">混合策略</option>
              </select>
            </div>
          </LabelSection>

          <PanelTitle>标签面板</PanelTitle>
          
          <LabelSection>
            <SectionTitle>实体类型</SectionTitle>
            {task?.entityTypes?.map((et, idx) => (
              <LabelButton
                key={idx}
                color={et.color}
                selected={selectedLabel?.label === et.label && mode === 'entity'}
                onClick={() => {
                  setSelectedLabel(et);
                  setMode('entity');
                }}
              >
                <span className="color-dot" />
                {et.label}
              </LabelButton>
            ))}
          </LabelSection>

          <LabelSection>
            <SectionTitle>其他操作</SectionTitle>
            <LabelButton
              color="#9b59b6"
              selected={mode === 'relation'}
              onClick={() => {
                setMode('relation');
                setRelationSource(null);
              }}
            >
              <span className="color-dot" style={{ backgroundColor: '#9b59b6' }} />
              关系标注
            </LabelButton>
          </LabelSection>
        </LabelPanel>

        <MainPanel>
          <Toolbar>
            <ToolbarLeft>
              <ModeSelector>
                <ModeButton active={mode === 'entity'} onClick={() => setMode('entity')}>
                  实体
                </ModeButton>
                <ModeButton active={mode === 'relation'} onClick={() => {
                  setMode('relation');
                  setRelationSource(null);
                }}>
                  关系
                </ModeButton>
              </ModeSelector>
            </ToolbarLeft>
            <ToolbarRight>
              <ToolButton onClick={handlePreAnnotate}>
                🔮 自动预标注
              </ToolButton>
              <ToolButton onClick={handleSkip}>
                ⏭️ 跳过
              </ToolButton>
              <ToolButton onClick={handleSave} disabled={saving}>
                💾 保存
              </ToolButton>
              <ToolButton primary onClick={handleNext}>
                下一篇 →
              </ToolButton>
            </ToolbarRight>
          </Toolbar>

          <TextContainer>
            <TextContent ref={textRef} onMouseUp={handleTextSelection}>
              {renderAnnotatedText()}
            </TextContent>
          </TextContainer>

          <div style={{ 
            padding: '12px', 
            backgroundColor: 'var(--bg-secondary)', 
            borderRadius: '6px',
            fontSize: '13px',
            color: 'var(--text-secondary)'
          }}>
            💡 提示: 在文本中拖拽选择文字来标注实体。点击已标注的实体可以删除它。
            {mode === 'relation' && ' 切换到关系模式后，依次点击两个实体来创建关系。'}
          </div>
        </MainPanel>

        <AnnotationsPanel>
          <PanelTitle>已标注内容</PanelTitle>
          
          <LabelSection>
            <SectionTitle>实体 ({annotations.entities.length})</SectionTitle>
            {annotations.entities.map(entity => (
              <AnnotationItem key={entity.id} color={entity.color}>
                <button 
                  className="delete-btn"
                  onClick={() => {
                    setAnnotations(prev => ({
                      ...prev,
                      entities: prev.entities.filter(e => e.id !== entity.id),
                      relations: prev.relations.filter(r => 
                        r.sourceId !== entity.id && r.targetId !== entity.id
                      )
                    }));
                  }}
                >
                  ✕
                </button>
                <div className="entity-text">{entity.text}</div>
                <span className="entity-label">{entity.label}</span>
                {entity.isPreAnnotated && (
                  <span style={{ fontSize: '10px', marginLeft: '8px', color: 'var(--warning)' }}>
                    (预标注)
                  </span>
                )}
              </AnnotationItem>
            ))}
            {annotations.entities.length === 0 && (
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                暂无实体标注
              </p>
            )}
          </LabelSection>

          <LabelSection>
            <SectionTitle>关系 ({annotations.relations.length})</SectionTitle>
            {annotations.relations.map(relation => {
              const source = getEntityById(relation.sourceId);
              const target = getEntityById(relation.targetId);
              return (
                <AnnotationItem key={relation.id} color={relation.color}>
                  <button 
                    className="delete-btn"
                    onClick={() => deleteRelation(relation.id)}
                  >
                    ✕
                  </button>
                  <div className="entity-text">
                    {source?.text} → {target?.text}
                  </div>
                  <span className="entity-label">{relation.label}</span>
                </AnnotationItem>
              );
            })}
            {annotations.relations.length === 0 && (
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                暂无关系标注
              </p>
            )}
          </LabelSection>
        </AnnotationsPanel>
      </AnnotationContainer>

      {achievementToast && (
        <AchievementToast>
          <ToastIcon>{achievementToast.achievement.icon}</ToastIcon>
          <ToastContent>
            <ToastTitle>🎉 成就解锁！</ToastTitle>
            <ToastName>{achievementToast.achievement.name}</ToastName>
            <ToastPoints>+{achievementToast.achievement.points} 积分</ToastPoints>
          </ToastContent>
        </AchievementToast>
      )}
    </div>
  );
};

const AchievementToast = styled.div`
  position: fixed;
  top: 100px;
  right: 24px;
  background: linear-gradient(135deg, var(--accent-primary), #667eea);
  color: white;
  padding: 16px 24px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 16px;
  z-index: 2000;
  animation: slideInRight 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
  box-shadow: 0 10px 40px rgba(99, 102, 241, 0.4);
  
  @keyframes slideInRight {
    from {
      transform: translateX(120%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
`;

const ToastIcon = styled.div`
  font-size: 40px;
`;

const ToastContent = styled.div`
  display: flex;
  flex-direction: column;
`;

const ToastTitle = styled.div`
  font-size: 12px;
  opacity: 0.9;
  margin-bottom: 2px;
`;

const ToastName = styled.div`
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 2px;
`;

const ToastPoints = styled.div`
  font-size: 13px;
  opacity: 0.8;
`;

export default AnnotationPage;
