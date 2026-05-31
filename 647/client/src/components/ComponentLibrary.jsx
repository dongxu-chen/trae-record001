import React, { useState } from 'react';
import { useDraggable } from '@dnd-kit/core';
import { regexComponents, templateCategories } from '../data/regexComponents';

const DraggableComponent = ({ component, onAdd }) => {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `component-${component.id}`,
    data: {
      type: 'component',
      component
    }
  });

  const style = transform ? {
    transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 1000 : 1,
    position: isDragging ? 'relative' : 'static'
  } : undefined;

  const handleAddClick = (e) => {
    e.stopPropagation();
    e.preventDefault();
    if (onAdd) {
      onAdd(component);
    }
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className="component-item"
      title={component.description + ' (拖拽添加)'}
    >
      <div className="component-icon" style={{ background: component.color + '20', color: component.color }}>
        {component.icon}
      </div>
      <div className="component-info">
        <div className="component-name">{component.name}</div>
        <div className="component-desc">{component.description}</div>
      </div>
      <button
        onClick={handleAddClick}
        style={{
          width: '24px',
          height: '24px',
          borderRadius: '50%',
          border: 'none',
          background: component.color,
          color: 'white',
          fontSize: '16px',
          fontWeight: 'bold',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          lineHeight: '1',
          flexShrink: 0,
          transition: 'transform 0.15s ease'
        }}
        title="点击添加"
        onMouseEnter={(e) => { e.currentTarget.style.transform = 'scale(1.1)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.transform = 'scale(1)'; }}
      >
        +
      </button>
    </div>
  );
};

const ComponentLibrary = ({ onAddComponent }) => {
  const [activeTab, setActiveTab] = useState('basic');

  const allCategories = [
    ...regexComponents.map(c => ({ ...c, tab: 'basic' })),
    ...templateCategories.map(c => ({ ...c, tab: 'templates' }))
  ];

  const filteredCategories = allCategories.filter(c => c.tab === activeTab);

  return (
    <div className="component-library">
      <div className="library-tabs">
        <button
          className={`library-tab ${activeTab === 'basic' ? 'active' : ''}`}
          onClick={() => setActiveTab('basic')}
        >
          🔧 基础组件
        </button>
        <button
          className={`library-tab ${activeTab === 'templates' ? 'active' : ''}`}
          onClick={() => setActiveTab('templates')}
        >
          📋 常用模板
        </button>
      </div>
      <div className="library-content">
        {filteredCategories.map((category) => (
          <div key={category.category} className="component-category">
            <div className="category-title">{category.category}</div>
            {category.items.map((component) => (
              <DraggableComponent key={component.id} component={component} onAdd={onAddComponent} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ComponentLibrary;
