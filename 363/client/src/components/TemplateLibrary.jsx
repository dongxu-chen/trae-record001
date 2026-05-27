import React, { useState, useEffect } from 'react';
import axios from 'axios';

const CATEGORIES = [
  { id: 'all', label: '全部', icon: '📁' },
  { id: 'frontend', label: '前端', icon: '🎨' },
  { id: 'backend', label: '后端', icon: '⚙️' },
  { id: 'fullstack', label: '全栈', icon: '🏗️' }
];

export default function TemplateLibrary({ onLoadTemplate }) {
  const [templates, setTemplates] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTemplates();
  }, [selectedCategory]);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const res = await axios.get('/api/templates', {
        params: { category: selectedCategory }
      });
      setTemplates(res.data);
    } catch (error) {
      console.error('加载模板失败:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="template-library">
      <div className="template-library-header">
        <div className="template-library-title">📚 模板库</div>
        <div className="template-category-tabs">
          {CATEGORIES.map(cat => (
            <button
              key={cat.id}
              className={`template-category-tab ${selectedCategory === cat.id ? 'active' : ''}
              onClick={() => setSelectedCategory(cat.id)}
            >
              {cat.icon} {cat.label}
            </button>
          ))}
        </div>
      </div>

      <div className="template-list">
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>
            加载中...
          </div>
        ) : (
          templates.map(template => (
            <div
              key={template.id}
              className="template-card"
              onClick={() => onLoadTemplate(template)}
            >
              <div className="template-card-icon">{template.icon}</div>
              <div className="template-card-content">
                <div className="template-card-title">{template.name}</div>
                <div className="template-card-desc">{template.description}</div>
                <div className="template-card-meta">
                  <span className="template-card-tag">{template.nodes?.length || 0} 个任务</span>
                  <span className="template-card-tag">{template.edges?.length || 0} 个依赖</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
