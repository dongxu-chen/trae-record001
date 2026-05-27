import React, { useState, useRef, useEffect } from 'react';
import { X, Save, Share2 } from 'lucide-react';
import './index.less';

interface SaveThemeModalProps {
  visible: boolean;
  onClose: () => void;
  onSave: (name: string, description: string, isShared: boolean) => boolean;
}

const SaveThemeModal: React.FC<SaveThemeModalProps> = ({ visible, onClose, onSave }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isShared, setIsShared] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (visible && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [visible]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('请输入主题名称');
      return;
    }

    const success = onSave(name.trim(), description.trim(), isShared);
    if (success) {
      setName('');
      setDescription('');
      setIsShared(false);
      onClose();
    } else {
      setError('保存失败，请重试');
    }
  };

  const handleClose = () => {
    setName('');
    setDescription('');
    setIsShared(false);
    setError(null);
    onClose();
  };

  if (!visible) return null;

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">
            <Save size={18} />
            保存主题
          </h3>
          <button className="modal-close" onClick={handleClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-group">
            <label className="form-label">主题名称 *</label>
            <input
              ref={inputRef}
              type="text"
              className="form-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="请输入主题名称"
              maxLength={50}
            />
          </div>

          <div className="form-group">
            <label className="form-label">主题描述</label>
            <textarea
              className="form-textarea"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="请输入主题描述（可选）"
              rows={3}
              maxLength={200}
            />
          </div>

          <div className="form-group">
            <label className="form-checkbox">
              <input
                type="checkbox"
                checked={isShared}
                onChange={(e) => setIsShared(e.target.checked)}
              />
              <span className="checkbox-icon" />
              <Share2 size={16} />
              <span>加入团队共享库</span>
            </label>
          </div>

          {error && <div className="form-error">{error}</div>}

          <div className="modal-actions">
            <button type="button" className="btn-cancel" onClick={handleClose}>
              取消
            </button>
            <button type="submit" className="btn-confirm">
              <Save size={16} />
              保存
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default SaveThemeModal;
