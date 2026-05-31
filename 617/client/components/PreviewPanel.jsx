import React, { useState, useEffect, useRef, useCallback } from 'react';

function PreviewPanel({
  skeletonData,
  device,
  loading,
  debugMode,
  selectedElement,
  onSelectElement,
  onUpdateElement,
  onDeleteElement
}) {
  const [activeTab, setActiveTab] = useState('html');
  const iframeRef = useRef(null);
  const [editValues, setEditValues] = useState({
    width: 0,
    height: 0,
    top: 0,
    left: 0
  });

  useEffect(() => {
    if (skeletonData && iframeRef.current) {
      const doc = iframeRef.current.contentDocument;
      doc.open();
      doc.write(`
        <!DOCTYPE html>
        <html>
        <head>
          <style>${skeletonData.css}</style>
          <style>
            ${debugMode ? `
              .skeleton-item {
                cursor: pointer;
                transition: outline 0.15s ease;
              }
              .skeleton-item:hover {
                outline: 2px solid #667eea !important;
                outline-offset: 1px;
              }
              .skeleton-item.selected {
                outline: 3px solid #ff6b6b !important;
                outline-offset: 2px;
              }
            ` : ''}
          </style>
        </head>
        <body style="margin:0;padding:0;">
          ${skeletonData.html}
        </body>
        </html>
      `);
      doc.close();
      
      if (debugMode) {
        const items = doc.querySelectorAll('.skeleton-item');
        items.forEach(item => {
          item.addEventListener('click', (e) => {
            e.stopPropagation();
            const elementId = item.getAttribute('data-element-id');
            const elementType = item.getAttribute('data-element-type');
            
            items.forEach(i => i.classList.remove('selected'));
            item.classList.add('selected');
            
            const rect = item.getBoundingClientRect();
            onSelectElement({
              id: elementId,
              type: elementType,
              width: rect.width,
              height: rect.height,
              top: rect.top,
              left: rect.left
            });
            
            setEditValues({
              width: Math.round(parseFloat(item.style.width)),
              height: Math.round(parseFloat(item.style.height)),
              top: Math.round(parseFloat(item.style.top)),
              left: Math.round(parseFloat(item.style.left))
            });
          });
        });
      }
    }
  }, [skeletonData, debugMode, onSelectElement]);

  const handleEditChange = useCallback((field, value) => {
    setEditValues(prev => ({
      ...prev,
      [field]: parseInt(value) || 0
    }));
  }, []);

  const applyChanges = useCallback(() => {
    if (selectedElement && onUpdateElement) {
      onUpdateElement(selectedElement.id, {
        rect: {
          width: editValues.width,
          height: editValues.height,
          top: editValues.top,
          left: editValues.left
        }
      });
    }
  }, [selectedElement, editValues, onUpdateElement]);

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      alert('已复制到剪贴板！');
    });
  };

  const downloadCode = (filename, content) => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!skeletonData) {
    return (
      <div className="preview-panel">
        <div className="preview-header">
          <h2>预览</h2>
        </div>
        <div className="preview-content">
          <div className="empty-state">
            <div className="empty-state-icon">🖼️</div>
            <p>请输入网页URL并点击"生成"按钮<br />来生成骨架屏代码</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="preview-panel">
      <div className="preview-header">
        <h2>骨架屏预览</h2>
        <div className="preview-actions">
          <button
            className="action-btn"
            onClick={() => copyToClipboard(skeletonData.html + '\n\n<style>\n' + skeletonData.css + '\n</style>')}
          >
            📋 复制全部
          </button>
          <button
            className="action-btn primary"
            onClick={() => {
              downloadCode('skeleton.html', skeletonData.html);
              downloadCode('skeleton.css', skeletonData.css);
            }}
          >
            ⬇️ 下载代码
          </button>
        </div>
      </div>
      
      <div className="preview-content">
        {debugMode && selectedElement && (
          <div className="debug-panel">
            <div className="debug-panel-header">
              <span>✏️ 编辑元素</span>
              <button
                className="delete-element-btn"
                onClick={() => onDeleteElement(selectedElement.id)}
              >
                🗑️ 删除
              </button>
            </div>
            <div className="debug-panel-body">
              <div className="debug-field">
                <label>类型: {selectedElement.type}</label>
              </div>
              <div className="debug-row">
                <div className="debug-field">
                  <label>宽度 (px)</label>
                  <input
                    type="number"
                    value={editValues.width}
                    onChange={(e) => handleEditChange('width', e.target.value)}
                  />
                </div>
                <div className="debug-field">
                  <label>高度 (px)</label>
                  <input
                    type="number"
                    value={editValues.height}
                    onChange={(e) => handleEditChange('height', e.target.value)}
                  />
                </div>
              </div>
              <div className="debug-row">
                <div className="debug-field">
                  <label>上边距 (px)</label>
                  <input
                    type="number"
                    value={editValues.top}
                    onChange={(e) => handleEditChange('top', e.target.value)}
                  />
                </div>
                <div className="debug-field">
                  <label>左边距 (px)</label>
                  <input
                    type="number"
                    value={editValues.left}
                    onChange={(e) => handleEditChange('left', e.target.value)}
                  />
                </div>
              </div>
              <button
                className="apply-edit-btn"
                onClick={applyChanges}
              >
                ✓ 应用修改
              </button>
            </div>
          </div>
        )}
        
        <div className={`preview-frame ${device}`}>
          <iframe
            ref={iframeRef}
            style={{
              width: device === 'mobile' ? '375px' : '100%',
              minHeight: '500px',
              border: 'none',
              background: '#fff'
            }}
            title="skeleton-preview"
          />
        </div>
      </div>
      
      <div className="code-panel">
        <div className="code-tabs">
          <button
            className={`code-tab ${activeTab === 'html' ? 'active' : ''}`}
            onClick={() => setActiveTab('html')}
          >
            HTML
          </button>
          <button
            className={`code-tab ${activeTab === 'css' ? 'active' : ''}`}
            onClick={() => setActiveTab('css')}
          >
            CSS
          </button>
        </div>
        <div className="code-content">
          <pre>{activeTab === 'html' ? skeletonData.html : skeletonData.css}</pre>
        </div>
      </div>
    </div>
  );
}

export default PreviewPanel;
