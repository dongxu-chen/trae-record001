import React, { useState, useCallback, useRef } from 'react';
import axios from 'axios';
import ImageUpload from './components/ImageUpload.jsx';
import CodeOutput from './components/CodeOutput.jsx';
import FlowchartPreview from './components/FlowchartPreview.jsx';

const CODE_TABS = [
  { key: 'pseudocode', label: '伪代码', test: false },
  { key: 'python', label: 'Python', test: true, lang: 'python' },
  { key: 'java', label: 'Java', test: true, lang: 'java' },
  { key: 'go', label: 'Go', test: true, lang: 'go' },
  { key: 'javascript', label: 'JavaScript', test: true, lang: 'javascript' },
  { key: 'plantuml', label: 'PlantUML', test: false },
];

const getTabLabel = (key) => {
  if (key.startsWith('test_')) {
    const lang = key.replace('test_', '');
    const langName = { python: 'Python', java: 'Java', go: 'Go', javascript: 'JS' }[lang] || lang;
    return `🧪 ${langName}测试`;
  }
  return CODE_TABS.find((t) => t.key === key)?.label || key;
};

const getTabLanguage = (key) => {
  if (key.startsWith('test_')) return 'text';
  const langMap = {
    pseudocode: 'text',
    python: 'python',
    java: 'java',
    go: 'go',
    javascript: 'javascript',
    plantuml: 'text',
  };
  return langMap[key] || 'text';
};

export default function App() {
  const [imageUrl, setImageUrl] = useState(null);
  const [activeTab, setActiveTab] = useState('pseudocode');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [editedNodes, setEditedNodes] = useState(null);
  const [editedEdges, setEditedEdges] = useState(null);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState(null);

  const handleFileSelect = useCallback(async (file) => {
    if (!file) return;

    setImageUrl(URL.createObjectURL(file));
    setLoading(true);
    setError(null);
    setResult(null);
    setEditMode(false);
    setEditedNodes(null);
    setEditedEdges(null);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);

    const formData = new FormData();
    formData.append('image', file);

    try {
      const res = await axios.post('/api/process', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
      });
      setResult(res.data);
      setEditedNodes(res.data.nodes || []);
      setEditedEdges(res.data.edges || []);
      if (res.data.warning) {
        setError(res.data.warning);
      }
    } catch (err) {
      console.error('Upload failed:', err);
      setError(err.response?.data?.error || err.message || '上传失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleReset = useCallback(() => {
    if (imageUrl) URL.revokeObjectURL(imageUrl);
    setImageUrl(null);
    setResult(null);
    setError(null);
    setEditMode(false);
    setEditedNodes(null);
    setEditedEdges(null);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
  }, [imageUrl]);

  const handleRegenerate = useCallback(async () => {
    if (!editedNodes || editedNodes.length === 0) return;

    setRegenerating(true);
    setError(null);

    try {
      const res = await axios.post(
        '/api/regenerate',
        {
          nodes: editedNodes,
          edges: editedEdges,
          language: 'all',
        },
        { timeout: 30000 }
      );
      setResult((prev) => ({
        ...prev,
        ...res.data,
        nodes: editedNodes,
        edges: editedEdges,
      }));
    } catch (err) {
      console.error('Regenerate failed:', err);
      setError(err.response?.data?.error || err.message || '重新生成失败');
    } finally {
      setRegenerating(false);
    }
  }, [editedNodes, editedEdges]);

  const handleNodesChange = useCallback((nodes) => {
    setEditedNodes(nodes);
  }, []);

  const handleEdgesChange = useCallback((edges) => {
    setEditedEdges(edges);
  }, []);

  const allTabs = [
    ...CODE_TABS.map((t) => ({ key: t.key, label: getTabLabel(t.key), test: false })),
    ...(result?.tests
      ? Object.keys(result.tests).map((lang) => ({
          key: `test_${lang}`,
          label: getTabLabel(`test_${lang}`),
          test: true,
        }))
      : []),
  ];

  const getActiveCode = () => {
    if (!result) return '';
    if (activeTab.startsWith('test_')) {
      const lang = activeTab.replace('test_', '');
      return result.tests?.[lang] || '';
    }
    return result[activeTab] || '';
  };

  const hasChanges =
    editedNodes &&
    result &&
    (JSON.stringify(editedNodes) !== JSON.stringify(result.nodes) ||
      JSON.stringify(editedEdges) !== JSON.stringify(result.edges));

  return (
    <div className="app">
      <header className="app-header">
        <h1>流程图转代码工具</h1>
        <p className="subtitle">
          上传 UML 活动图 / 流程图，自动识别节点类型并生成多语言代码，支持交互式修正
        </p>
      </header>

      <main className="app-main">
        <section className="upload-section">
          <ImageUpload onFileSelect={handleFileSelect} loading={loading} onReset={handleReset} />
          {error && <div className="error-msg">{error}</div>}
        </section>

        {imageUrl && (
          <section className="preview-section">
            <div className="section-header">
              <h2>流程图预览</h2>
              {result && (
                <div className="edit-mode-actions">
                  <button
                    className={`edit-toggle-btn ${editMode ? 'active' : ''}`}
                    onClick={() => {
                      setEditMode(!editMode);
                      setSelectedNodeId(null);
                      setSelectedEdgeId(null);
                    }}
                  >
                    {editMode ? '✓ 完成编辑' : '✏️ 编辑修正'}
                  </button>
                  {editMode && (
                    <button
                      className="regenerate-btn"
                      onClick={handleRegenerate}
                      disabled={regenerating || !hasChanges}
                    >
                      {regenerating ? '⏳ 重新生成中...' : hasChanges ? '🔄 应用修改并生成代码' : ' 应用修改'}
                    </button>
                  )}
                </div>
              )}
            </div>

            {editMode && (
              <div className="edit-hint">
                💡 提示：拖拽节点移动位置，拖拽四角调整大小，点击节点/连线可编辑属性，修改完成后点击"应用修改"按钮
              </div>
            )}

            <FlowchartPreview
              imageUrl={imageUrl}
              nodes={editedNodes || result?.nodes || []}
              edges={editedEdges || result?.edges || []}
              editMode={editMode}
              onNodesChange={handleNodesChange}
              onEdgesChange={handleEdgesChange}
              selectedNodeId={selectedNodeId}
              onSelectNode={setSelectedNodeId}
              selectedEdgeId={selectedEdgeId}
              onSelectEdge={setSelectedEdgeId}
            />
          </section>
        )}

        {result && (
          <section className="output-section">
            <h2>生成结果</h2>
            <div className="tabs">
              {allTabs.map((tab) => (
                <button
                  key={tab.key}
                  className={`tab-btn ${activeTab === tab.key ? 'active' : ''} ${tab.test ? 'test-tab' : ''}`}
                  onClick={() => setActiveTab(tab.key)}
                >
                  {tab.label}
                </button>
              ))}
            </div>
            <CodeOutput
              code={getActiveCode()}
              language={getTabLanguage(activeTab)}
              label={getTabLabel(activeTab)}
            />
          </section>
        )}

        {loading && (
          <div className="loading-overlay">
            <div className="spinner" />
            <p>正在分析流程图，请稍候...</p>
          </div>
        )}

        {regenerating && (
          <div className="loading-overlay">
            <div className="spinner" />
            <p>正在重新生成代码...</p>
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>基于 OpenCV + PaddleOCR + React + Node.js 构建 | 支持 Python / Java / Go / JS 多语言生成</p>
      </footer>
    </div>
  );
}
