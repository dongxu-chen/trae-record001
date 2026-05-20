import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import collaborationClient from '../utils/collaborationClient';

export const VersionHistory = ({ oplog, onRevert }) => {
  const [loadingSnapshot, setLoadingSnapshot] = useState(null);
  const [previewContent, setPreviewContent] = useState(null);
  const [previewVersion, setPreviewVersion] = useState(null);
  const sortedOplog = [...oplog].sort((a, b) => b.v - a.v);

  useEffect(() => {
    const handleSnapshot = (data) => {
      if (data.snapshot && data.snapshot.v === loadingSnapshot) {
        setPreviewContent(deltaToPlainText(data.snapshot.content, data.snapshot.v));
        setPreviewVersion(data.snapshot.v);
        setLoadingSnapshot(null);
      }
    };
    
    collaborationClient.on('snapshot', handleSnapshot);
    return () => collaborationClient.off('snapshot', handleSnapshot);
  }, [loadingSnapshot]);

  const handlePreview = (version) => {
    if (previewVersion === version) {
      setPreviewContent(null);
      setPreviewVersion(null);
      return;
    }
    
    setLoadingSnapshot(version);
    setPreviewContent(null);
    setPreviewVersion(null);
    collaborationClient.getSnapshot(version);
    
    setTimeout(() => {
      setLoadingSnapshot(null);
    }, 5000);
  };

  return (
    <div className="version-history">
      <div className="version-header">
        <h3>📜 Oplog 版本历史</h3>
        <span className="version-count">{oplog.length} 条记录</span>
      </div>

      <div className="versions-list">
        {sortedOplog.length === 0 ? (
          <div className="empty-versions">
            暂无操作记录，开始编辑后将自动保存
          </div>
        ) : (
          sortedOplog.map((entry, index) => (
            <div key={entry.v} className="version-item">
              <div className="version-info">
                <span className="version-number">版本 #{entry.v}</span>
                <span className="version-time">
                  {format(entry.timestamp, 'MM-dd HH:mm:ss')}
                </span>
                <span className="version-author">
                  用户: {entry.clientId.slice(0, 6)}
                </span>
                {entry.type === 'revert' && (
                  <span className="revert-badge">↺ 回退</span>
                )}
              </div>
              <div className="version-ops">
                {entry.op && describeOp(entry.op)}
              </div>
              <div className="version-actions">
                <button
                  onClick={() => handlePreview(entry.v)}
                  className="preview-btn"
                  disabled={loadingSnapshot === entry.v}
                >
                  {loadingSnapshot === entry.v ? '加载中...' : '预览'}
                </button>
                {index > 0 && (
                  <button
                    onClick={() => onRevert && onRevert(entry.v)}
                    className="revert-btn"
                  >
                    恢复到此版本
                  </button>
                )}
                {index === 0 && (
                  <span className="current-badge">当前版本</span>
                )}
              </div>
              {previewContent !== null && previewVersion === entry.v && (
                <div className="version-preview">
                  <div className="preview-header">版本 #{entry.v} 内容预览:</div>
                  <div className="preview-content">{previewContent}</div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

function describeOp(op) {
  if (!op || !Array.isArray(op)) return '';
  
  let inserts = 0;
  let deletes = 0;
  let retains = 0;
  let hasFormat = false;
  
  for (const component of op) {
    if (typeof component === 'object') {
      if (component.insert) {
        inserts += component.insert.length;
      }
      if (component.delete) {
        deletes += component.delete;
      }
      if (component.retain && component.attributes) {
        hasFormat = true;
      }
      if (component.wrapList || component.unwrapList) {
        hasFormat = true;
      }
    } else if (typeof component === 'number') {
      retains += component;
    }
  }
  
  const parts = [];
  if (inserts > 0) parts.push(`插入 ${inserts} 字符`);
  if (deletes > 0) parts.push(`删除 ${deletes} 字符`);
  if (hasFormat) parts.push('格式变更');
  
  return parts.join(', ') || '无变更';
}

function deltaToPlainText(delta, version) {
  if (!delta || !Array.isArray(delta)) {
    return '';
  }
  
  let text = '';
  for (const item of delta) {
    if (typeof item === 'object' && item.insert) {
      text += item.insert;
    }
  }
  
  return text.slice(0, 500) + (text.length > 500 ? '...' : '');
}
