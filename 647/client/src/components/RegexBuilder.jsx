import React, { useState } from 'react';
import { useDroppable } from '@dnd-kit/core';
import { getComponentById } from '../data/regexComponents';
import { generatePattern } from '../utils/regexEngine';

const BuilderItem = ({ item, onRemove, onUpdate, level = 0, onAddToGroup }) => {
  const component = getComponentById(item.componentId);
  const [showInput, setShowInput] = useState(false);
  const [inputValue, setInputValue] = useState(item.inputValue || '');

  if (!component) return null;

  const handleInputConfirm = () => {
    if (inputValue.trim()) {
      onUpdate(item.id, { inputValue: inputValue.trim() });
    }
    setShowInput(false);
  };

  const displayText = component.hasInput && item.inputValue
    ? component.id === 'exact'
      ? `{${item.inputValue}}`
      : component.id === 'range'
        ? `{${item.inputValue}}`
        : component.name
    : component.name;

  const hasChildren = item.children && item.children.length > 0;

  return (
    <div style={{ marginLeft: level * 16, marginBottom: '8px' }}>
      <div 
        className="builder-item" 
        style={{ 
          background: `linear-gradient(135deg, ${component.color} 0%, ${component.color}dd 100%)`,
          display: 'inline-flex',
          alignItems: 'center'
        }}
      >
        <span>{component.icon}</span>
        <span 
          onClick={() => component.hasInput && setShowInput(true)}
          style={{ cursor: component.hasInput ? 'pointer' : 'default' }}
          title={component.hasInput ? '点击修改参数' : component.description}
        >
          {displayText}
        </span>
        <span className="builder-item-remove" onClick={() => onRemove(item.id)}>×</span>
      </div>
      
      {component.isGroup && (
        <button
          onClick={() => onAddToGroup && onAddToGroup(item.id)}
          style={{
            marginLeft: '8px',
            padding: '2px 8px',
            background: '#f59e0b',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            fontSize: '11px',
            cursor: 'pointer'
          }}
          title="添加子组件到该组"
        >
          + 添加子组件
        </button>
      )}
      
      {hasChildren && (
        <div 
          style={{ 
            marginTop: '8px', 
            padding: '12px', 
            paddingLeft: level * 16 + 20,
            borderLeft: `3px solid ${component.color}`,
            background: `${component.color}10`,
            borderRadius: '0 8px 8px 8px'
          }}
        >
          <div style={{ fontSize: '11px', color: component.color, marginBottom: '8px', fontWeight: 500 }}>
            {component.name} 内容:
          </div>
          {item.children.map(child => (
            <BuilderItem
              key={child.id}
              item={child}
              onRemove={onRemove}
              onUpdate={onUpdate}
              level={level + 1}
              onAddToGroup={onAddToGroup}
            />
          ))}
        </div>
      )}
      
      {showInput && (
        <div className="modal-overlay" onClick={() => setShowInput(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">{component.inputLabel}</div>
            <div className="form-group">
              <input
                type="text"
                className="form-input"
                placeholder={component.inputPlaceholder}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                autoFocus
              />
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowInput(false)}>取消</button>
              <button className="btn btn-primary" onClick={handleInputConfirm}>确认</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const RegexBuilder = ({ builderItems, onRemoveItem, onUpdateItem, onClear, onAddToGroup, warnings }) => {
  const { setNodeRef, isOver } = useDroppable({
    id: 'builder-area',
    data: {
      type: 'builder'
    }
  });

  const pattern = generatePattern(builderItems);

  const copyPattern = () => {
    if (pattern) {
      navigator.clipboard.writeText(pattern);
    }
  };

  return (
    <div>
      {warnings && warnings.length > 0 && (
        <div style={{ 
          padding: '12px 16px', 
          background: '#fffbeb', 
          border: '1px solid #f59e0b', 
          borderRadius: '8px', 
          marginBottom: '16px',
          fontSize: '13px'
        }}>
          <div style={{ color: '#92400e', fontWeight: 600, marginBottom: '4px' }}>
            ⚠️ 优化建议
          </div>
          {warnings.map((warning, idx) => (
            <div key={idx} style={{ color: '#b45309', marginLeft: '8px' }}>
              • {warning}
            </div>
          ))}
        </div>
      )}
      
      <div
        ref={setNodeRef}
        className={`builder-area ${isOver ? 'drag-over' : ''} ${builderItems.length === 0 ? 'empty' : ''}`}
        style={{ minHeight: '150px' }}
      >
        {builderItems.length === 0 ? (
          <span>拖拽左侧组件到此处构建正则表达式，或点击组件的 + 按钮添加</span>
        ) : (
          <div style={{ padding: '8px 0' }}>
            {builderItems.map((item, index) => (
              <React.Fragment key={item.id}>
                <BuilderItem
                  item={item}
                  onRemove={onRemoveItem}
                  onUpdate={onUpdateItem}
                  level={0}
                  onAddToGroup={onAddToGroup}
                />
                {index < builderItems.length - 1 && (
                  <div style={{ textAlign: 'center', color: '#999', fontSize: '12px', margin: '4px 0' }}>
                    ─── 连接 ───
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>
        )}
      </div>

      <div className="pattern-display" style={{ marginTop: '16px' }}>
        <div className="pattern-label" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>生成的正则表达式</span>
          <div style={{ display: 'flex', gap: '8px' }}>
            {builderItems.length > 0 && (
              <button className="btn btn-sm btn-secondary" onClick={onClear}>清空</button>
            )}
            {pattern && (
              <button className="btn btn-sm btn-primary" onClick={copyPattern}>复制</button>
            )}
          </div>
        </div>
        <div className="pattern-code">
          {pattern || '请拖拽组件开始构建'}
        </div>
      </div>
    </div>
  );
};

export default RegexBuilder;
