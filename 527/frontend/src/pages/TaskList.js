import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import styled from 'styled-components';
import { taskApi, documentApi, exportApi } from '../services/api';

const PageTitle = styled.h1`
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 24px;
  color: var(--text-primary);
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const CreateButton = styled.button`
  padding: 10px 20px;
  background-color: var(--accent-primary);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  
  &:hover {
    opacity: 0.9;
  }
`;

const TaskCard = styled.div`
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 16px;
  
  &:hover {
    border-color: var(--accent-primary);
  }
`;

const TaskHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
`;

const TaskName = styled.h3`
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 4px;
`;

const TaskDescription = styled.p`
  color: var(--text-secondary);
  font-size: 14px;
`;

const TaskStats = styled.div`
  display: flex;
  gap: 24px;
  margin: 16px 0;
  padding: 16px 0;
  border-top: 1px solid var(--border-color);
  border-bottom: 1px solid var(--border-color);
`;

const StatItem = styled.div`
  text-align: center;
  
  .stat-value {
    font-size: 24px;
    font-weight: 700;
    color: var(--accent-primary);
  }
  
  .stat-label {
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 4px;
  }
`;

const EntityTags = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
`;

const EntityTag = styled.span`
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  color: white;
  background-color: ${props => props.color || 'var(--bg-tertiary)'};
`;

const TaskActions = styled.div`
  display: flex;
  gap: 12px;
  margin-top: 16px;
`;

const ActionLink = styled(Link)`
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  background-color: ${props => props.primary ? 'var(--accent-primary)' : 'var(--bg-tertiary)'};
  color: white;
  
  &:hover {
    opacity: 0.9;
  }
`;

const Modal = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
`;

const ModalContent = styled.div`
  background-color: var(--bg-secondary);
  border-radius: 12px;
  padding: 32px;
  width: 100%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
`;

const ModalTitle = styled.h2`
  font-size: 22px;
  margin-bottom: 24px;
`;

const FormGroup = styled.div`
  margin-bottom: 20px;
  
  label {
    display: block;
    margin-bottom: 8px;
    font-size: 14px;
    font-weight: 500;
  }
  
  input, textarea {
    width: 100%;
    padding: 10px 14px;
    background-color: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    color: var(--text-primary);
    font-size: 14px;
    
    &:focus {
      outline: none;
      border-color: var(--accent-primary);
    }
  }
  
  textarea {
    resize: vertical;
    min-height: 80px;
  }
`;

const EntityTypeRow = styled.div`
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  align-items: center;
  
  input[type="text"] {
    flex: 1;
  }
  
  input[type="color"] {
    width: 50px;
    height: 38px;
    padding: 2px;
    cursor: pointer;
  }
  
  button {
    padding: 8px 12px;
    background-color: var(--error);
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 12px;
  }
`;

const ButtonRow = styled.div`
  display: flex;
  gap: 12px;
  margin-top: 24px;
  
  button {
    flex: 1;
    padding: 12px;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    border: none;
  }
  
  .cancel {
    background-color: var(--bg-tertiary);
    color: var(--text-primary);
  }
  
  .submit {
    background-color: var(--accent-primary);
    color: white;
  }
`;

const AddButton = styled.button`
  padding: 8px 16px;
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
  border: none;
  border-radius: 6px;
  font-size: 13px;
  margin-bottom: 12px;
  
  &:hover {
    background-color: var(--accent-secondary);
  }
`;

const DEFAULT_ENTITY_TYPES = [
  { label: 'PERSON', color: '#FF6B6B', description: '人物' },
  { label: 'ORGANIZATION', color: '#4ECDC4', description: '组织' },
  { label: 'LOCATION', color: '#45B7D1', description: '地点' },
  { label: 'DATE', color: '#96CEB4', description: '日期' },
  { label: 'EVENT', color: '#FFEAA7', description: '事件' }
];

