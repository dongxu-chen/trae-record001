import React, { useState } from 'react';
import type { SignatureStroke, SignatureVerificationResult, SignatureData } from '../types';
import { verifySignature } from '../utils/signatureUtils';
import SignaturePadComponent from './SignaturePad';
import type { SignaturePadHandle } from './SignaturePad';

interface SignatureVerificationProps {
  referenceSignatures: SignatureData[];
  onVerificationComplete?: (result: SignatureVerificationResult, referenceSignature: SignatureData) => void;
}

const SignatureVerification: React.FC<SignatureVerificationProps> = ({
  referenceSignatures,
  onVerificationComplete,
}) => {
  const [selectedReference, setSelectedReference] = useState<SignatureData | null>(null);
  const [verificationResult, setVerificationResult] = useState<SignatureVerificationResult | null>(null);
  const [currentStrokes, setCurrentStrokes] = useState<SignatureStroke[]>([]);
  const [isVerifying, setIsVerifying] = useState(false);
  const padRef = React.useRef<SignaturePadHandle | null>(null);

  const handleVerify = () => {
    if (!selectedReference || currentStrokes.length === 0) {
      return;
    }

    setIsVerifying(true);

    setTimeout(() => {
      const result = verifySignature(currentStrokes, selectedReference.strokes, 0.6);
      setVerificationResult(result);
      setIsVerifying(false);

      if (onVerificationComplete) {
        onVerificationComplete(result, selectedReference);
      }
    }, 500);
  };

  const handleClear = () => {
    if (padRef.current) {
      padRef.current.clear();
    }
    setCurrentStrokes([]);
    setVerificationResult(null);
  };

  const getResultColor = (similarity: number): string => {
    if (similarity >= 0.8) return '#4caf50';
    if (similarity >= 0.6) return '#ff9800';
    return '#f44336';
  };

  const getResultText = (similarity: number): string => {
    if (similarity >= 0.8) return '高度匹配';
    if (similarity >= 0.6) return '基本匹配';
    if (similarity >= 0.4) return '相似度较低';
    return '不匹配';
  };

  return (
    <div className="signature-verification">
      <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', color: '#333' }}>
        签名验证
      </h3>

      {referenceSignatures.length === 0 ? (
        <p style={{ color: '#999', textAlign: 'center', padding: '20px' }}>
          请先保存签名用于验证
        </p>
      ) : (
        <>
          <div style={{ marginBottom: '16px' }}>
            <label
              style={{
                display: 'block',
                marginBottom: '8px',
                fontSize: '14px',
                color: '#666',
              }}
            >
              选择参考签名:
            </label>
            <select
              value={selectedReference?.id || ''}
              onChange={(e) => {
                const sig = referenceSignatures.find((s) => s.id === e.target.value);
                setSelectedReference(sig || null);
                setVerificationResult(null);
              }}
              style={{
                width: '100%',
                padding: '10px 12px',
                fontSize: '14px',
                border: '1px solid #e0e0e0',
                borderRadius: '6px',
                outline: 'none',
                backgroundColor: '#fff',
              }}
            >
              <option value="">-- 请选择参考签名 --</option>
              {referenceSignatures.map((sig) => (
                <option key={sig.id} value={sig.id}>
                  {sig.signerName} - {new Date(sig.createdAt).toLocaleString('zh-CN')}
                </option>
              ))}
            </select>
          </div>

          {selectedReference && (
            <div
              style={{
                marginBottom: '16px',
                padding: '12px',
                backgroundColor: '#f9f9f9',
                borderRadius: '6px',
              }}
            >
              <div
                style={{
                  fontSize: '12px',
                  color: '#666',
                  marginBottom: '8px',
                }}
              >
                参考签名预览:
              </div>
              {selectedReference.imageData && (
                <img
                  src={selectedReference.imageData}
                  alt="参考签名"
                  style={{
                    width: '100%',
                    maxHeight: '100px',
                    objectFit: 'contain',
                    border: '1px solid #e0e0e0',
                    borderRadius: '4px',
                  }}
                />
              )}
            </div>
          )}

          <div style={{ marginBottom: '16px' }}>
            <div
              style={{
                fontSize: '14px',
                color: '#666',
                marginBottom: '8px',
              }}
            >
              请在下方重新签名进行验证:
            </div>
            <SignaturePadComponent
              onSignatureChange={setCurrentStrokes}
              height={200}
            />
          </div>

          <div
            style={{
              display: 'flex',
              gap: '8px',
              marginBottom: '16px',
            }}
          >
            <button
              onClick={handleVerify}
              disabled={!selectedReference || currentStrokes.length === 0 || isVerifying}
              style={{
                flex: 1,
                padding: '10px',
                fontSize: '14px',
                color: '#fff',
                backgroundColor:
                  selectedReference && currentStrokes.length > 0 && !isVerifying
                    ? '#4a90d9'
                    : '#ccc',
                border: 'none',
                borderRadius: '6px',
                cursor:
                  selectedReference && currentStrokes.length > 0 && !isVerifying
                    ? 'pointer'
                    : 'not-allowed',
              }}
            >
              {isVerifying ? '验证中...' : '开始验证'}
            </button>
            <button
              onClick={handleClear}
              style={{
                padding: '10px 16px',
                fontSize: '14px',
                color: '#666',
                backgroundColor: '#f5f5f5',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              清除
            </button>
          </div>

          {verificationResult && (
            <div
              className="verification-result"
              style={{
                padding: '16px',
                borderRadius: '8px',
                backgroundColor: verificationResult.isVerified ? '#f1f8e9' : '#ffebee',
                border: `1px solid ${
                  verificationResult.isVerified ? '#c5e1a5' : '#ef9a9a'
                }`,
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '12px',
                }}
              >
                <span
                  style={{
                    fontSize: '16px',
                    fontWeight: 600,
                    color: verificationResult.isVerified ? '#2e7d32' : '#c62828',
                  }}
                >
                  {verificationResult.isVerified ? '✓ 验证通过' : '✗ 验证失败'}
                </span>
                <span
                  style={{
                    fontSize: '14px',
                    fontWeight: 500,
                    color: getResultColor(verificationResult.similarity),
                  }}
                >
                  {getResultText(verificationResult.similarity)}
                </span>
              </div>

              <div
                style={{
                  marginBottom: '8px',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginBottom: '4px',
                    fontSize: '12px',
                    color: '#666',
                  }}
                >
                  <span>相似度</span>
                  <span
                    style={{
                      color: getResultColor(verificationResult.similarity),
                      fontWeight: 600,
                    }}
                  >
                    {(verificationResult.similarity * 100).toFixed(1)}%
                  </span>
                </div>
                <div
                  style={{
                    width: '100%',
                    height: '8px',
                    backgroundColor: '#e0e0e0',
                    borderRadius: '4px',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: `${verificationResult.similarity * 100}%`,
                      height: '100%',
                      backgroundColor: getResultColor(verificationResult.similarity),
                      transition: 'width 0.5s ease',
                    }}
                  />
                </div>
              </div>

              <div
                style={{
                  fontSize: '12px',
                  color: '#666',
                  borderTop: '1px solid #e0e0e0',
                  paddingTop: '8px',
                }}
              >
                <div>笔画数匹配: {verificationResult.details.strokeCountMatch ? '是' : '否'}</div>
                <div>
                  笔画平均相似度: {(verificationResult.details.averageSimilarity * 100).toFixed(1)}%
                </div>
                <div>
                  边框相似度: {(verificationResult.details.boundingBoxSimilarity * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default SignatureVerification;
