import React, { useState } from 'react';

const mockTemplates = [
  {
    id: 'template-env-prod',
    name: '生产环境资源',
    description: '生产环境所有资源自动打标',
    tags: { Environment: 'Production', CostCenter: 'CC100' },
    autoApply: true,
    priority: 100,
    conditions: { resourceTypes: [], accountIds: [], namePattern: 'prod', regions: [] },
    enabled: true,
  },
  {
    id: 'template-env-dev',
    name: '开发环境资源',
    description: '开发环境所有资源自动打标',
    tags: { Environment: 'Development', CostCenter: 'CC200' },
    autoApply: true,
    priority: 90,
    conditions: { resourceTypes: [], accountIds: [], namePattern: 'dev', regions: [] },
    enabled: true,
  },
  {
    id: 'template-ecs-standard',
    name: 'ECS标准标签',
    description: 'ECS服务器标准标签集',
    tags: { Department: 'Engineering', Owner: 'devops@example.com' },
    autoApply: true,
    priority: 80,
    conditions: { resourceTypes: ['ECS'], accountIds: [], namePattern: '', regions: [] },
    enabled: true,
  },
  {
    id: 'template-rds-database',
    name: '数据库标准标签',
    description: 'RDS数据库标准标签集',
    tags: { Department: 'Data', Backup: 'Enabled' },
    autoApply: true,
    priority: 80,
    conditions: { resourceTypes: ['RDS'], accountIds: [], namePattern: '', regions: [] },
    enabled: true,
  },
  {
    id: 'template-oss-storage',
    name: '存储标准标签',
    description: 'OSS存储标准标签集',
    tags: { Department: 'Engineering', Retention: '30days' },
    autoApply: true,
    priority: 80,
    conditions: { resourceTypes: ['OSS'], accountIds: [], namePattern: '', regions: [] },
    enabled: true,
  },
  {
    id: 'template-finance-resources',
    name: '财务系统资源',
    description: '财务相关资源自动打标',
    tags: { Department: 'Finance', Compliance: 'Strict' },
    autoApply: true,
    priority: 95,
    conditions: { resourceTypes: [], accountIds: [], namePattern: 'finance|fin-|pay', regions: [] },
    enabled: true,
  },
];

