import { useState, useEffect, useCallback } from 'react';
import { X, Key, Check } from 'lucide-react';
import { useEditorStore } from '@/store/useEditorStore';
import { getSettings, saveSettings, type Settings } from '@/db/database';

export default function SettingsModal() {
  const { showSettingsModal, toggleSettingsModal } = useEditorStore();
  const [appId, setAppId] = useState('');
  const [appKey, setAppKey] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (showSettingsModal) {
      getSettings().then((s) => {
        if (s) {
          setAppId(s.mathpixAppId || '');
          setAppKey(s.mathpixAppKey || '');
        }
      });
    }
  }, [showSettingsModal]);

  const handleSave = useCallback(async () => {
    await saveSettings({
      mathpixAppId: appId,
      mathpixAppKey: appKey,
      editorMode: 'visual',
      exportFormat: 'png',
      theme: 'dark',
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }, [appId, appKey]);

  if (!showSettingsModal) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-fade-in" onClick={toggleSettingsModal}>
      <div
        className="bg-bg-secondary rounded-xl shadow-2xl w-[420px] animate-scale-in overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-border-custom">
          <span className="text-sm font-medium text-text-primary">设置</span>
          <button onClick={toggleSettingsModal} className="p-1 text-text-muted hover:text-text-primary transition-colors rounded hover:bg-bg-tertiary">
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-5">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Key size={14} className="text-accent" />
              <span className="text-sm font-medium text-text-primary">Mathpix 手写识别 API</span>
            </div>
            <p className="text-xs text-text-muted leading-relaxed">
              配置 Mathpix API 密钥以启用手写公式识别功能。未配置时将使用演示模式。
              访问 <a href="https://mathpix.com" target="_blank" rel="noopener noreferrer" className="text-accent hover:text-accent-hover">mathpix.com</a> 获取密钥。
            </p>
            <div className="space-y-2">
              <div>
                <label className="text-xs text-text-muted">App ID</label>
                <input
                  type="text"
                  value={appId}
                  onChange={(e) => setAppId(e.target.value)}
                  placeholder="输入 Mathpix App ID"
                  className="w-full mt-1 bg-bg-tertiary text-sm text-text-primary placeholder:text-text-muted rounded-lg px-3 py-2 outline-none border border-border-custom focus:border-accent"
                />
              </div>
              <div>
                <label className="text-xs text-text-muted">App Key</label>
                <input
                  type="password"
                  value={appKey}
                  onChange={(e) => setAppKey(e.target.value)}
                  placeholder="输入 Mathpix App Key"
                  className="w-full mt-1 bg-bg-tertiary text-sm text-text-primary placeholder:text-text-muted rounded-lg px-3 py-2 outline-none border border-border-custom focus:border-accent"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-border-custom">
          <button
            onClick={toggleSettingsModal}
            className="px-4 py-1.5 text-sm text-text-secondary bg-bg-tertiary rounded-lg hover:text-text-primary transition-colors"
          >
            关闭
          </button>
          <button
            onClick={handleSave}
            className="flex items-center gap-1.5 px-4 py-1.5 text-sm bg-accent text-bg-primary font-medium rounded-lg hover:bg-accent-hover transition-colors"
          >
            {saved ? <Check size={14} /> : null}
            {saved ? '已保存' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
