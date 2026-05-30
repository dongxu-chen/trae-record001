import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import styled from 'styled-components';
import { templateApi, taskApi } from '../services/api';

const PageContainer = styled.div`
  max-width: 1400px;
  margin: 0 auto;
`;

const PageHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
`;

const Title = styled.h1`
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
`;

const Subtitle = styled.p`
  color: var(--text-secondary);
  margin-top: 4px;
  font-size: 14px;
`;

const FilterBar = styled.div`
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  align-items: center;
  flex-wrap: wrap;
`;

const FilterGroup = styled.div`
  display: flex;
  gap: 8px;
  align-items: center;
`;

const Label = styled.label`
  font-size: 13px;
  color: var(--text-secondary);
`;

const Select = styled.select`
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  
  &:focus {
    border-color: var(--accent-primary);
  }
`;

const Button = styled.button`
  padding: 8px 16px;
  border-radius: 6px;
  border: none;
  font-weight: 500;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
  
  ${props => props.primary ? `
    background-color: var(--accent-primary);
    color: white;
    
    &:hover {
      opacity: 0.9;
    }
  ` : `
    background-color: var(--bg-tertiary);
    color: var(--text-primary);
    
    &:hover {
      background-color: var(--border-color);
    }
  `}
  
  ${props => props.disabled && `
    opacity: 0.5;
    cursor: not-allowed;
  `}
`;

const TemplatesGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
`;

const TemplateCard = styled.div`
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 20px;
  transition: all 0.2s ease;
  
  &:hover {
    border-color: var(--accent-primary);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }
`;

const CardHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
`;

const TemplateName = styled.h3`
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
`;

const CategoryBadge = styled.span`
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 500;
  
  ${props => {
    const colors = {
      entity: '#4ECDC4',
      relation: '#45B7D1',
      event: '#F39C12',
      composite: '#9B59B6'
    };
    return `
      background-color: ${colors[props.category]}20;
      color: ${colors[props.category]};
    `;
  }}
`;

const TemplateDescription = styled.p`
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 16px;
`;

const TemplateStats = styled.div`
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
`;

const StatItem = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
`;

const StatValue = styled.span`
  font-weight: 600;
  color: var(--text-primary);
`;

const EntityLabels = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
`;

const EntityTag = styled.span`
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  background-color: ${props => props.color}20;
  color: ${props => props.color};
`;

const CardActions = styled.div`
  display: flex;
  gap: 8px;
  margin-top: 16px;
`;

const GlobalBadge = styled.span`
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
  background-color: var(--accent-primary);
  color: white;
  margin-left: 6px;
`;

const ModalOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
`;

const Modal = styled.div`
  background-color: var(--bg-secondary);
  border-radius: 12px;
  padding: 24px;
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
`;

const ModalTitle = styled.h2`
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
`;

const Input = styled.input`
  width: 100%;
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-primary);
  color: var(--text-primary);
  font-size: 13px;
  margin-bottom: 12px;
  outline: none;
  
  &:focus {
    border-color: var(--accent-primary);
  }
`;

const TextArea = styled.textarea`
  width: 100%;
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-primary);
  color: var(--text-primary);
  font-size: 13px;
  margin-bottom: 12px;
  min-height: 80px;
  resize: vertical;
  outline: none;
  
  &:focus {
    border-color: var(--accent-primary);
  }
`;

const Toast = styled.div`
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 12px 20px;
  border-radius: 8px;
  background-color: ${props => props.type === 'success' ? '#27ae60' : '#e74c3c'};
  color: white;
  font-size: 14px;
  font-weight: 500;
  z-index: 2000;
  animation: slideIn 0.3s ease;
  
  @keyframes slideIn {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 60px 20px;
  color: var(--text-secondary);
  
  h3 {
    color: var(--text-primary);
    margin-bottom: 8px;
  }
`;

const RatingStars = styled.div`
  display: flex;
  gap: 2px;
  align-items: center;
  
  span {
    cursor: pointer;
    font-size: 14px;
  }
`;

