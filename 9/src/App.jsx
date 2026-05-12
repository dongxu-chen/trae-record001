import { useState, useEffect, useCallback, useRef } from 'react';
import CodeEditor from './CodeEditor.jsx';

const { electronAPI } = window;

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

function formatDate(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleDateString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
}

function useDebouncedSave(delay = 500) {
  const timeoutRef = useRef(null);

  const debouncedSave = useCallback((updatedSnippets) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(() => {
      electronAPI.saveSnippets(updatedSnippets);
    }, delay);
  }, [delay]);

  const cancel = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  return { debouncedSave, cancel };
}

function getAllTags(snippets) {
  const tagMap = new Map();
  snippets.forEach(s => {
    (s.tags || []).forEach(tag => {
      const lower = tag.toLowerCase();
      tagMap.set(lower, (tagMap.get(lower) || 0) + 1);
    });
  });
  return Array.from(tagMap.entries())
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);
}

function SettingsModal({ settings, onClose, onSave, onUpload, onDownload }) {
  const [localSettings, setLocalSettings] = useState(settings);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    setLocalSettings(settings);
  }, [settings]);

  const handleSave = async () => {
    await onSave(localSettings);
    onClose();
  };

  const handleUpload = async () => {
    setSyncing(true);
    setMessage({ type: 'info', text: '正在上传...' });
    const result = await onUpload();
    setSyncing(false);
    if (result.success) {
      setMessage({ type: 'success', text: '上传成功！Gist ID: ' + result.gistId });
      setLocalSettings(prev => ({ ...prev, gistId: result.gistId }));
    } else {
      setMessage({ type: 'error', text: result.error || '上传失败' });
    }
  };

  const handleDownload = async () => {
    if (!localSettings.gistId) {
      setMessage({ type: 'error', text: '请先设置 Gist ID 或执行一次上传' });
      return;
    }
    setSyncing(true);
    setMessage({ type: 'info', text: '正在下载...' });
    const result = await onDownload();
    setSyncing(false);
    if (result.success) {
      setMessage({ type: 'success', text: `导入成功，共 ${result.snippets?.length || 0} 个片段` });
    } else {
      setMessage({ type: 'error', text: result.error || '下载失败' });
    }
  };

  return (
    <div className="settings-modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="settings-modal">
        <div className="settings-header">
          <h3>设置</h3>
          <button className="settings-close" onClick={onClose}>&times;</button>
        </div>
        <div className="settings-body">
          <div className="settings-section">
            <h4>云同步 (GitHub Gist)</h4>
            <div className="settings-item">
              <div className="settings-label">
                <strong>GitHub Personal Access Token</strong>
                <small>需要 gist 权限</small>
              </div>
              <input
                type="password"
                className="settings-input"
                placeholder="ghp_xxxxxxxxxxxx"
                value={localSettings.githubToken || ''}
                onChange={(e) => setLocalSettings(prev => ({ ...prev, githubToken: e.target.value }))}
              />
            </div>
            <div className="settings-item">
              <div className="settings-label">
                <strong>Gist ID (可选)</strong>
                <small>留空则自动创建新 Gist</small>
              </div>
              <input
                type="text"
                className="settings-input"
                placeholder="留空自动创建"
                value={localSettings.gistId || ''}
                onChange={(e) => setLocalSettings(prev => ({ ...prev, gistId: e.target.value }))}
              />
            </div>
            {message && (
              <div style={{
                padding: '10px 12px',
                borderRadius: '6px',
                marginTop: '12px',
                fontSize: '13px',
                backgroundColor: message.type === 'success' ? '#313244' :
                                 message.type === 'error' ? '#313244' : '#313244',
                color: message.type === 'success' ? '#a6e3a1' :
                       message.type === 'error' ? '#f38ba8' : '#89b4fa'
              }}>
                {message.text}
              </div>
            )}
            <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
              <button
                className="btn-settings btn-primary"
                onClick={handleUpload}
                disabled={syncing || !localSettings.githubToken}
              >
                {syncing ? '同步中...' : '上传到 Gist'}
              </button>
              <button
                className="btn-settings"
                onClick={handleDownload}
                disabled={syncing || !localSettings.githubToken || !localSettings.gistId}
              >
                从 Gist 导入
              </button>
            </div>
          </div>

          <div className="settings-section">
            <h4>安全</h4>
            <div className="settings-item">
              <div className="settings-label">
                <strong>本地加密存储</strong>
                <small>使用 AES-256-GCM 加密本地数据</small>
              </div>
              <input
                type="checkbox"
                className="settings-checkbox"
                checked={localSettings.encryptionEnabled ?? true}
                onChange={(e) => setLocalSettings(prev => ({ ...prev, encryptionEnabled: e.target.checked }))}
              />
            </div>
          </div>
        </div>
        <div className="settings-actions">
          <button className="btn-settings" onClick={onClose}>取消</button>
          <button className="btn-settings btn-primary" onClick={handleSave}>保存设置</button>
        </div>
      </div>
    </div>
  );
}