const TaskList = () => {
  const [tasks, setTasks] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [taskStats, setTaskStats] = useState({});
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    entityTypes: [...DEFAULT_ENTITY_TYPES]
  });

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    try {
      const response = await taskApi.getAll();
      setTasks(response.data);
      
      const stats = {};
      for (const task of response.data) {
        try {
          const statsRes = await exportApi.getStats(task._id);
          stats[task._id] = statsRes.data;
        } catch (e) {
          stats[task._id] = { total: 0, annotated: 0 };
        }
      }
      setTaskStats(stats);
    } catch (error) {
      console.error('Error loading tasks:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await taskApi.create(formData);
      setShowModal(false);
      setFormData({
        name: '',
        description: '',
        entityTypes: [...DEFAULT_ENTITY_TYPES]
      });
      loadTasks();
    } catch (error) {
      console.error('Error creating task:', error);
    }
  };

  const handleAddEntityType = () => {
    setFormData({
      ...formData,
      entityTypes: [...formData.entityTypes, { label: '', color: '#CCCCCC', description: '' }]
    });
  };

  const handleRemoveEntityType = (index) => {
    const newEntityTypes = formData.entityTypes.filter((_, i) => i !== index);
    setFormData({ ...formData, entityTypes: newEntityTypes });
  };

  const handleEntityTypeChange = (index, field, value) => {
    const newEntityTypes = [...formData.entityTypes];
    newEntityTypes[index][field] = value;
    setFormData({ ...formData, entityTypes: newEntityTypes });
  };

  const handleAddSampleData = async (taskId) => {
    const sampleTexts = [
      { text: '张三在2024年1月15日加入了百度公司，担任高级工程师一职。他之前在阿里巴巴工作了5年，参与了多个重要项目。', meta: { source: 'sample' } },
      { text: '李明将于下周三前往北京参加人工智能研讨会，会议将在清华大学举行，预计有超过500名专家学者参加。', meta: { source: 'sample' } },
      { text: '华为公司宣布在深圳建立新的研发中心，投资总额达到50亿元人民币。该项目将创造超过3000个就业岗位。', meta: { source: 'sample' } },
      { text: '王教授在2023年发表了一篇关于自然语言处理的重要论文，该论文被国际顶级期刊收录。', meta: { source: 'sample' } },
      { text: '上海的张江高科技园区聚集了大量的科技企业，包括腾讯、字节跳动等知名公司都在这里设有分支机构。', meta: { source: 'sample' } }
    ];
    
    try {
      await documentApi.bulkCreate(taskId, sampleTexts);
      alert('示例数据添加成功！');
      loadTasks();
    } catch (error) {
      console.error('Error adding sample data:', error);
      alert('添加示例数据失败');
    }
  };

  const handleDeleteTask = async (taskId) => {
    if (confirm('确定要删除这个任务吗？')) {
      try {
        await taskApi.delete(taskId);
        loadTasks();
      } catch (error) {
        console.error('Error deleting task:', error);
      }
    }
  };

  return (
    <div>
      <PageTitle>
        任务管理
        <CreateButton onClick={() => setShowModal(true)}>
          <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
            <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
          </svg>
          创建任务
        </CreateButton>
      </PageTitle>

      {tasks.map(task => (
        <TaskCard key={task._id}>
          <TaskHeader>
            <div>
              <TaskName>{task.name}</TaskName>
              <TaskDescription>{task.description || '暂无描述'}</TaskDescription>
            </div>
            <button 
              onClick={() => handleDeleteTask(task._id)}
              style={{ 
                background: 'none', 
                border: 'none', 
                color: 'var(--error)', 
                cursor: 'pointer',
                fontSize: '18px'
              }}
            >
              ✕
            </button>
          </TaskHeader>
          
          <TaskStats>
            <StatItem>
              <div className="stat-value">{taskStats[task._id]?.total || 0}</div>
              <div className="stat-label">总文档</div>
            </StatItem>
            <StatItem>
              <div className="stat-value" style={{ color: 'var(--success)' }}>
                {taskStats[task._id]?.annotated || 0}
              </div>
              <div className="stat-label">已标注</div>
            </StatItem>
            <StatItem>
              <div className="stat-value" style={{ color: 'var(--warning)' }}>
                {taskStats[task._id]?.pending || 0}
              </div>
              <div className="stat-label">待标注</div>
            </StatItem>
            <StatItem>
              <div className="stat-value" style={{ color: 'var(--accent-secondary)' }}>
                {task.entityTypes?.length || 0}
              </div>
              <div className="stat-label">实体类型</div>
            </StatItem>
          </TaskStats>

          <div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
              实体类型:
            </div>
            <EntityTags>
              {task.entityTypes?.map((et, idx) => (
                <EntityTag key={idx} color={et.color}>
                  {et.label}
                </EntityTag>
              ))}
            </EntityTags>
          </div>

          <TaskActions>
            <ActionLink primary="true" to={`/annotate/${task._id}`}>
              开始标注
            </ActionLink>
            <ActionLink to={`/templates/${task._id}`}>
              📋 模板库
            </ActionLink>
            <ActionLink to={`/export/${task._id}`}>
              导出数据
            </ActionLink>
            <ActionLink to={`/consistency/${task._id}`}>
              一致性检查
            </ActionLink>
            <ActionLink to={`/quality/${task._id}`}>
              📊 质量评分
            </ActionLink>
            <ActionLink to={`/achievements/${task._id}`}>
              🏆 成就
            </ActionLink>
            <button 
              onClick={() => handleAddSampleData(task._id)}
              style={{
                padding: '8px 16px',
                border: 'none',
                borderRadius: '6px',
                fontSize: '13px',
                backgroundColor: 'var(--bg-tertiary)',
                color: 'var(--text-primary)',
                cursor: 'pointer'
              }}
            >
              添加示例数据
            </button>
          </TaskActions>
        </TaskCard>
      ))}

      {tasks.length === 0 && (
        <div style={{ 
          textAlign: 'center', 
          padding: '60px 20px', 
          color: 'var(--text-secondary)',
          backgroundColor: 'var(--bg-secondary)',
          borderRadius: '12px',
          border: '1px dashed var(--border-color)'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>📋</div>
          <p style={{ marginBottom: '8px' }}>还没有创建任何任务</p>
          <p style={{ fontSize: '14px' }}>点击上方按钮创建您的第一个标注任务</p>
        </div>
      )}

      {showModal && (
        <Modal onClick={() => setShowModal(false)}>
          <ModalContent onClick={e => e.stopPropagation()}>
            <ModalTitle>创建新任务</ModalTitle>
            
            <form onSubmit={handleSubmit}>
              <FormGroup>
                <label>任务名称</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={e => setFormData({ ...formData, name: e.target.value })}
                  placeholder="输入任务名称"
                  required
                />
              </FormGroup>
              
              <FormGroup>
                <label>任务描述</label>
                <textarea
                  value={formData.description}
                  onChange={e => setFormData({ ...formData, description: e.target.value })}
                  placeholder="输入任务描述"
                />
              </FormGroup>
              
              <FormGroup>
                <label>实体类型</label>
                {formData.entityTypes.map((et, idx) => (
                  <EntityTypeRow key={idx}>
                    <input
                      type="text"
                      value={et.label}
                      onChange={e => handleEntityTypeChange(idx, 'label', e.target.value)}
                      placeholder="类型名称"
                      required
                    />
                    <input
                      type="color"
                      value={et.color}
                      onChange={e => handleEntityTypeChange(idx, 'color', e.target.value)}
                    />
                    <button type="button" onClick={() => handleRemoveEntityType(idx)}>
                      删除
                    </button>
                  </EntityTypeRow>
                ))}
                <AddButton type="button" onClick={handleAddEntityType}>
                  + 添加实体类型
                </AddButton>
              </FormGroup>
              
              <ButtonRow>
                <button type="button" className="cancel" onClick={() => setShowModal(false)}>
                  取消
                </button>
                <button type="submit" className="submit">
                  创建任务
                </button>
              </ButtonRow>
            </form>
          </ModalContent>
        </Modal>
      )}
    </div>
  );
};

export default TaskList;
