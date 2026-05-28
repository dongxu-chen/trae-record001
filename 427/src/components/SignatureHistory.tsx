import React from 'react';
import type { SignatureData } from '../types';

interface SignatureHistoryProps {
  signatures: SignatureData[];
  onSelect: (signature: SignatureData) => void;
  onDelete: (id: string) => void;
  selectedId?: string;
}

const SignatureHistory: React.FC<SignatureHistoryProps> = ({
  signatures,
  onSelect,
  onDelete,
  selectedId,
}) => {
  const formatDate = (timestamp: number): string => {
    return new Date(timestamp).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  if (signatures.length === 0) {
    return (
      <div className="signature-history-empty">
        <p style={{ color: '#999', textAlign: 'center', padding: '20px' }}>
          暂无签名历史
        </p>
      </div>
    );
  }

  return (
    <div className="signature-history">
      <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', color: '#333' }}>
        签名历史 ({signatures.length})
      </h3>
      <div
        className="signature-list"
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          maxHeight: '500px',
          overflowY: 'auto',
        }}
      >
        {signatures.map((signature) => (
          <div
            key={signature.id}
            className={`signature-item ${selectedId === signature.id ? 'selected' : ''}`}
            style={{
              border: selectedId === signature.id ? '2px solid #4a90d9' : '1px solid #e0e0e0',
              borderRadius: '8px',
              padding: '12px',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              backgroundColor: selectedId === signature.id ? '#f0f7ff' : '#fff',
            }}
            onClick={() => onSelect(signature)}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: '8px',
              }}
            >
              <div>
                <div
                  style={{
                    fontWeight: 600,
                    color: '#333',
                    fontSize: '14px',
                  }}
                >
                  {signature.signerName}
                </div>
                <div
                  style={{
                    fontSize: '12px',
                    color: '#666',
                    marginTop: '2px',
                  }}
                >
                  {formatDate(signature.createdAt)}
                </div>
                <div
                  style={{
                    fontSize: '12px',
                    color: '#999',
                    marginTop: '2px',
                  }}
                >
                  笔画数: {signature.strokes.length}
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(signature.id);
                }}
                style={{
                  padding: '4px 8px',
                  fontSize: '12px',
                  color: '#ff4757',
                  backgroundColor: 'transparent',
                  border: '1px solid #ff4757',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#ff4757';
                  e.currentTarget.style.color = '#fff';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = '#ff4757';
                }}
              >
                删除
              </button>
            </div>
            {signature.imageData && (
              <div
                style={{
                  width: '100%',
                  height: '80px',
                  backgroundColor: '#f9f9f9',
                  borderRadius: '4px',
                  overflow: 'hidden',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <img
                  src={signature.imageData}
                  alt="签名预览"
                  style={{
                    maxWidth: '100%',
                    maxHeight: '100%',
                    objectFit: 'contain',
                  }}
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default SignatureHistory;
