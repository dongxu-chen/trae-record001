import React, { useState } from 'react';
import { EXPORT_FORMATS, exportDocument } from '../utils/exportUtils';

export const ExportMenu = ({ editorValue, isVisible, onClose }) => {
  const [exporting, setExporting] = useState(null);

  const handleExport = async (format) => {
    if (!editorValue || !editorValue.length) {
      alert('文档为空，无法导出');
      return;
    }

    setExporting(format);
    try {
      await exportDocument(editorValue, format);
    } catch (error) {
      console.error('Export error:', error);
      alert('导出失败: ' + error.message);
    } finally {
      setExporting(null);
      onClose && onClose();
    }
  };

  if (!isVisible) return null;

  return (
    <div className="export-menu-overlay" onClick={onClose}>
      <div className="export-menu" onClick={(e) => e.stopPropagation()}>
        <div className="export-header">
          <h3>📤 导出文档</h3>
          <button onClick={onClose} className="close-btn">×</button>
        </div>
        
        <div className="export-formats">
          {EXPORT_FORMATS.map(format => (
            <div
              key={format.id}
              className="export-format-card"
              onClick={() => handleExport(format.id)}
            >
              <div className="format-icon">{format.icon}</div>
              <div className="format-info">
                <div className="format-name">{format.name}</div>
                <div className="format-ext">{format.extension}</div>
                <div className="format-desc">{format.description}</div>
              </div>
              <button
                className="export-btn"
                disabled={exporting === format.id}
              >
                {exporting === format.id ? '导出中...' : '导出'}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
