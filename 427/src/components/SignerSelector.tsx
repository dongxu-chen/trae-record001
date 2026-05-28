import React, { useState } from 'react';
import type { Signer } from '../types';
import { isWebAuthnSupported, registerWebAuthn, authenticateWebAuthn, registerDualFactor, performDualFactorAuthentication } from '../utils/webAuthn';

interface SignerSelectorProps {
  signers: Signer[];
  currentSignerId: string | null;
  onSelectSigner: (signer: Signer) => void;
  onAddSigner: (signer: Signer) => void;
  onUpdateSigner: (signer: Signer) => void;
  onDeleteSigner: (id: string) => void;
}

const SignerSelector: React.FC<SignerSelectorProps> = ({
  signers,
  currentSignerId,
  onSelectSigner,
  onAddSigner,
  onUpdateSigner,
  onDeleteSigner,
}) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [newSignerName, setNewSignerName] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const webAuthnSupported = isWebAuthnSupported();

  const handleAddSigner = async () => {
    if (!newSignerName.trim()) {
      setAuthError('请输入签名者姓名');
      return;
    }

    const existingSigner = signers.find(
      (s) => s.name.toLowerCase() === newSignerName.trim().toLowerCase()
    );
    if (existingSigner) {
      setAuthError('该签名者已存在');
      return;
    }

    const newSigner: Signer = {
      id: Math.random().toString(36).substring(2, 15),
      name: newSignerName.trim(),
      verificationLevel: 'none',
      signatures: [],
    };

    onAddSigner(newSigner);
    onSelectSigner(newSigner);
    setNewSignerName('');
    setShowAddForm(false);
    setAuthError(null);
  };

  const handleRegisterFingerprint = async (signer: Signer) => {
    if (!webAuthnSupported) {
      setAuthError('当前浏览器不支持WebAuthn');
      return;
    }

    setIsRegistering(true);
    setAuthError(null);

    try {
      const registration = await registerWebAuthn(signer.name, 'fingerprint');
      if (registration) {
        const updatedSigner: Signer = {
          ...signer,
          credentialId: registration.credentialId,
          publicKey: registration.publicKey,
          verificationLevel: signer.credentialIdSecondary ? 'dual' : 'single',
        };
        onUpdateSigner(updatedSigner);
        if (currentSignerId === signer.id) {
          onSelectSigner(updatedSigner);
        }
      } else {
        setAuthError('指纹注册失败');
      }
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : '注册失败');
    } finally {
      setIsRegistering(false);
    }
  };

  const handleRegisterFace = async (signer: Signer) => {
    if (!webAuthnSupported) {
      setAuthError('当前浏览器不支持WebAuthn');
      return;
    }

    if (!signer.credentialId) {
      setAuthError('请先注册指纹验证');
      return;
    }

    setIsRegistering(true);
    setAuthError(null);

    try {
      const registration = await registerWebAuthn(signer.name, 'face');
      if (registration) {
        const updatedSigner: Signer = {
          ...signer,
          credentialIdSecondary: registration.credentialId,
          publicKeySecondary: registration.publicKey,
          verificationLevel: 'dual',
        };
        onUpdateSigner(updatedSigner);
        if (currentSignerId === signer.id) {
          onSelectSigner(updatedSigner);
        }
      } else {
        setAuthError('人脸注册失败');
      }
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : '注册失败');
    } finally {
      setIsRegistering(false);
    }
  };

  const handleRegisterDualFactor = async (signer: Signer) => {
    if (!webAuthnSupported) {
      setAuthError('当前浏览器不支持WebAuthn');
      return;
    }

    setIsRegistering(true);
    setAuthError(null);

    try {
      const { primary, secondary } = await registerDualFactor(signer.name);
      if (primary) {
        const updatedSigner: Signer = {
          ...signer,
          credentialId: primary.credentialId,
          publicKey: primary.publicKey,
          credentialIdSecondary: secondary?.credentialId,
          publicKeySecondary: secondary?.publicKey,
          verificationLevel: secondary ? 'dual' : 'single',
        };
        onUpdateSigner(updatedSigner);
        if (currentSignerId === signer.id) {
          onSelectSigner(updatedSigner);
        }
      } else {
        setAuthError('双重验证注册失败');
      }
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : '注册失败');
    } finally {
      setIsRegistering(false);
    }
  };

  const handleAuthenticate = async (signer: Signer) => {
    if (!signer.credentialId) {
      setAuthError('该签名者尚未注册生物验证');
      return;
    }

    setIsAuthenticating(true);
    setAuthError(null);

    try {
      const result = await performDualFactorAuthentication(
        signer.credentialId,
        signer.credentialIdSecondary
      );
      if (result.primaryVerified) {
        onSelectSigner(signer);
      } else {
        setAuthError('身份验证失败');
      }
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : '验证失败');
    } finally {
      setIsAuthenticating(false);
    }
  };

  const getVerificationLevelText = (level: Signer['verificationLevel']): string => {
    switch (level) {
      case 'dual':
        return '✓✓ 双重验证';
      case 'single':
        return '✓ 单因子验证';
      default:
        return '未绑定验证';
    }
  };

  const getVerificationLevelColor = (level: Signer['verificationLevel']): string => {
    switch (level) {
      case 'dual':
        return '#2e7d32';
      case 'single':
        return '#f57c00';
      default:
        return '#999';
    }
  };

  return (
    <div className="signer-selector">
      <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', color: '#333' }}>
        签名者管理
      </h3>

      {authError && (
        <div
          style={{
            backgroundColor: '#ffebee',
            color: '#c62828',
            padding: '8px 12px',
            borderRadius: '4px',
            marginBottom: '12px',
            fontSize: '14px',
          }}
        >
          {authError}
        </div>
      )}

      <div
        className="signer-list"
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          marginBottom: '16px',
        }}
      >
        {signers.map((signer) => (
          <div
            key={signer.id}
            className={`signer-item ${currentSignerId === signer.id ? 'active' : ''}`}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px',
              border: currentSignerId === signer.id ? '2px solid #4a90d9' : '1px solid #e0e0e0',
              borderRadius: '8px',
              backgroundColor: currentSignerId === signer.id ? '#f0f7ff' : '#fff',
              transition: 'all 0.2s ease',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                flex: 1,
              }}
            >
              <div
                style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '50%',
                  backgroundColor: currentSignerId === signer.id ? '#4a90d9' : '#e0e0e0',
                  color: currentSignerId === signer.id ? '#fff' : '#666',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 600,
                  fontSize: '16px',
                }}
              >
                {signer.name.charAt(0).toUpperCase()}
              </div>
              <div>
                <div
                  style={{
                    fontWeight: 500,
                    color: '#333',
                    fontSize: '15px',
                  }}
                >
                  {signer.name}
                </div>
                <div
                  style={{
                    fontSize: '12px',
                    color: getVerificationLevelColor(signer.verificationLevel),
                    marginTop: '2px',
                  }}
                >
                  {getVerificationLevelText(signer.verificationLevel)}
                </div>
              </div>
            </div>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
                alignItems: 'flex-end',
              }}
            >
              <div style={{ display: 'flex', gap: '4px' }}>
                {webAuthnSupported && !signer.credentialId && (
                  <button
                    onClick={() => handleRegisterFingerprint(signer)}
                    disabled={isRegistering}
                    style={{
                      padding: '4px 8px',
                      fontSize: '11px',
                      color: '#fff',
                      backgroundColor: '#ff9800',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: isRegistering ? 'not-allowed' : 'pointer',
                    }}
                  >
                    绑定指纹
                  </button>
                )}
                {webAuthnSupported && signer.credentialId && !signer.credentialIdSecondary && (
                  <button
                    onClick={() => handleRegisterFace(signer)}
                    disabled={isRegistering}
                    style={{
                      padding: '4px 8px',
                      fontSize: '11px',
                      color: '#fff',
                      backgroundColor: '#9c27b0',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: isRegistering ? 'not-allowed' : 'pointer',
                    }}
                  >
                    绑定人脸
                  </button>
                )}
                {signer.credentialId && (
                  <button
                    onClick={() => handleAuthenticate(signer)}
                    disabled={isAuthenticating}
                    style={{
                      padding: '4px 8px',
                      fontSize: '11px',
                      color: '#fff',
                      backgroundColor: '#4caf50',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: isAuthenticating ? 'not-allowed' : 'pointer',
                    }}
                  >
                    {isAuthenticating ? '验证中...' : '验证'}
                  </button>
                )}
              </div>
              <div style={{ display: 'flex', gap: '4px' }}>
                <button
                  onClick={() => onSelectSigner(signer)}
                  style={{
                    padding: '4px 8px',
                    fontSize: '11px',
                    color: '#4a90d9',
                    backgroundColor: 'transparent',
                    border: '1px solid #4a90d9',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  选择
                </button>
                <button
                  onClick={() => onDeleteSigner(signer.id)}
                  style={{
                    padding: '4px 8px',
                    fontSize: '11px',
                    color: '#ff4757',
                    backgroundColor: 'transparent',
                    border: '1px solid #ff4757',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {!showAddForm ? (
        <button
          onClick={() => setShowAddForm(true)}
          style={{
            width: '100%',
            padding: '12px',
            fontSize: '14px',
            color: '#4a90d9',
            backgroundColor: 'transparent',
            border: '1px dashed #4a90d9',
            borderRadius: '8px',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = '#f0f7ff';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent';
          }}
        >
          + 添加签名者
        </button>
      ) : (
        <div
          className="add-signer-form"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          <input
            type="text"
            value={newSignerName}
            onChange={(e) => setNewSignerName(e.target.value)}
            placeholder="输入签名者姓名"
            style={{
              padding: '12px',
              fontSize: '14px',
              border: '1px solid #e0e0e0',
              borderRadius: '8px',
              outline: 'none',
            }}
            onFocus={(e) => {
              e.target.style.borderColor = '#4a90d9';
            }}
            onBlur={(e) => {
              e.target.style.borderColor = '#e0e0e0';
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleAddSigner();
              }
            }}
          />
          <div
            style={{
              display: 'flex',
              gap: '8px',
            }}
          >
            <button
              onClick={handleAddSigner}
              style={{
                flex: 1,
                padding: '12px',
                fontSize: '14px',
                color: '#fff',
                backgroundColor: '#4a90d9',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
              }}
            >
              添加
            </button>
            <button
              onClick={() => {
                setShowAddForm(false);
                setNewSignerName('');
                setAuthError(null);
              }}
              style={{
                flex: 1,
                padding: '12px',
                fontSize: '14px',
                color: '#666',
                backgroundColor: '#f5f5f5',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
              }}
            >
              取消
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default SignerSelector;
