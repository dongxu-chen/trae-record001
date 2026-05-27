import React, { useRef } from 'react';

export default function YamlModal({ isOpen, onClose, yamlContent, onExport, fileName }) {
  const textareaRef = useRef(null);

  if (!isOpen) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(yamlContent);
      alert('YAML已复制到剪贴板');
    } catch (err) {
      textareaRef.current?.select();
      document.execCommand('copy');
    }
  };

  const handleDownload = () => {
    const blob = new Blob([yamlContent], { type: 'application/x-yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName || 'pipeline.yaml';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="yaml-modal-overlay" onClick={onClose}>
      <div className="yaml-modal" onClick={(e) => e.stopPropagation()}>
        <div className="yaml-modal-header">
          <div className="yaml-modal-title">📄 流水线 YAML 预览</div>
          <button className="yaml-modal-close" onClick={onClose}>×</button>
        </div>
        
        <div className="yaml-modal-body">
          <pre className="yaml-code">{yamlContent}</pre>
        </div>
        
        <div className="yaml-modal-footer">
          <button className="btn btn-secondary" onClick={handleCopy}>
            📋 复制
          </button>
          <button className="btn btn-secondary" onClick={handleDownload}>
            💾 下载
          </button>
          {onExport && (
            <button className="btn btn-primary" onClick={onExport}>
              📤 导出
            </button>
          )}
          <button className="btn btn-primary" onClick={onClose}>
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}