const TemplatesPage = () => {
  const { taskId } = useParams();
  const [templates, setTemplates] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [toast, setToast] = useState(null);
  const [task, setTask] = useState(null);
  const [newTemplate, setNewTemplate] = useState({
    name: '',
    description: '',
    category: 'entity',
    entities: [],
    relations: [],
    events: []
  });

  useEffect(() => {
    loadTemplates();
    if (taskId) {
      loadTask();
      loadSuggestions();
    }
  }, [taskId, category]);

  const loadTask = async () => {
    try {
      const res = await taskApi.getById(taskId);
      setTask(res.data);
    } catch (error) {
      console.error('Failed to load task:', error);
    }
  };

  const loadTemplates = async () => {
    try {
      setLoading(true);
      const params = {};
      if (category) params.category = category;
      if (taskId) params.taskId = taskId;
      
      const res = await templateApi.getAll(params);
      setTemplates(res.data);
    } catch (error) {
      console.error('Failed to load templates:', error);
      showToast('加载模板失败', 'error');
    } finally {
      setLoading(false);
    }
  };

  const loadSuggestions = async () => {
    try {
      const res = await templateApi.getSuggestions(taskId);
      setSuggestions(res.data);
    } catch (error) {
      console.error('Failed to load suggestions:', error);
    }
  };

  const applyTemplate = async (template) => {
    if (!taskId) {
      showToast('请先选择一个任务', 'error');
      return;
    }
    
    try {
      const res = await templateApi.apply(template._id, taskId);
      showToast(`成功应用模板：${res.data.appliedEntityCount}个实体标签，${res.data.appliedRelationCount}个关系类型，${res.data.appliedEventCount}个事件类型`, 'success');
    } catch (error) {
      showToast('应用模板失败: ' + error.response?.data?.error, 'error');
    }
  };

  const handleCreateTemplate = async () => {
    try {
      const data = {
        ...newTemplate,
        taskId: taskId || null,
        isGlobal: !taskId
      };
      await templateApi.create(data);
      setShowModal(false);
      loadTemplates();
      showToast('模板创建成功', 'success');
      setNewTemplate({
        name: '',
        description: '',
        category: 'entity',
        entities: [],
        relations: [],
        events: []
      });
    } catch (error) {
      showToast('创建失败: ' + error.response?.data?.error, 'error');
    }
  };

  const deleteTemplate = async (template) => {
    if (template.isGlobal) {
      showToast('无法删除系统模板', 'error');
      return;
    }
    
    if (window.confirm(`确定要删除模板"${template.name}"吗？`)) {
      try {
        await templateApi.delete(template._id);
        loadTemplates();
        showToast('模板已删除', 'success');
      } catch (error) {
        showToast('删除失败', 'error');
      }
    }
  };

  const rateTemplate = async (templateId, rating) => {
    try {
      await templateApi.rate(templateId, rating);
      loadTemplates();
      showToast('评分成功', 'success');
    } catch (error) {
      showToast('评分失败', 'error');
    }
  };

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const getCategoryLabel = (category) => {
    const labels = {
      entity: '实体',
      relation: '关系',
      event: '事件',
      composite: '综合'
    };
    return labels[category] || category;
  };

  return (
    <PageContainer>
      <PageHeader>
        <div>
          <Title>标注模板库</Title>
          <Subtitle>选择和管理常用的标注类型模板，快速开始标注任务</Subtitle>
        </div>
        <Button primary onClick={() => setShowModal(true)}>
          + 创建新模板
        </Button>
      </PageHeader>

      {suggestions.length > 0 && taskId && (
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ fontSize: '16px', marginBottom: '12px', color: 'var(--text-primary)' }}>
            🌟 推荐模板
          </h3>
          <TemplatesGrid>
            {suggestions.slice(0, 3).map(({ template, matchScore }) => (
              <TemplateCard key={template._id} style={{ borderColor: 'var(--accent-primary)' }}>
                <CardHeader>
                  <div>
                    <TemplateName>
                      {template.name}
                      {template.isGlobal && <GlobalBadge>官方</GlobalBadge>}
                    </TemplateName>
                    <span style={{ fontSize: '11px', color: 'var(--accent-primary)' }}>
                      匹配度: {matchScore}%
                    </span>
                  </div>
                  <CategoryBadge category={template.category}>
                    {getCategoryLabel(template.category)}
                  </CategoryBadge>
                </CardHeader>
                <TemplateDescription>{template.description}</TemplateDescription>
                <CardActions>
                  <Button primary onClick={() => applyTemplate(template)}>
                    应用模板
                  </Button>
                  <Button onClick={() => setSelectedTemplate(template)}>查看详情</Button>
                </CardActions>
              </TemplateCard>
            ))}
          </TemplatesGrid>
        </div>
      )}

      <FilterBar>
        <FilterGroup>
          <Label>分类:</Label>
          <Select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">全部</option>
            <option value="entity">实体模板</option>
            <option value="relation">关系模板</option>
            <option value="event">事件模板</option>
            <option value="composite">综合模板</option>
          </Select>
        </FilterGroup>
        <span style={{ color: 'var(--text-secondary)', fontSize: '13px', marginLeft: 'auto' }}>
          共 {templates.length} 个模板
        </span>
      </FilterBar>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
          加载中...
        </div>
      ) : templates.length === 0 ? (
        <EmptyState>
          <h3>暂无模板</h3>
          <p>点击"创建新模板"按钮创建第一个模板吧</p>
        </EmptyState>
      ) : (
        <TemplatesGrid>
          {templates.map(template => (
            <TemplateCard key={template._id}>
              <CardHeader>
                <div>
                  <TemplateName>
                    {template.name}
                    {template.isGlobal && <GlobalBadge>官方</GlobalBadge>}
                  </TemplateName>
                </div>
                <CategoryBadge category={template.category}>
                  {getCategoryLabel(template.category)}
                </CategoryBadge>
              </CardHeader>
              
              <TemplateDescription>{template.description}</TemplateDescription>
              
              <TemplateStats>
                <StatItem>
                  <StatValue>{template.entities.length}</StatValue> 实体
                </StatItem>
                <StatItem>
                  <StatValue>{template.relations.length}</StatValue> 关系
                </StatItem>
                <StatItem>
                  <StatValue>{template.events.length}</StatValue> 事件
                </StatItem>
                <StatItem>
                  <StatValue>{template.usageCount || 0}</StatValue> 使用
                </StatItem>
              </TemplateStats>
              
              {template.entities.length > 0 && (
                <EntityLabels>
                  {template.entities.slice(0, 6).map(entity => (
                    <EntityTag key={entity.label} color={entity.color}>
                      {entity.label}
                    </EntityTag>
                  ))}
                  {template.entities.length > 6 && (
                    <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                      +{template.entities.length - 6}
                    </span>
                  )}
                </EntityLabels>
              )}
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', justifyContent: 'space-between' }}>
                <RatingStars>
                  {[1, 2, 3, 4, 5].map(star => (
                    <span 
                      key={star}
                      onClick={() => rateTemplate(template._id, star)}
                      style={{ color: star <= (template.rating || 0) ? '#f1c40f' : 'var(--text-muted)' }}
                    >
                      ★
                    </span>
                  ))}
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)', marginLeft: '4px' }}>
                    ({template.ratingCount || 0})
                  </span>
                </RatingStars>
              </div>
              
              <CardActions>
                {taskId && (
                  <Button primary onClick={() => applyTemplate(template)}>
                    应用到任务
                  </Button>
                )}
                <Button onClick={() => setSelectedTemplate(template)}>查看</Button>
                {!template.isGlobal && (
                  <Button onClick={() => deleteTemplate(template)}>删除</Button>
                )}
              </CardActions>
            </TemplateCard>
          ))}
        </TemplatesGrid>
      )}

      {showModal && (
        <ModalOverlay onClick={() => setShowModal(false)}>
          <Modal onClick={e => e.stopPropagation()}>
            <ModalTitle>创建新模板</ModalTitle>
            
            <Input
              placeholder="模板名称"
              value={newTemplate.name}
              onChange={e => setNewTemplate({ ...newTemplate, name: e.target.value })}
            />
            
            <TextArea
              placeholder="模板描述"
              value={newTemplate.description}
              onChange={e => setNewTemplate({ ...newTemplate, description: e.target.value })}
            />
            
            <FilterGroup style={{ marginBottom: '12px' }}>
              <Label>模板类型:</Label>
              <Select 
                value={newTemplate.category}
                onChange={e => setNewTemplate({ ...newTemplate, category: e.target.value })}
              >
                <option value="entity">实体模板</option>
                <option value="relation">关系模板</option>
                <option value="event">事件模板</option>
                <option value="composite">综合模板</option>
              </Select>
            </FilterGroup>
            
            {task && (
              <div style={{ marginBottom: '12px' }}>
                <Label style={{ display: 'block', marginBottom: '8px' }}>从当前任务导入标签:</Label>
                <Button 
                  onClick={() => {
                    setNewTemplate({
                      ...newTemplate,
                      entities: task.entityTypes || [],
                      relations: task.relationTypes || [],
                      events: task.eventTypes || []
                    });
                  }}
                >
                  导入标签 ({task.entityTypes?.length || 0}实体, {task.relationTypes?.length || 0}关系)
                </Button>
              </div>
            )}
            
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '20px' }}>
              <Button onClick={() => setShowModal(false)}>取消</Button>
              <Button primary onClick={handleCreateTemplate} disabled={!newTemplate.name}>
                创建
              </Button>
            </div>
          </Modal>
        </ModalOverlay>
      )}

      {selectedTemplate && (
        <ModalOverlay onClick={() => setSelectedTemplate(null)}>
          <Modal onClick={e => e.stopPropagation()}>
            <ModalTitle>
              {selectedTemplate.name}
              {selectedTemplate.isGlobal && <GlobalBadge>官方模板</GlobalBadge>}
            </ModalTitle>
            
            <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
              {selectedTemplate.description}
            </p>
            
            {selectedTemplate.entities.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <h4 style={{ fontSize: '14px', marginBottom: '8px', color: 'var(--text-primary)' }}>实体类型 ({selectedTemplate.entities.length})</h4>
                {selectedTemplate.entities.map(entity => (
                  <div key={entity.label} style={{ 
                    display: 'flex', alignItems: 'center', gap: '8px', 
                    padding: '8px', background: 'var(--bg-primary)', 
                    borderRadius: '4px', marginBottom: '4px' 
                  }}>
                    <span style={{ 
                      width: '12px', height: '12px', borderRadius: '3px', 
                      background: entity.color 
                    }}></span>
                    <strong>{entity.label}</strong>
                    {entity.description && (
                      <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
                        - {entity.description}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
            
            {selectedTemplate.relations.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <h4 style={{ fontSize: '14px', marginBottom: '8px', color: 'var(--text-primary)' }}>关系类型 ({selectedTemplate.relations.length})</h4>
                {selectedTemplate.relations.map(rel => (
                  <div key={rel.label} style={{ 
                    padding: '8px', background: 'var(--bg-primary)', 
                    borderRadius: '4px', marginBottom: '4px' 
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ 
                        padding: '2px 6px', borderRadius: '3px', fontSize: '11px',
                        background: rel.color + '20', color: rel.color 
                      }}>
                        {rel.label}
                      </span>
                      <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                        {rel.sourceLabel} → {rel.targetLabel}
                      </span>
                    </div>
                    {rel.description && (
                      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        {rel.description}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
            
            {selectedTemplate.events.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <h4 style={{ fontSize: '14px', marginBottom: '8px', color: 'var(--text-primary)' }}>事件类型 ({selectedTemplate.events.length})</h4>
                {selectedTemplate.events.map(evt => (
                  <div key={evt.label} style={{ 
                    padding: '8px', background: 'var(--bg-primary)', 
                    borderRadius: '4px', marginBottom: '4px' 
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ 
                        padding: '2px 6px', borderRadius: '3px', fontSize: '11px',
                        background: evt.color + '20', color: evt.color 
                      }}>
                        {evt.label}
                      </span>
                    </div>
                    {evt.description && (
                      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        {evt.description}
                      </p>
                    )}
                    {evt.roleTypes?.length > 0 && (
                      <div style={{ marginTop: '6px' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                          角色:
                        </span>
                        {evt.roleTypes.map(role => (
                          <span key={role.role} style={{
                            fontSize: '11px', marginLeft: '4px',
                            padding: '1px 4px', background: 'var(--bg-tertiary)',
                            borderRadius: '2px'
                          }}>
                            {role.role} ({role.entityLabel})
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '20px' }}>
              {taskId && (
                <Button primary onClick={() => {
                  applyTemplate(selectedTemplate);
                  setSelectedTemplate(null);
                }}>
                  应用到此任务
                </Button>
              )}
              <Button onClick={() => setSelectedTemplate(null)}>关闭</Button>
            </div>
          </Modal>
        </ModalOverlay>
      )}

      {toast && (
        <Toast type={toast.type}>{toast.message}</Toast>
      )}
    </PageContainer>
  );
};

export default TemplatesPage;
