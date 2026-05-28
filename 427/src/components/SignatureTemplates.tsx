import React, { useState } from 'react';
import type { SignatureTemplate, SignatureStroke } from '../types';

interface SignatureTemplatesProps {
  templates: SignatureTemplate[];
  currentSignerId: string | null;
  onSelectTemplate: (strokes: SignatureStroke[]) => void;
  onSaveTemplate: (name: string, strokes: SignatureStroke[], imageData: string) => void;
  onDeleteTemplate: (id: string) => void;
  onUpdateTemplate: (template: SignatureTemplate) => void;
  hasCurrentSignature: boolean;
}

const SignatureTemplates: React.FC<SignatureTemplatesProps> = ({
  templates,
  currentSignerId,
  onSelectTemplate,
  onSaveTemplate,
  onDeleteTemplate,
  onUpdateTemplate,
  hasCurrentSignature,
}) => {
  const [showSaveForm, setShowSaveForm] = useState(false);
  const [newTemplateName, setNewTemplateName] = useState('');
  const [strokesToSave, setStrokesToSave] = useState<SignatureStroke[]>([]);
  const [imageDataToSave, setImageDataToSave] = useState('');

  const userTemplates = templates.filter((t) => t.signerId === currentSignerId);

  const handleOpenSaveForm = (strokes: SignatureStroke[], imageData: string) => {
    setStrokesToSave(strokes);
    setImageDataToSave(imageData);
    setShowSaveForm(true);
  };

  const handleSaveTemplate = () => {
    if (!newTemplateName.trim()) return;
    onSaveTemplate(newTemplateName.trim(), strokesToSave, imageDataToSave);
    setNewTemplateName('');
    setShowSaveForm(false);
    setStrokesToSave([]);
    setImageDataToSave('');
  };

  const formatDate = (timestamp: number): string => {
    return new Date(timestamp).toLocaleDateString('zh-CN');
  };

  return (
    <div className="signature-templates">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px',
        }}
      >
        <h3 style={{ margin: 0, fontSize: '16px', color: '#333' }}>
          签名模板库
        </h3>
        {hasCurrentSignature && (
          <button
            onClick={() => {
              const canvas = document.querySelector('canvas');
              const imageData = canvas?.toDataURL('image/png') || '';
              const event = new CustomEvent('requestSignature', {
                detail: { callback: handleOpenSaveForm, imageData },
              });
              window.dispatchEvent(event);
            }}
            style={{
              padding: '6px 12px',
              fontSize: '12px',
              color: '#fff',
              backgroundColor: '#4a90d9',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            + 保存为模板
          </button>
        )}
      </div>

      {showSaveForm && (
        <div
          style={{
            padding: '12px',
            backgroundColor: '#f5f5f5',
            borderRadius: '6px',
            marginBottom: '16px',
          }}
        >
          <input
            type="text"
            value={newTemplateName}
            onChange={(e) => setNewTemplateName(e.target.value)}
            placeholder="输入模板名称"
            style={{
              width: '100%',
              padding: '8px 12px',
              fontSize: '14px',
              border: '1px solid #e0e0e0',
              borderRadius: '4px',
              marginBottom: '8px',
              boxSizing: 'border-box',
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSaveTemplate();
            }}
          />
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={handleSaveTemplate}
              disabled={!newTemplateName.trim()}
              style={{
                flex: 1,
                padding: '8px',
                fontSize: '14px',
                color: '#fff',
                backgroundColor: newTemplateName.trim() ? '#4a90d9' : '#ccc',
                border: 'none',
                borderRadius: '4px',
                cursor: newTemplateName.trim() ? 'pointer' : 'not-allowed',
              }}
            >
              保存
            </button>
            <button
              onClick={() => {
                setShowSaveForm(false);
                setNewTemplateName('');
              }}
              style={{
                flex: 1,
                padding: '8px',
                fontSize: '14px',
                color: '#666',
                backgroundColor: '#e0e0e0',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              取消
            </button>
          </div>
        </div>
      )}

      {userTemplates.length === 0 ? (
        <p style={{ color: '#999', textAlign: 'center', padding: '20px' }}>
          暂无签名模板，先签名后保存为模板
        </p>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
            gap: '12px',
          }}
        >
          {userTemplates.map((template) => (
            <div
              key={template.id}
              className="template-card"
              style={{
                border: '1px solid #e0e0e0',
                borderRadius: '8px',
                padding: '12px',
                backgroundColor: '#fff',
                transition: 'all 0.2s ease',
                cursor: 'pointer',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
                e.currentTarget.style.borderColor = '#4a90d9';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = 'none';
                e.currentTarget.style.borderColor = '#e0e0e0';
              }}
              onClick={() => onSelectTemplate(template.strokes)}
            >
              <div
                style={{
                  height: '80px',
                  backgroundColor: '#f9f9f9',
                  borderRadius: '4px',
                  marginBottom: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  overflow: 'hidden',
                }}
              >
                <img
                  src={template.imageData}
                  alt={template.name}
                  style={{
                    maxWidth: '100%',
                    maxHeight: '100%',
                    objectFit: 'contain',
                  }}
                />
              </div>
              <div
                style={{
                  fontSize: '14px',
                  fontWeight: 500,
                  color: '#333',
                  marginBottom: '4px',
                }}
              >
                {template.name}
              </div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: '12px',
                  color: '#999',
                }}
              >
                <span>使用 {template.usageCount} 次</span>
                <span>{formatDate(template.createdAt)}</span>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteTemplate(template.id);
                }}
                style={{
                  position: 'absolute',
                  top: '8px',
                  right: '8px',
                  padding: '2px 6px',
                  fontSize: '11px',
                  color: '#ff4757',
                  backgroundColor: 'rgba(255,71,87,0.1)',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  opacity: 0,
                  transition: 'opacity 0.2s',
                }}
                onMouseEnter={(e) => {
                  (e.target as HTMLButtonElement).style.opacity = '1';
                }}
              >
                删除
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SignatureTemplates;
