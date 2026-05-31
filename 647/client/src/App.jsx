import React, { useState, useCallback, useMemo } from 'react';
import { DndContext, DragOverlay, useSensor, useSensors, PointerSensor } from '@dnd-kit/core';
import { v4 as uuidv4 } from 'uuid';
import ComponentLibrary from './components/ComponentLibrary';
import RegexBuilder from './components/RegexBuilder';
import TestArea from './components/TestArea';
import RegexVisualizer from './components/RegexVisualizer';
import TestCaseManager from './components/TestCaseManager';
import RegexOptimizer from './components/RegexOptimizer';
import { 
  generatePattern, 
  checkMutexRules, 
  addToGroup, 
  removeFromBuilder,
  MUTEX_RULES
} from './utils/regexEngine';
import { getComponentById, regexComponents } from './data/regexComponents';

function App() {
  const [builderItems, setBuilderItems] = useState([]);
  const [testText, setTestText] = useState('请在此输入测试文本，例如：test@example.com 或者 13812345678');
  const [activeTab, setActiveTab] = useState('visualize');
  const [activeComponent, setActiveComponent] = useState(null);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [targetGroupId, setTargetGroupId] = useState(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const pattern = generatePattern(builderItems);

  const mutexWarnings = useMemo(() => {
    const warnings = [];
    const collectIds = (items) => {
      let ids = [];
      const collect = (itemList) => {
        for (const item of itemList) {
          ids.push(item.componentId);
          if (item.children) {
            collect(item.children);
          }
        }
        return ids;
      };
      collect(items);
      return ids;
    };
    
    const allIds = collectIds(builderItems);
    
    for (const rule of MUTEX_RULES) {
      const hasAll = rule.components.every(c => allIds.includes(c));
      if (hasAll) {
        warnings.push(`⚠️ ${rule.reason}`);
      }
    }
    
    return [...new Set(warnings)];
  }, [builderItems]);

  const handleDragStart = (event) => {
    const { active } = event;
    const data = active.data.current;
    if (data?.type === 'component') {
      setActiveComponent(data.component);
    }
  };

  const handleDragEnd = (event) => {
    const { active, over } = event;
    setActiveComponent(null);

    if (!over) return;

    const activeData = active.data.current;
    const overData = over.data.current;

    if (activeData?.type === 'component' && overData?.type === 'builder') {
      const component = activeData.component;
      handleAddComponentInternal(component, null);
    }
  };

  const handleAddComponentInternal = (component, groupId) => {
    const newItem = {
      id: uuidv4(),
      componentId: component.id,
      createdAt: Date.now()
    };

    if (component.hasInput) {
      if (component.id === 'exact') {
        newItem.inputValue = '3';
      } else if (component.id === 'range') {
        newItem.inputValue = '1,5';
      }
    }

    if (groupId) {
      setBuilderItems(prev => addToGroup(prev, groupId, newItem));
    } else {
      setBuilderItems(prev => [...prev, newItem]);
    }
  };

  const handleAddComponent = useCallback((component) => {
    handleAddComponentInternal(component, null);
  }, []);

  const handleRemoveItem = useCallback((itemId) => {
    setBuilderItems(prev => removeFromBuilder(prev, itemId));
  }, []);

  const handleUpdateItem = useCallback((itemId, updates) => {
    const updateRecursive = (items) => {
      return items.map(item => {
        if (item.id === itemId) {
          return { ...item, ...updates };
        }
        if (item.children) {
          return { ...item, children: updateRecursive(item.children) };
        }
        return item;
      });
    };
    setBuilderItems(prev => updateRecursive(prev));
  }, []);

  const handleClearBuilder = useCallback(() => {
    if (confirm('确定要清空所有组件吗？')) {
      setBuilderItems([]);
    }
  }, []);

  const handleLoadTestCase = useCallback((testCase) => {
    setTestText(testCase.testText);
  }, []);

  const handleAddToGroup = useCallback((groupId) => {
    setTargetGroupId(groupId);
    setShowGroupModal(true);
  }, []);

  const handleSelectComponentForGroup = (component) => {
    if (targetGroupId) {
      handleAddComponentInternal(component, targetGroupId);
    }
    setShowGroupModal(false);
    setTargetGroupId(null);
  };

  const handleApplyOptimization = useCallback((optimization, optimizedPattern) => {
    const newItem = {
      id: uuidv4(),
      componentId: 'custom-pattern',
      customPattern: optimizedPattern,
      createdAt: Date.now()
    };
    if (confirm('应用优化后将替换当前所有组件，是否继续？')) {
      setBuilderItems([newItem]);
    }
  }, []);

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="app-container">
        <div className="header">
          <h1>🔍 正则表达式可视化构建工具</h1>
          <p>拖拽组件构建正则表达式，实时预览匹配效果</p>
        </div>

        <div className="main-layout">
          <div className="panel">
            <div className="panel-header">组件库</div>
            <div className="panel-body">
              <ComponentLibrary onAddComponent={handleAddComponent} />
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">构建区域</div>
            <div className="panel-body">
              <RegexBuilder
                builderItems={builderItems}
                onRemoveItem={handleRemoveItem}
                onUpdateItem={handleUpdateItem}
                onClear={handleClearBuilder}
                onAddToGroup={handleAddToGroup}
                warnings={mutexWarnings}
              />
              <TestArea
                pattern={pattern}
                testText={testText}
                onTestTextChange={setTestText}
              />
            </div>
          </div>

          <div className="panel">
            <div className="nav-tabs" style={{ margin: '16px 16px 0' }}>
              <button
                className={`nav-tab ${activeTab === 'visualize' ? 'active' : ''}`}
                onClick={() => setActiveTab('visualize')}
              >
                📊 可视化
              </button>
              <button
                className={`nav-tab ${activeTab === 'optimizer' ? 'active' : ''}`}
                onClick={() => setActiveTab('optimizer')}
              >
                ⚡ 优化评估
              </button>
              <button
                className={`nav-tab ${activeTab === 'testcases' ? 'active' : ''}`}
                onClick={() => setActiveTab('testcases')}
              >
                📋 测试用例
              </button>
            </div>

            {activeTab === 'visualize' ? (
              <div className="panel-body">
                <div className="panel-header" style={{ margin: '-16px -16px 16px', borderRadius: 0 }}>
                  正则表达式可视化
                </div>
                <RegexVisualizer pattern={pattern} />
              </div>
            ) : activeTab === 'optimizer' ? (
              <div className="panel-body">
                <RegexOptimizer
                  pattern={pattern}
                  testText={testText}
                  onApplyOptimization={handleApplyOptimization}
                />
              </div>
            ) : (
              <TestCaseManager
                onLoadTestCase={handleLoadTestCase}
                currentPattern={pattern}
                currentTestText={testText}
              />
            )}
          </div>
        </div>
      </div>

      <DragOverlay>
        {activeComponent ? (
          <div
            className="component-item"
            style={{
              background: activeComponent.color + '20',
              borderColor: activeComponent.color,
              boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
              opacity: 0.9
            }}
          >
            <div className="component-icon" style={{ background: activeComponent.color + '20', color: activeComponent.color }}>
              {activeComponent.icon}
            </div>
            <div className="component-info">
              <div className="component-name">{activeComponent.name}</div>
              <div className="component-desc">{activeComponent.description}</div>
            </div>
          </div>
        ) : null}
      </DragOverlay>

      {showGroupModal && (
        <div className="modal-overlay" onClick={() => setShowGroupModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">选择要添加到组的组件</div>
            <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
              {regexComponents.map((category) => (
                <div key={category.category} className="component-category">
                  <div className="category-title">{category.category}</div>
                  {category.items.map((component) => (
                    <div
                    key={component.id}
                    className="component-item"
                    style={{ cursor: 'pointer' }}
                    onClick={() => handleSelectComponentForGroup(component)}
                  >
                    <div className="component-icon" style={{ background: component.color + '20', color: component.color }}>
                      {component.icon}
                    </div>
                    <div className="component-info">
                      <div className="component-name">{component.name}</div>
                      <div className="component-desc">{component.description}</div>
                    </div>
                  </div>
                ))}
                </div>
              ))}
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowGroupModal(false)}>取消</button>
            </div>
          </div>
        </div>
      )}
    </DndContext>
  );
}

export default App;
