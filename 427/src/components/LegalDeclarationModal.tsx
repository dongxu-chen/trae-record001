import React, { useState } from 'react';
import type { LegalDeclaration, ChainProof, BiometricVerificationResult } from '../types';
import { getLegalStatement, formatHashForDisplay } from '../utils/chainProof';

interface LegalDeclarationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (declaration: LegalDeclaration, requireBiometric: boolean) => void;
  signerName: string;
  biometricAvailable: boolean;
  verificationLevel: 'none' | 'single' | 'dual';
  verificationResult?: BiometricVerificationResult;
  chainProof?: ChainProof | null;
  signatureHash?: string;
  isSubmitting?: boolean;
}

const LegalDeclarationModal: React.FC<LegalDeclarationModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  signerName,
  biometricAvailable,
  verificationLevel,
  verificationResult,
  chainProof,
  signatureHash,
  isSubmitting = false,
}) => {
  const [agreed, setAgreed] = useState(false);
  const [requireBiometric, setRequireBiometric] = useState(biometricAvailable);
  const statement = getLegalStatement();

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '20px',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !isSubmitting) {
          onClose();
        }
      }}
    >
      <div
        style={{
          backgroundColor: '#fff',
          borderRadius: '12px',
          maxWidth: '500px',
          width: '100%',
          maxHeight: '90vh',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid #e0e0e0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <h2 style={{ margin: 0, fontSize: '18px', color: '#333' }}>
            法律声明与存证
          </h2>
          {!isSubmitting && (
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                fontSize: '24px',
                color: '#999',
                cursor: 'pointer',
                lineHeight: 1,
              }}
            >
              ×
            </button>
          )}
        </div>

        <div style={{ padding: '20px 24px', overflowY: 'auto', flex: 1 }}>
          <div
            style={{
              backgroundColor: '#f9f9f9',
              border: '1px solid #e0e0e0',
              borderRadius: '6px',
              padding: '16px',
              marginBottom: '16px',
              maxHeight: '200px',
              overflowY: 'auto',
              fontSize: '13px',
              lineHeight: 1.6,
              color: '#555',
              whiteSpace: 'pre-wrap',
            }}
          >
            {statement}
          </div>

          <div
            style={{
              marginBottom: '16px',
              padding: '12px',
              backgroundColor: '#fff8e1',
              borderRadius: '6px',
              borderLeft: '4px solid #ffc107',
            }}
          >
            <div style={{ fontSize: '14px', fontWeight: 500, color: '#333', marginBottom: '4px' }}>
              签名信息
            </div>
            <div style={{ fontSize: '13px', color: '#666' }}>
              签名者: <strong>{signerName}</strong>
            </div>
            {signatureHash && (
              <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                签名哈希: <code>{formatHashForDisplay(signatureHash)}</code>
              </div>
            )}
          </div>

          {biometricAvailable && (
            <div style={{ marginBottom: '16px' }}>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  color: '#333',
                }}
              >
                <input
                  type="checkbox"
                  checked={requireBiometric}
                  onChange={(e) => setRequireBiometric(e.target.checked)}
                  style={{ width: '16px', height: '16px' }}
                />
                <span>使用生物特征验证（{verificationLevel === 'dual' ? '指纹+人脸' : '指纹'}）</span>
              </label>
              {verificationResult && (
                <div
                  style={{
                    marginTop: '8px',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    backgroundColor: verificationResult.primaryVerified ? '#e8f5e9' : '#ffebee',
                    color: verificationResult.primaryVerified ? '#2e7d32' : '#c62828',
                    fontSize: '13px',
                  }}
                >
                  {verificationResult.primaryVerified
                    ? `✓ ${verificationResult.verificationLevel === 'dual' ? '双重' : '单因子'}生物验证通过`
                    : '✗ 生物验证失败'}
                </div>
              )}
            </div>
          )}

          {chainProof && (
            <div
              style={{
                padding: '12px',
                backgroundColor: '#e3f2fd',
                borderRadius: '6px',
                borderLeft: '4px solid #2196f3',
                marginBottom: '16px',
              }}
            >
              <div style={{ fontSize: '14px', fontWeight: 500, color: '#1565c0', marginBottom: '4px' }}>
                区块链存证成功
              </div>
              <div style={{ fontSize: '12px', color: '#1976d2' }}>
                区块高度: #{chainProof.blockHeight}
              </div>
              <div style={{ fontSize: '12px', color: '#1976d2', fontFamily: 'monospace' }}>
                交易哈希: {formatHashForDisplay(chainProof.hash)}
              </div>
            </div>
          )}

          <label
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px',
              cursor: 'pointer',
              fontSize: '14px',
              color: '#333',
            }}
          >
            <input
              type="checkbox"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
              style={{ width: '16px', height: '16px', marginTop: '2px' }}
              disabled={isSubmitting}
            />
            <span>
              我已阅读并同意以上法律声明，确认此签名为本人真实意愿表示
            </span>
          </label>
        </div>

        <div
          style={{
            padding: '16px 24px',
            borderTop: '1px solid #e0e0e0',
            display: 'flex',
            gap: '12px',
          }}
        >
          <button
            onClick={onClose}
            disabled={isSubmitting}
            style={{
              flex: 1,
              padding: '12px',
              fontSize: '14px',
              color: '#666',
              backgroundColor: '#f5f5f5',
              border: 'none',
              borderRadius: '6px',
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
            }}
          >
            取消
          </button>
          <button
            onClick={() => {
              if (agreed) {
                onConfirm(
                  {
                    agreed: true,
                    agreedAt: Date.now(),
                    statement,
                    userAgent: navigator.userAgent,
                  },
                  requireBiometric
                );
              }
            }}
            disabled={!agreed || isSubmitting}
            style={{
              flex: 1,
              padding: '12px',
              fontSize: '14px',
              color: '#fff',
              backgroundColor: agreed && !isSubmitting ? '#4a90d9' : '#ccc',
              border: 'none',
              borderRadius: '6px',
              cursor: agreed && !isSubmitting ? 'pointer' : 'not-allowed',
            }}
          >
            {isSubmitting ? '存证中...' : '确认签署'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default LegalDeclarationModal;
