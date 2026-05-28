import { useState, useRef, useCallback, useEffect } from 'react';
import SignaturePadComponent from './components/SignaturePad';
import type { SignaturePadHandle } from './components/SignaturePad';
import SignatureHistory from './components/SignatureHistory';
import SignerSelector from './components/SignerSelector';
import SignatureVerification from './components/SignatureVerification';
import SignatureTemplates from './components/SignatureTemplates';
import LegalDeclarationModal from './components/LegalDeclarationModal';
import type {
  SignatureData,
  SignatureStroke,
  Signer,
  SignatureTemplate,
  LegalDeclaration,
  ChainProof,
  BiometricVerificationResult,
} from './types';
import {
  generateId,
  exportToPNG,
  exportToSVG,
  downloadFile,
} from './utils/signatureUtils';
import {
  isWebAuthnSupported,
  performDualFactorAuthentication,
} from './utils/webAuthn';
import {
  setEncryptedStorage,
  getEncryptedStorage,
  isEncryptionSupported,
} from './utils/encryption';
import {
  generateSignatureHash,
  submitToBlockchain,
  getBlockchainStatus,
} from './utils/chainProof';
import './App.css';

type TabType = 'draw' | 'history' | 'templates' | 'signers' | 'verify';

function App() {
  const [activeTab, setActiveTab] = useState<TabType>('draw');
  const [strokes, setStrokes] = useState<SignatureStroke[]>([]);
  const [signatures, setSignatures] = useState<SignatureData[]>([]);
  const [templates, setTemplates] = useState<SignatureTemplate[]>([]);
  const [signers, setSigners] = useState<Signer[]>([
    {
      id: generateId(),
      name: '默认用户',
      verificationLevel: 'none',
      signatures: [],
    },
  ]);
  const [currentSigner, setCurrentSigner] = useState<Signer | null>(null);
  const [selectedHistorySignature, setSelectedHistorySignature] =
    useState<SignatureData | null>(null);
  const [penColor, setPenColor] = useState('#1a1a1a');
  const [penWidth, setPenWidth] = useState(3);
  const [notification, setNotification] = useState<{
    type: 'success' | 'error' | 'info';
    message: string;
  } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [encryptionSupported, setEncryptionSupported] = useState(true);

  const [showLegalModal, setShowLegalModal] = useState(false);
  const [pendingSignature, setPendingSignature] =
    useState<SignatureData | null>(null);
  const [signatureHash, setSignatureHash] = useState<string>('');
  const [chainProof, setChainProof] = useState<ChainProof | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [biometricResult, setBiometricResult] =
    useState<BiometricVerificationResult | null>(null);

  const padRef = useRef<SignaturePadHandle>(null);

  useEffect(() => {
    setEncryptionSupported(isEncryptionSupported());
  }, []);

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        const loadedSignatures =
          await getEncryptedStorage<SignatureData[]>('signaturePad_signatures');
        const loadedSigners =
          await getEncryptedStorage<Signer[]>('signaturePad_signers');
        const loadedTemplates =
          await getEncryptedStorage<SignatureTemplate[]>(
            'signaturePad_templates'
          );

        if (loadedSignatures) {
          setSignatures(loadedSignatures);
        }

        if (loadedTemplates) {
          setTemplates(loadedTemplates);
        }

        if (loadedSigners && loadedSigners.length > 0) {
          setSigners(loadedSigners);
          setCurrentSigner(loadedSigners[0]);
        } else {
          setCurrentSigner(signers[0]);
        }
      } catch (e) {
        console.error('Failed to load encrypted data', e);
        const savedSignatures = localStorage.getItem('signaturePad_signatures');
        const savedSigners = localStorage.getItem('signaturePad_signers');
        const savedTemplates = localStorage.getItem('signaturePad_templates');

        if (savedSignatures) {
          try {
            setSignatures(JSON.parse(savedSignatures));
          } catch {
          }
        }

        if (savedTemplates) {
          try {
            setTemplates(JSON.parse(savedTemplates));
          } catch {
          }
        }

        if (savedSigners) {
          try {
            const parsedSigners = JSON.parse(savedSigners);
            setSigners(parsedSigners);
            if (parsedSigners.length > 0) {
              setCurrentSigner(parsedSigners[0]);
            }
          } catch {
          }
        } else {
          setCurrentSigner(signers[0]);
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  useEffect(() => {
    if (!isLoading) {
      setEncryptedStorage('signaturePad_signatures', signatures).catch(
        () => {
          localStorage.setItem(
            'signaturePad_signatures',
            JSON.stringify(signatures)
          );
        }
      );
    }
  }, [signatures, isLoading]);

  useEffect(() => {
    if (!isLoading) {
      setEncryptedStorage('signaturePad_signers', signers).catch(() => {
        localStorage.setItem(
          'signaturePad_signers',
          JSON.stringify(signers)
        );
      });
    }
  }, [signers, isLoading]);

  useEffect(() => {
    if (!isLoading) {
      setEncryptedStorage('signaturePad_templates', templates).catch(() => {
        localStorage.setItem(
          'signaturePad_templates',
          JSON.stringify(templates)
        );
      });
    }
  }, [templates, isLoading]);

  useEffect(() => {
    const handleRequestSignature = (e: Event) => {
      const customEvent = e as CustomEvent;
      const { callback, imageData } = customEvent.detail;
      if (callback && strokes.length > 0) {
        callback(strokes, imageData);
      }
    };

    window.addEventListener('requestSignature', handleRequestSignature);
    return () => {
      window.removeEventListener('requestSignature', handleRequestSignature);
    };
  }, [strokes]);

  const showNotification = useCallback(
    (type: 'success' | 'error' | 'info', message: string) => {
      setNotification({ type, message });
      setTimeout(() => setNotification(null), 3000);
    },
    []
  );

  const handleSignatureChange = useCallback((newStrokes: SignatureStroke[]) => {
    setStrokes(newStrokes);
  }, []);

  const handleClear = useCallback(() => {
    if (padRef.current) {
      padRef.current.clear();
    }
    setStrokes([]);
  }, []);

  const handleUndo = useCallback(() => {
    if (padRef.current) {
      padRef.current.undo();
    }
  }, []);

  const handleSave = useCallback(() => {
    if (strokes.length === 0) {
      showNotification('error', '请先签名');
      return;
    }

    if (!currentSigner) {
      showNotification('error', '请先选择签名者');
      return;
    }

    const canvas = padRef.current?.getCanvas();
    const imageData = canvas ? exportToPNG(canvas) : undefined;

    const newSignature: SignatureData = {
      id: generateId(),
      strokes: [...strokes],
      signerId: currentSigner.id,
      signerName: currentSigner.name,
      createdAt: Date.now(),
      imageData,
    };

    const hash = generateSignatureHash(newSignature);
    newSignature.hash = hash;
    setSignatureHash(hash);
    setPendingSignature(newSignature);
    setChainProof(null);
    setBiometricResult(null);
    setShowLegalModal(true);
  }, [strokes, currentSigner, showNotification]);

  const handleConfirmSign = useCallback(
    async (declaration: LegalDeclaration, requireBiometric: boolean) => {
      if (!pendingSignature) return;

      setIsSubmitting(true);

      try {
        if (requireBiometric && currentSigner?.credentialId) {
          const result = await performDualFactorAuthentication(
            currentSigner.credentialId,
            currentSigner.credentialIdSecondary
          );
          setBiometricResult(result);

          if (!result.primaryVerified) {
            showNotification('error', '生物验证失败，无法签名');
            setIsSubmitting(false);
            return;
          }
        }

        const proof = await submitToBlockchain(pendingSignature);
        setChainProof(proof);

        const finalSignature: SignatureData = {
          ...pendingSignature,
          legalDeclaration: declaration,
          proof: proof || undefined,
        };

        setSignatures((prev) => [finalSignature, ...prev]);
        setSigners((prev) =>
          prev.map((s) =>
            s.id === currentSigner?.id
              ? { ...s, signatures: [...s.signatures, finalSignature.id] }
              : s
          )
        );
        setCurrentSigner((prev) =>
          prev
            ? { ...prev, signatures: [...prev.signatures, finalSignature.id] }
            : null
        );

        showNotification(
          'success',
          `签名保存成功${proof ? '，已上链存证' : ''}`
        );

        setTimeout(() => {
          setShowLegalModal(false);
          setPendingSignature(null);
          setChainProof(null);
          setBiometricResult(null);
          setSignatureHash('');
          handleClear();
        }, 1500);
      } catch (error) {
        showNotification('error', '签名保存失败');
      } finally {
        setIsSubmitting(false);
      }
    },
    [pendingSignature, currentSigner, handleClear, showNotification]
  );

  const handleExportPNG = useCallback(() => {
    const canvas = padRef.current?.getCanvas();
    if (!canvas || strokes.length === 0) {
      showNotification('error', '没有可导出的签名');
      return;
    }

    const dataUrl = exportToPNG(canvas);
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    downloadFile(dataUrl, `signature_${timestamp}.png`, 'image/png');
    showNotification('success', 'PNG导出成功');
  }, [strokes, showNotification]);

  const handleExportSVG = useCallback(() => {
    if (strokes.length === 0) {
      showNotification('error', '没有可导出的签名');
      return;
    }

    const canvas = padRef.current?.getCanvas();
    const width = canvas?.width || 800;
    const height = canvas?.height || 400;
    const svgContent = exportToSVG(strokes, width, height);
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    downloadFile(svgContent, `signature_${timestamp}.svg`, 'image/svg+xml');
    showNotification('success', 'SVG导出成功');
  }, [strokes, showNotification]);

  const handleAddSigner = useCallback(
    (signer: Signer) => {
      setSigners((prev) => [...prev, signer]);
      showNotification('success', `签名者"${signer.name}"添加成功`);
    },
    [showNotification]
  );

  const handleUpdateSigner = useCallback(
    (signer: Signer) => {
      setSigners((prev) =>
        prev.map((s) => (s.id === signer.id ? signer : s))
      );
      showNotification('success', `签名者"${signer.name}"已更新`);
    },
    [showNotification]
  );

  const handleDeleteSigner = useCallback(
    (id: string) => {
      const signer = signers.find((s) => s.id === id);
      if (!signer) return;

      if (signatures.some((sig) => sig.signerId === id)) {
        showNotification('error', '该签名者有关联的签名，无法删除');
        return;
      }

      setSigners((prev) => prev.filter((s) => s.id !== id));
      if (currentSigner?.id === id) {
        setCurrentSigner(signers.find((s) => s.id !== id) || null);
      }
      showNotification('success', `签名者"${signer.name}"已删除`);
    },
    [signers, signatures, currentSigner, showNotification]
  );

  const handleSelectSigner = useCallback(
    (signer: Signer) => {
      setCurrentSigner(signer);
      showNotification('info', `已切换到签名者"${signer.name}"`);
    },
    [showNotification]
  );

  const handleSelectHistorySignature = useCallback(
    (signature: SignatureData) => {
      setSelectedHistorySignature(signature);
      if (padRef.current) {
        padRef.current.loadStrokes(signature.strokes);
      }
      setStrokes(signature.strokes);
      showNotification('info', '已加载历史签名');
    },
    [showNotification]
  );

  const handleDeleteSignature = useCallback(
    (id: string) => {
      setSignatures((prev) => prev.filter((s) => s.id !== id));
      if (selectedHistorySignature?.id === id) {
        setSelectedHistorySignature(null);
      }
      showNotification('success', '签名已删除');
    },
    [selectedHistorySignature, showNotification]
  );

  const handleSaveTemplate = useCallback(
    (name: string, templateStrokes: SignatureStroke[], imageData: string) => {
      if (!currentSigner) return;

      const newTemplate: SignatureTemplate = {
        id: generateId(),
        name,
        strokes: templateStrokes,
        imageData,
        signerId: currentSigner.id,
        createdAt: Date.now(),
        usageCount: 0,
      };

      setTemplates((prev) => [newTemplate, ...prev]);
      showNotification('success', `模板"${name}"已保存`);
    },
    [currentSigner, showNotification]
  );

  const handleSelectTemplate = useCallback(
    (templateStrokes: SignatureStroke[]) => {
      if (padRef.current) {
        padRef.current.loadStrokes(templateStrokes);
      }
      setStrokes(templateStrokes);

      const templateId = templates.find(
        (t) =>
          JSON.stringify(t.strokes) === JSON.stringify(templateStrokes)
      )?.id;
      if (templateId) {
        setTemplates((prev) =>
          prev.map((t) =>
            t.id === templateId
              ? { ...t, usageCount: t.usageCount + 1, lastUsedAt: Date.now() }
              : t
          )
        );
      }

      showNotification('info', '已加载签名模板');
    },
    [templates, showNotification]
  );

  const handleDeleteTemplate = useCallback(
    (id: string) => {
      setTemplates((prev) => prev.filter((t) => t.id !== id));
      showNotification('success', '模板已删除');
    },
    [showNotification]
  );

  const handleUpdateTemplate = useCallback(
    (template: SignatureTemplate) => {
      setTemplates((prev) =>
        prev.map((t) => (t.id === template.id ? template : t))
      );
    },
    []
  );

  const chainStatus = getBlockchainStatus();
  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: 'draw', label: '签名', icon: '✏️' },
    { id: 'templates', label: '模板', icon: '📑' },
    { id: 'history', label: '历史', icon: '📋' },
    { id: 'signers', label: '签名者', icon: '👤' },
    { id: 'verify', label: '验证', icon: '🔍' },
  ];

  return (
    <div className="app">
      <header className="app-header">
        <h1>✍️ 签名板</h1>
        <div className="current-signer">
          {currentSigner && (
            <span>
              当前签名者: <strong>{currentSigner.name}</strong>
              {currentSigner.verificationLevel === 'dual' && (
                <span className="auth-badge dual">✓✓ 双重认证</span>
              )}
              {currentSigner.verificationLevel === 'single' && (
                <span className="auth-badge">✓ 已认证</span>
              )}
            </span>
          )}
        </div>
      </header>

      {notification && (
        <div className={`notification ${notification.type}`}>
          {notification.message}
        </div>
      )}

      <nav className="tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="tab-icon">{tab.icon}</span>
            <span className="tab-label">{tab.label}</span>
          </button>
        ))}
      </nav>

      <main className="main-content">
        {activeTab === 'draw' && (
          <div className="draw-panel">
            <div className="toolbar">
              <div className="tool-group">
                <label htmlFor="penColor">颜色:</label>
                <input
                  type="color"
                  id="penColor"
                  value={penColor}
                  onChange={(e) => setPenColor(e.target.value)}
                />
              </div>
              <div className="tool-group">
                <label htmlFor="penWidth">粗细: {penWidth}px</label>
                <input
                  type="range"
                  id="penWidth"
                  min="1"
                  max="20"
                  value={penWidth}
                  onChange={(e) => setPenWidth(Number(e.target.value))}
                />
              </div>
              <div className="tool-group">
                <button
                  onClick={handleUndo}
                  disabled={strokes.length === 0}
                >
                  ↶ 撤销
                </button>
                <button onClick={handleClear}>🗑️ 清除</button>
              </div>
              <div className="tool-group">
                <button
                  onClick={handleSave}
                  disabled={strokes.length === 0}
                >
                  💾 保存
                </button>
                <button
                  onClick={handleExportPNG}
                  disabled={strokes.length === 0}
                >
                  📤 PNG
                </button>
                <button
                  onClick={handleExportSVG}
                  disabled={strokes.length === 0}
                >
                  📤 SVG
                </button>
              </div>
            </div>

            <div className="signature-area">
              <SignaturePadComponent
                ref={padRef}
                onSignatureChange={handleSignatureChange}
                penColor={penColor}
                penWidth={penWidth}
                height={400}
                pressureSensitivity={true}
              />
              <p className="signature-hint">
                {strokes.length === 0
                  ? '请在上方区域使用鼠标或触屏进行签名（支持压感模拟）'
                  : `已绘制 ${strokes.length} 笔`}
              </p>
            </div>

            <div className="webauthn-info">
              <span className="info-icon">ℹ️</span>
              <span>
                {isWebAuthnSupported()
                  ? '支持WebAuthn生物认证'
                  : '不支持WebAuthn认证'}
                {' | '}
                {encryptionSupported
                  ? 'AES会话加密已启用'
                  : 'AES加密不可用'}
                {' | '}
                区块高度: #{chainStatus.blockHeight}
              </span>
            </div>
          </div>
        )}

        {activeTab === 'templates' && (
          <div className="templates-panel">
            <SignatureTemplates
              templates={templates}
              currentSignerId={currentSigner?.id || null}
              onSelectTemplate={handleSelectTemplate}
              onSaveTemplate={handleSaveTemplate}
              onDeleteTemplate={handleDeleteTemplate}
              onUpdateTemplate={handleUpdateTemplate}
              hasCurrentSignature={strokes.length > 0}
            />
          </div>
        )}

        {activeTab === 'history' && (
          <div className="history-panel">
            <SignatureHistory
              signatures={signatures}
              onSelect={handleSelectHistorySignature}
              onDelete={handleDeleteSignature}
              selectedId={selectedHistorySignature?.id}
            />
          </div>
        )}

        {activeTab === 'signers' && (
          <div className="signers-panel">
            <SignerSelector
              signers={signers}
              currentSignerId={currentSigner?.id || null}
              onSelectSigner={handleSelectSigner}
              onAddSigner={handleAddSigner}
              onUpdateSigner={handleUpdateSigner}
              onDeleteSigner={handleDeleteSigner}
            />
          </div>
        )}

        {activeTab === 'verify' && (
          <div className="verify-panel">
            <SignatureVerification
              referenceSignatures={signatures}
              onVerificationComplete={(result, reference) => {
                if (result.isVerified) {
                  showNotification(
                    'success',
                    `签名验证通过，与"${reference.signerName}"的签名匹配`
                  );
                } else {
                  showNotification('error', '签名验证失败');
                }
              }}
            />
          </div>
        )}
      </main>

      <LegalDeclarationModal
        isOpen={showLegalModal}
        onClose={() => {
          if (!isSubmitting) {
            setShowLegalModal(false);
            setPendingSignature(null);
            setChainProof(null);
            setBiometricResult(null);
            setSignatureHash('');
          }
        }}
        onConfirm={handleConfirmSign}
        signerName={currentSigner?.name || ''}
        biometricAvailable={
          isWebAuthnSupported() && !!currentSigner?.credentialId
        }
        verificationLevel={currentSigner?.verificationLevel || 'none'}
        verificationResult={biometricResult || undefined}
        chainProof={chainProof}
        signatureHash={signatureHash}
        isSubmitting={isSubmitting}
      />

      <footer className="app-footer">
        <p>
          基于 Canvas + React + WebAuthn + 区块链存证 构建 | 区块高度: #{chainStatus.blockHeight}
        </p>
      </footer>
    </div>
  );
}

export default App;