function App() {
  const [snippets, setSnippets] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [activeTag, setActiveTag] = useState(null);
  const [settings, setSettings] = useState({ encryptionEnabled: true, githubToken: null, gistId: null });
  const [showSettings, setShowSettings] = useState(false);
  const [syncState, setSyncState] = useState({ status: 'idle', message: null });
  const [newTagInput, setNewTagInput] = useState('');
  const { debouncedSave, cancel } = useDebouncedSave(500);

  const activeSnippet = snippets.find(s => s.id === activeId);
  const allTags = getAllTags(snippets);

  const filteredSnippets = activeTag
    ? snippets.filter(s => (s.tags || []).map(t => t.toLowerCase()).includes(activeTag.toLowerCase()))
    : snippets;

  useEffect(() => {
    async function loadInitial() {
      const [loadedSnippets, loadedSettings] = await Promise.all([
        electronAPI.getSnippets(),
        electronAPI.getSettings()
      ]);
      setSnippets(loadedSnippets);
      setSettings(loadedSettings);
    }
    loadInitial();

    const cleanup1 = electronAPI.onSnippetsChanged((updated) => {
      setSnippets(updated);
    });

    const cleanup2 = electronAPI.onSyncStatus((status) => {
      setSyncState({ status: status.success ? 'success' : 'error', message: status.message });
      setTimeout(() => setSyncState({ status: 'idle', message: null }), 3000);
    });

    const cleanup3 = electronAPI.onOpenGistSettings(() => {
      setShowSettings(true);
    });

    return () => {
      cleanup1();
      cleanup2();
      cleanup3();
      cancel();
    };
  }, [cancel]);

  const createNewSnippet = () => {
    const newSnippet = {
      id: generateId(),
      title: '未命名片段',
      language: 'javascript',
      code: '',
      tags: activeTag ? [activeTag] : [],
      createdAt: Date.now(),
      updatedAt: Date.now()
    };
    const updated = [newSnippet, ...snippets];
    setSnippets(updated);
    setActiveId(newSnippet.id);
    cancel();
    electronAPI.saveSnippets(updated);
  };

  const updateActiveSnippet = (field, value) => {
    if (!activeId) return;
    const updated = snippets.map(s =>
      s.id === activeId
        ? { ...s, [field]: value, updatedAt: Date.now() }
        : s
    );
    setSnippets(updated);
    debouncedSave(updated);
  };

  const addTagToActiveSnippet = (tag) => {
    if (!activeId || !tag.trim()) return;
    const trimmed = tag.trim();
    const current = activeSnippet.tags || [];
    if (current.map(t => t.toLowerCase()).includes(trimmed.toLowerCase())) return;
    updateActiveSnippet('tags', [...current, trimmed]);
    setNewTagInput('');
  };

  const removeTagFromActiveSnippet = (tagToRemove) => {
    if (!activeId) return;
    const current = activeSnippet.tags || [];
    const updated = current.filter(t => t.toLowerCase() !== tagToRemove.toLowerCase());
    updateActiveSnippet('tags', updated);
  };

  const deleteActiveSnippet = () => {
    if (!activeId) return;
    if (!confirm('确定要删除这个代码片段吗？')) return;
    const updated = snippets.filter(s => s.id !== activeId);
    setSnippets(updated);
    setActiveId(null);
    cancel();
    electronAPI.saveSnippets(updated);
  };

  const handleSaveSettings = async (newSettings) => {
    await electronAPI.saveSettings(newSettings);
    setSettings(newSettings);
  };

  const handleUpload = async () => {
    setSyncState({ status: 'syncing', message: '正在同步...' });
    const result = await electronAPI.uploadToGist();
    if (result.success) {
      setSyncState({ status: 'success', message: '同步成功' });
      setSettings(prev => ({ ...prev, gistId: result.gistId }));
    } else {
      setSyncState({ status: 'error', message: result.error || '同步失败' });
    }
    setTimeout(() => setSyncState({ status: 'idle', message: null }), 3000);
    return result;
  };

  const handleDownload = async () => {
    setSyncState({ status: 'syncing', message: '正在导入...' });
    const result = await electronAPI.downloadFromGist();
    if (result.success) {
      setSyncState({ status: 'success', message: '导入成功' });
      setSnippets(result.snippets);
    } else {
      setSyncState({ status: 'error', message: result.error || '导入失败' });
    }
    setTimeout(() => setSyncState({ status: 'idle', message: null }), 3000);
    return result;
  };

  return (
    <div className="app-container">
      <div className="top-bar">
        <div className="top-bar-left">
          <span className="top-bar-title">代码片段管理器</span>
          {syncState.status !== 'idle' && (
            <div className={`sync-status ${syncState.status}`}>
              <span className={`sync-dot ${syncState.status}`}></span>
              <span>{syncState.message}</span>
            </div>
          )}
        </div>
        <div className="editor-actions">
          <button
            className="btn-settings"
            onClick={handleUpload}
            disabled={syncState.status === 'syncing' || !settings.githubToken}
            title="上传到 Gist"
          >
            ⬆ 同步
          </button>
          <button
            className="btn-settings"
            onClick={handleDownload}
            disabled={syncState.status === 'syncing' || !settings.githubToken || !settings.gistId}
            title="从 Gist 导入"
          >
            ⬇ 导入
          </button>
          <button
            className="btn-settings"
            onClick={() => setShowSettings(true)}
          >
            ⚙ 设置
          </button>
        </div>
      </div>

      <div className="main-content">
        <aside className="sidebar">
          <div className="sidebar-header">
            <h2>代码片段</h2>
            <button className="new-btn" onClick={createNewSnippet}>
              + 新建
            </button>
          </div>

          {allTags.length > 0 && (
            <div className="tag-filter-bar">
              <div className="tag-filter-header">
                <span>标签筛选</span>
                {activeTag && (
                  <button className="tag-clear-btn" onClick={() => setActiveTag(null)}>
                    清除
                  </button>
                )}
              </div>
              <div className="tag-cloud">
                {allTags.map(tag => (
                  <span
                    key={tag.name}
                    className={`tag-chip ${activeTag?.toLowerCase() === tag.name ? 'active' : ''}`}
                    onClick={() => setActiveTag(
                      activeTag?.toLowerCase() === tag.name ? null : tag.name
                    )}
                  >
                    {tag.name}
                    <span className="tag-chip-count">{tag.count}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          <ul className="snippet-list">
            {filteredSnippets.length === 0 ? (
              <li style={{
                padding: '40px 16px',
                textAlign: 'center',
                color: '#6c7086',
                fontSize: '13px'
              }}>
                {activeTag ? `没有「${activeTag}」标签的片段` : '暂无代码片段'}
              </li>
            ) : (
              filteredSnippets.map(snippet => (
                <li
                  key={snippet.id}
                  className={`snippet-item ${snippet.id === activeId ? 'active' : ''}`}
                  onClick={() => setActiveId(snippet.id)}
                >
                  <div className="snippet-title">{snippet.title}</div>
                  <div className="snippet-meta">
                    <span className="snippet-lang">{snippet.language}</span>
                    <span>{formatDate(snippet.updatedAt)}</span>
                  </div>
                  {(snippet.tags || []).length > 0 && (
                    <div className="snippet-tags">
                      {snippet.tags.slice(0, 3).map(tag => (
                        <span key={tag} className="snippet-tag">{tag}</span>
                      ))}
                      {(snippet.tags || []).length > 3 && (
                        <span className="snippet-tag">+{snippet.tags.length - 3}</span>
                      )}
                    </div>
                  )}
                </li>
              ))
            )}
          </ul>
        </aside>

        <main className="editor-container">
          {activeSnippet ? (
            <>
              <div className="editor-header">
                <div className="editor-fields">
                  <input
                    type="text"
                    className="input-title"
                    placeholder="片段标题"
                    value={activeSnippet.title}
                    onChange={(e) => updateActiveSnippet('title', e.target.value)}
                  />
                  <div className="editor-row">
                    <input
                      type="text"
                      className="input-lang"
                      placeholder="语言"
                      value={activeSnippet.language}
                      onChange={(e) => updateActiveSnippet('language', e.target.value)}
                    />
                    <div className="editor-tags-section">
                      <div className="editor-tags">
                        {(activeSnippet.tags || []).map(tag => (
                          <span key={tag} className="editor-tag">
                            {tag}
                            <button
                              className="remove"
                              onClick={(e) => {
                                e.stopPropagation();
                                removeTagFromActiveSnippet(tag);
                              }}
                            >
                              &times;
                            </button>
                          </span>
                        ))}
                        <input
                          type="text"
                          className="tag-input-sm"
                          placeholder="添加标签 + Enter"
                          value={newTagInput}
                          onChange={(e) => setNewTagInput(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && newTagInput.trim()) {
                              addTagToActiveSnippet(newTagInput);
                            }
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
                <div className="editor-actions">
                  <button
                    className="btn btn-delete"
                    onClick={deleteActiveSnippet}
                  >
                    删除
                  </button>
                </div>
              </div>
              <CodeEditor
                value={activeSnippet.code}
                onChange={(code) => updateActiveSnippet('code', code)}
                language={activeSnippet.language}
              />
            </>
          ) : snippets.length === 0 ? (
            <div className="empty-state">
              <h3>暂无代码片段</h3>
              <p>点击左侧的「新建」按钮创建你的第一个代码片段</p>
            </div>
          ) : (
            <div className="empty-state">
              <h3>请选择一个代码片段</h3>
              <p>从左侧列表中选择一个片段进行查看和编辑</p>
            </div>
          )}
        </main>
      </div>

      {showSettings && (
        <SettingsModal
          settings={settings}
          onClose={() => setShowSettings(false)}
          onSave={handleSaveSettings}
          onUpload={handleUpload}
          onDownload={handleDownload}
        />
      )}
    </div>
  );
}

export default App;
