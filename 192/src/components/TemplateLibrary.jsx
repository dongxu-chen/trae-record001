import React, { useState } from 'react';
import { DOCUMENT_TEMPLATES, TEMPLATE_CATEGORIES } from '../utils/templates';

export const TemplateLibrary = ({ isVisible, onClose, onApplyTemplate }) => {
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredTemplates = DOCUMENT_TEMPLATES.filter(template => {
    const matchesCategory = selectedCategory === 'all' || template.category === selectedCategory;
    const matchesSearch = template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          template.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const handleApplyTemplate = (template) => {
    onApplyTemplate && onApplyTemplate(template);
    onClose && onClose();
  };

  if (!isVisible) return null;

  return (
    <div className="template-library-overlay" onClick={onClose}>
      <div className="template-library" onClick={(e) => e.stopPropagation()}>
        <div className="template-header">
          <h2>📚 文档模板库</h2>
          <button onClick={onClose} className="close-btn">×</button>
        </div>

        <div className="template-search">
          <input
            type="text"
            placeholder="搜索模板..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="template-categories">
          {TEMPLATE_CATEGORIES.map(category => (
            <button
              key={category.id}
              className={`category-btn ${selectedCategory === category.id ? 'active' : ''}`}
              onClick={() => setSelectedCategory(category.id)}
            >
              {category.icon} {category.name}
            </button>
          ))}
        </div>

        <div className="template-grid">
          {filteredTemplates.map(template => (
            <div
              key={template.id}
              className="template-card"
              onClick={() => handleApplyTemplate(template)}
            >
              <div className="template-icon">{template.icon}</div>
              <div className="template-name">{template.name}</div>
              <div className="template-category">{template.category}</div>
              <div className="template-desc">{template.description}</div>
              <button className="apply-template-btn">
                应用模板
              </button>
            </div>
          ))}
        </div>

        {filteredTemplates.length === 0 && (
          <div className="no-templates">
            没有找到匹配的模板
          </div>
        )}
      </div>
    </div>
  );
};
