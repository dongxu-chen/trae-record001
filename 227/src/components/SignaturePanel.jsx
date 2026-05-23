import { useState, useEffect } from 'react';
import {
  generateKeyPair,
  signPDFDocument,
  verifyPDFSignature,
  saveKeyPair,
  loadKeyPair,
  generateHash
} from '../utils/digitalSignature';

export function SignaturePanel({ pdfDoc, pdfData, onClose }) {
  const [keyPair, setKeyPair] = useState(null);
  const [signerName, setSignerName] = useState('');
  const [signReason, setSignReason] = useState('');
  const [signature, setSignature] = useState(null);
  const [verificationResult, setVerificationResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('sign');

  useEffect(() => {
    const saved = loadKeyPair();
    if (saved) {
      setKeyPair(saved);
    }
  }, []);

  const handleGenerateKeys = async () => {
    setLoading(true);
    try {
      const newKeyPair = await generateKeyPair();
      setKeyPair(newKeyPair);
      saveKeyPair(newKeyPair);
      alert('密钥对已生成并保存到本地！');
    } catch (error) {
      alert('生成密钥失败: ' + error.message);
    }
    setLoading(false);
  };

  const handleSign = async () => {
    if (!keyPair) {
      alert('请先生成或加载密钥对');
      return;
    }
    if (!signerName.trim()) {
      alert('请输入签名者姓名');
      return;
    }

    setLoading(true);
    try {
      const dataToSign = pdfData || JSON.stringify({ 
        docId: pdfDoc?.fingerprint || 'unknown',
        timestamp: Date.now()
      });
      
      const sig = await signPDFDocument(dataToSign, signerName, signReason, keyPair);
      setSignature(sig);
      setVerificationResult(null);
    } catch (error) {
      alert('签名失败: ' + error.message);
    }
    setLoading(false);
  };

  const handleVerify = async () => {
    if (!signature) {
      alert('请先签名或导入签名数据');
      return;
    }

    setLoading(true);
    try {
      const dataToVerify = pdfData || JSON.stringify({ 
        docId: pdfDoc?.fingerprint || 'unknown',
        timestamp: Date.now()
      });
      
      const result = await verifyPDFSignature(dataToVerify, signature);
      setVerificationResult(result);
    } catch (error) {
      alert('验证失败: ' + error.message);
    }
    setLoading(false);
  };

  const handleExportSignature = () => {
    if (!signature) return;
    
    const blob = new Blob([JSON.stringify(signature, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `signature_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImportSignature = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const sig = JSON.parse(event.target.result);
        setSignature(sig);
        setVerificationResult(null);
      } catch (error) {
        alert('签名文件格式错误');
      }
    };
    reader.readAsText(file);
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        background: 'white',
        borderRadius: '8px',
        width: '90%',
        maxWidth: '600px',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column'
      }}>
        <div style={{
          padding: '16px 24px',
          borderBottom: '1px solid #e0e0e0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <h3 style={{ margin: 0 }}>🔐 数字签名</h3>
          <button 
            onClick={onClose}
            style={{
              border: 'none',
              background: 'none',
              fontSize: '20px',
              cursor: 'pointer',
              color: '#666'
            }}
          >
            ✕
          </button>
        </div>

        <div style={{
          display: 'flex',
          borderBottom: '1px solid #e0e0e0'
        }}>
          <button
            onClick={() => setActiveTab('sign')}
            style={{
              flex: 1,
              padding: '12px',
              border: 'none',
              background: activeTab === 'sign' ? '#f0f8ff' : 'white',
              borderBottom: `2px solid ${activeTab === 'sign' ? '#3498db' : 'transparent'}`,
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: activeTab === 'sign' ? 600 : 400
            }}
          >
            ✍️ 签名文档
          </button>
          <button
            onClick={() => setActiveTab('verify')}
            style={{
              flex: 1,
              padding: '12px',
              border: 'none',
              background: activeTab === 'verify' ? '#f0f8ff' : 'white',
              borderBottom: `2px solid ${activeTab === 'verify' ? '#3498db' : 'transparent'}`,
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: activeTab === 'verify' ? 600 : 400
            }}
          >
            ✅ 验证签名
          </button>
        </div>

        <div style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>
          {activeTab === 'sign' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{
                padding: '16px',
                background: keyPair ? '#e8f5e9' : '#fff3e0',
                borderRadius: '6px',
                border: `1px solid ${keyPair ? '#81c784' : '#ffb74d'}`
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <strong>密钥状态:</strong> {keyPair ? '✅ 已加载' : '⚠️ 未生成'}
                  </div>
                  <button
                    onClick={handleGenerateKeys}
                    disabled={loading}
                    style={{
                      padding: '6px 16px',
                      border: 'none',
                      background: '#3498db',
                      color: 'white',
                      borderRadius: '4px',
                      cursor: loading ? 'not-allowed' : 'pointer',
                      opacity: loading ? 0.6 : 1
                    }}
                  >
                    {keyPair ? '重新生成' : '生成密钥对'}
                  </button>
                </div>
                {keyPair && (
                  <p style={{ fontSize: '12px', color: '#666', margin: '8px 0 0 0' }}>
                    使用RSA 2048位密钥 + SHA-256哈希算法
                  </p>
                )}
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
                  签名者姓名 <span style={{ color: 'red' }}>*</span>
                </label>
                <input
                  type="text"
                  value={signerName}
                  onChange={(e) => setSignerName(e.target.value)}
                  placeholder="请输入您的姓名"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
                  签名原因
                </label>
                <select
                  value={signReason}
                  onChange={(e) => setSignReason(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                >
                  <option value="">请选择原因...</option>
                  <option value="同意文档内容">同意文档内容</option>
                  <option value="审核通过">审核通过</option>
                  <option value="已阅读并理解">已阅读并理解</option>
                  <option value="作为见证人">作为见证人</option>
                </select>
              </div>

              <button
                onClick={handleSign}
                disabled={loading || !keyPair || !signerName.trim()}
                style={{
                  padding: '12px',
                  border: 'none',
                  background: '#27ae60',
                  color: 'white',
                  borderRadius: '4px',
                  fontSize: '16px',
                  cursor: (loading || !keyPair || !signerName.trim()) ? 'not-allowed' : 'pointer',
                  opacity: (loading || !keyPair || !signerName.trim()) ? 0.6 : 1
                }}
              >
                {loading ? '签名中...' : '🔏 对文档进行数字签名'}
              </button>

              {signature && (
                <div style={{
                  padding: '16px',
                  background: '#e8f5e9',
                  borderRadius: '6px',
                  border: '1px solid #81c784'
                }}>
                  <p style={{ margin: '0 0 12px 0', fontWeight: 600, color: '#2e7d32' }}>
                    ✅ 签名成功！
                  </p>
                  <div style={{ fontSize: '13px', color: '#666', marginBottom: '12px' }}>
                    <p><strong>签名者:</strong> {signature.metadata.signerName}</p>
                    <p><strong>原因:</strong> {signature.metadata.reason || '无'}</p>
                    <p><strong>时间:</strong> {new Date(signature.metadata.timestamp).toLocaleString()}</p>
                    <p><strong>文档哈希:</strong> {signature.hash.slice(0, 20)}...</p>
                  </div>
                  <button
                    onClick={handleExportSignature}
                    style={{
                      padding: '8px 16px',
                      border: '1px solid #27ae60',
                      background: 'white',
                      color: '#27ae60',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    📥 导出签名文件
                  </button>
                </div>
              )}
            </div>
          )}

          {activeTab === 'verify' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{
                padding: '16px',
                background: '#f5f5f5',
                borderRadius: '6px',
                border: '1px dashed #ddd'
              }}>
                <p style={{ margin: '0 0 8px 0', fontSize: '14px' }}>
                  导入签名文件 (.json) 进行验证:
                </p>
                <input
                  type="file"
                  accept=".json"
                  onChange={handleImportSignature}
                  style={{ width: '100%' }}
                />
              </div>

              {signature && !verificationResult && (
                <button
                  onClick={handleVerify}
                  disabled={loading}
                  style={{
                    padding: '12px',
                    border: 'none',
                    background: '#3498db',
                    color: 'white',
                    borderRadius: '4px',
                    fontSize: '16px',
                    cursor: loading ? 'not-allowed' : 'pointer',
                    opacity: loading ? 0.6 : 1
                  }}
                >
                  {loading ? '验证中...' : '🔍 验证签名有效性'}
                </button>
              )}

              {signature && (
                <div style={{
                  padding: '16px',
                  background: '#f5f5f5',
                  borderRadius: '6px'
                }}>
                  <p style={{ margin: '0 0 8px 0', fontWeight: 600 }}>当前签名信息:</p>
                  <div style={{ fontSize: '13px', color: '#666' }}>
                    <p><strong>签名者:</strong> {signature.metadata.signerName}</p>
                    <p><strong>时间:</strong> {new Date(signature.metadata.timestamp).toLocaleString()}</p>
                  </div>
                </div>
              )}

              {verificationResult && (
                <div style={{
                  padding: '16px',
                  background: verificationResult.valid ? '#e8f5e9' : '#ffebee',
                  borderRadius: '6px',
                  border: `1px solid ${verificationResult.valid ? '#81c784' : '#e57373'}`
                }}>
                  <p style={{ 
                    margin: '0 0 8px 0', 
                    fontWeight: 600,
                    color: verificationResult.valid ? '#2e7d32' : '#c62828'
                  }}>
                    {verificationResult.valid ? '✅ 签名有效' : '❌ 签名无效'}
                  </p>
                  <p style={{ margin: 0, fontSize: '14px' }}>{verificationResult.message}</p>
                  <p style={{ margin: '8px 0 0 0', fontSize: '13px', color: '#666' }}>
                    文档完整性: {verificationResult.integrity ? '✅ 未被篡改' : '⚠️ 可能被篡改'}
                  </p>
                </div>
              )}

              {!signature && !verificationResult && (
                <div style={{
                  textAlign: 'center',
                  padding: '40px',
                  color: '#999'
                }}>
                  <p style={{ fontSize: '48px', margin: '0 0 16px 0' }}>🔍</p>
                  <p>请先导入签名文件</p>
                  <p style={{ fontSize: '14px' }}>支持验证签名的真实性和文档完整性</p>
                </div>
              )}
            </div>
          )}
        </div>

        <div style={{
          padding: '16px 24px',
          borderTop: '1px solid #e0e0e0',
          display: 'flex',
          justifyContent: 'flex-end'
        }}>
          <button
            onClick={onClose}
            style={{
              padding: '8px 24px',
              border: '1px solid #ddd',
              background: 'white',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}