const TagTemplates = () => {
  const [templates, setTemplates] = useState(mockTemplates);
  const [showModal, setShowModal] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [newTemplate, setNewTemplate] = useState({
    name: '',
    description: '',
    tags: {},
    autoApply: true,
    priority: 50,
    conditions: { resourceTypes: [], accountIds: [], namePattern: '', regions: [] },
    enabled: true,
  });
  const [tagInput, setTagInput] = useState({ key: '', value: '' });

  const handleAddTag = () => {
    if (tagInput.key && tagInput.value) {
      setNewTemplate({
        ...newTemplate,
        tags: { ...newTemplate.tags, [tagInput.key]: tagInput.value },
      });
      setTagInput({ key: '', value: '' });
    }
  };

  const handleRemoveTag = (key) => {
    const newTags = { ...newTemplate.tags };
    delete newTags[key];
    setNewTemplate({ ...newTemplate, tags: newTags });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const templateToSave = {
      ...newTemplate,
      id: editingTemplate?.id || 'template-' + Date.now(),
    };

    if (editingTemplate) {
      setTemplates(templates.map(t => t.id === editingTemplate.id ? templateToSave : t));
    } else {
      setTemplates([...templates, templateToSave]);
    }

    setShowModal(false);
    setEditingTemplate(null);
    setNewTemplate({
      name: '',
      description: '',
      tags: {},
      autoApply: true,
      priority: 50,
      conditions: { resourceTypes: [], accountIds: [], namePattern: '', regions: [] },
      enabled: true,
    });
  };

  const handleEdit = (template) => {
    setEditingTemplate(template);
    setNewTemplate({ ...template });
    setShowModal(true);
  };

  const handleToggle = (id) => {
    setTemplates(templates.map(t =>
      t.id === id ? { ...t, enabled: !t.enabled } : t
    ));
  };

  const handleDelete = (id) => {
    if (confirm('确定要删除这个模板吗？')) {
      setTemplates(templates.filter(t => t.id !== id));
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>🏷️ 标签模板管理</h1>
          <p className="page-subtitle">配置标签模板，新建资源自动打标</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          + 新建模板
        </button>
      </div>

      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: '1.5rem' }}>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#3b82f6' }}>{templates.length}</div>
          <div className="stat-label">模板总数</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#10b981' }}>{templates.filter(t => t.enabled && t.autoApply).length}</div>
          <div className="stat-label">自动应用</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#8b5cf6' }}>3</div>
          <div className="stat-label">资源类型覆盖</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#f59e0b' }}>6</div>
          <div className="stat-label">标签数量</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1.5rem' }}>
        {templates.map(template => (
          <div key={template.id} className="card">
            <div className="card-header">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    background: template.enabled ? '#10b981' : '#9ca3af',
                  }} />
                  <span style={{ fontWeight: '600', color: '#111827' }}>{template.name}</span>
                  {template.autoApply && (
                    <span className="badge" style={{ background: '#dbeafe', color: '#1d4ed8', fontSize: '0.7rem' }}>
                      自动应用
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <label className="switch" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={template.enabled}
                      onChange={() => handleToggle(template.id)}
                      style={{
                        width: '40px',
                        height: '20px',
                        appearance: 'none',
                        background: template.enabled ? '#3b82f6' : '#d1d5db',
                        borderRadius: '10px',
                        position: 'relative',
                        cursor: 'pointer',
                      }}
                    />
                  </label>
                </div>
              </div>
            </div>
            <div style={{ padding: '1.5rem' }}>
              <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem' }}>
                {template.description}
              </p>

              <div style={{ marginBottom: '1rem' }}>
                <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.5rem', fontWeight: '500' }}>
                  标签集合
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {Object.entries(template.tags).map(([key, value]) => (
                    <span key={key} style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                      padding: '0.25rem 0.5rem',
                      background: '#f3f4f6',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                    }}>
                      <span style={{ color: '#3b82f6', fontWeight: '500' }}>{key}</span>
                      <span style={{ color: '#6b7280' }}>=</span>
                      <span style={{ color: '#111827' }}>{value}</span>
                    </span>
                  ))}
                </div>
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.5rem', fontWeight: '500' }}>
                  匹配条件
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', fontSize: '0.75rem' }}>
                  {template.conditions.resourceTypes?.length > 0 && (
                    <span className="badge" style={{ background: '#ede9fe', color: '#7c3aed' }}>
                      资源类型: {template.conditions.resourceTypes.join(', ')}
                    </span>
                  )}
                  {template.conditions.namePattern && (
                    <span className="badge" style={{ background: '#dbeafe', color: '#1d4ed8' }}>
                      名称模式: {template.conditions.namePattern}
                    </span>
                  )}
                  {!template.conditions.resourceTypes?.length && !template.conditions.namePattern && (
                    <span className="badge" style={{ background: '#f3f4f6', color: '#6b7280' }}>
                      无匹配条件（全部资源）
                    </span>
                  )}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                  优先级: {template.priority}
                </span>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    className="btn btn-secondary"
                    style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem' }}
                    onClick={() => handleEdit(template)}
                  >
                    编辑
                  </button>
                  <button
                    className="btn btn-secondary"
                    style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem', color: '#ef4444' }}
                    onClick={() => handleDelete(template.id)}
                  >
                    删除
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" style={{ maxWidth: '600px' }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">{editingTemplate ? '编辑模板' : '新建模板'}</span>
              <button className="modal-close" onClick={() => setShowModal(false)}>×</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div style={{ padding: '1.5rem' }}>
                <div className="form-group">
                  <label>模板名称</label>
                  <input
                    type="text"
                    value={newTemplate.name}
                    onChange={(e) => setNewTemplate({ ...newTemplate, name: e.target.value })}
                    placeholder="例如: 生产环境标准标签"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>模板描述</label>
                  <textarea
                    value={newTemplate.description}
                    onChange={(e) => setNewTemplate({ ...newTemplate, description: e.target.value })}
                    placeholder="描述这个模板的用途..."
                    rows="2"
                  />
                </div>

                <div className="form-group">
                  <label>标签集合</label>
                  <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
                    <input
                      type="text"
                      placeholder="标签键"
                      value={tagInput.key}
                      onChange={(e) => setTagInput({ ...tagInput, key: e.target.value })}
                      style={{ flex: 1 }}
                    />
                    <input
                      type="text"
                      placeholder="标签值"
                      value={tagInput.value}
                      onChange={(e) => setTagInput({ ...tagInput, value: e.target.value })}
                      style={{ flex: 1 }}
                    />
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={handleAddTag}
                    >
                      添加
                    </button>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {Object.entries(newTemplate.tags).map(([key, value]) => (
                      <span key={key} style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        padding: '0.375rem 0.75rem',
                        background: '#f3f4f6',
                        borderRadius: '4px',
                        fontSize: '0.8rem',
                      }}>
                        <span style={{ fontWeight: '500' }}>{key}</span>
                        <span style={{ color: '#9ca3af' }}>=</span>
                        <span>{value}</span>
                        <button
                          type="button"
                          onClick={() => handleRemoveTag(key)}
                          style={{
                            background: 'none',
                            border: 'none',
                            color: '#ef4444',
                            cursor: 'pointer',
                            padding: 0,
                            fontSize: '1rem',
                          }}
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>自动应用</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', paddingTop: '0.5rem' }}>
                      <input
                        type="checkbox"
                        checked={newTemplate.autoApply}
                        onChange={(e) => setNewTemplate({ ...newTemplate, autoApply: e.target.checked })}
                      />
                      <span style={{ fontSize: '0.875rem' }}>新建资源时自动应用此模板</span>
                    </div>
                  </div>
                  <div className="form-group">
                    <label>优先级</label>
                    <input
                      type="number"
                      value={newTemplate.priority}
                      onChange={(e) => setNewTemplate({ ...newTemplate, priority: parseInt(e.target.value) || 0 })}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label>匹配条件 - 资源类型（多选，用逗号分隔）</label>
                  <input
                    type="text"
                    placeholder="例如: ECS, RDS, OSS"
                    value={newTemplate.conditions.resourceTypes?.join(', ') || ''}
                    onChange={(e) => setNewTemplate({
                      ...newTemplate,
                      conditions: {
                        ...newTemplate.conditions,
                        resourceTypes: e.target.value.split(',').map(s => s.trim()).filter(Boolean),
                      },
                    })}
                  />
                </div>

                <div className="form-group">
                  <label>匹配条件 - 名称模式（支持 | 分隔多个模式）</label>
                  <input
                    type="text"
                    placeholder="例如: prod|production"
                    value={newTemplate.conditions.namePattern || ''}
                    onChange={(e) => setNewTemplate({
                      ...newTemplate,
                      conditions: {
                        ...newTemplate.conditions,
                        namePattern: e.target.value,
                      },
                    })}
                  />
                </div>
              </div>

              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  取消
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingTemplate ? '保存' : '创建'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default TagTemplates;
