import React, { useState, useCallback } from 'react';
import { generateShareLink } from '../utils/timelineUtils';

const SnapshotShare = ({
  timeRange,
  timeUnit,
  filterKeywords = '',
  filterTypes = [],
  onRestoreSnapshot,
  savedSnapshots = [],
  onSaveSnapshot
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [shareLink, setShareLink] = useState('');
  const [copied, setCopied] = useState(false);
  const [snapshotName, setSnapshotName] = useState('');

  const generateLink = useCallback(() => {
    const state = {
      timeRange,
      timeUnit,
      filterKeywords,
      filterTypes
    };
    const link = generateShareLink(state);
    setShareLink(link);
    setCopied(false);
  }, [timeRange, timeUnit, filterKeywords, filterTypes]);

  const handleCopyLink = useCallback(async () => {
    if (!shareLink) {
      generateLink();
    }
    try {
      await navigator.clipboard.writeText(shareLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      const textArea = document.createElement('textarea');
      textArea.value = shareLink;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [shareLink, generateLink]);

  const handleSaveSnapshot = useCallback(() => {
    if (!snapshotName.trim()) return;
    const snapshot = {
      id: Date.now().toString(),
      name: snapshotName.trim(),
      timeRange,
      timeUnit,
      filterKeywords,
      filterTypes,
      createdAt: Date.now()
    };
    onSaveSnapshot && onSaveSnapshot(snapshot);
    setSnapshotName('');
    setIsOpen(false);
  }, [snapshotName, timeRange, timeUnit, filterKeywords, filterTypes, onSaveSnapshot]);

  const handleLoadSnapshot = useCallback((snapshot) => {
    onRestoreSnapshot && onRestoreSnapshot(snapshot);
    setIsOpen(false);
  }, [onRestoreSnapshot]);

  const formatDate = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="snapshot-share-container">
      <button
        className="snapshot-toggle-btn"
        onClick={() => {
          setIsOpen(!isOpen);
          if (!isOpen) generateLink();
        }}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
          <polyline points="16 6 12 2 8 6" />
          <line x1="12" y1="2" x2="12" y2="15" />
        </svg>
        快照/分享
      </button>

      {isOpen && (
        <div className="snapshot-dropdown">
          <div className="snapshot-section">
            <h4 className="snapshot-section-title">分享链接</h4>
            <div className="share-link-section">
              <input
                type="text"
                className="share-link-input"
                value={shareLink}
                readOnly
                placeholder="点击生成分享链接"
              />
              <button
                className={`copy-link-btn ${copied ? 'copied' : ''}`}
                onClick={handleCopyLink}
              >
                {copied ? '已复制' : '复制'}
              </button>
            </div>
          </div>

          <div className="snapshot-divider" />

          <div className="snapshot-section">
            <h4 className="snapshot-section-title">保存快照</h4>
            <div className="save-snapshot-section">
              <input
                type="text"
                className="snapshot-name-input"
                placeholder="输入快照名称"
                value={snapshotName}
                onChange={(e) => setSnapshotName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSaveSnapshot()}
              />
              <button
                className="save-snapshot-btn"
                onClick={handleSaveSnapshot}
                disabled={!snapshotName.trim()}
              >
                保存
              </button>
            </div>
          </div>

          {savedSnapshots.length > 0 && (
            <>
              <div className="snapshot-divider" />
              <div className="snapshot-section">
                <h4 className="snapshot-section-title">已保存快照</h4>
                <div className="saved-snapshots-list">
                  {savedSnapshots.map(snapshot => (
                    <div
                      key={snapshot.id}
                      className="saved-snapshot-item"
                      onClick={() => handleLoadSnapshot(snapshot)}
                    >
                      <div className="snapshot-item-info">
                        <span className="snapshot-item-name">{snapshot.name}</span>
                        <span className="snapshot-item-date">
                          {formatDate(snapshot.createdAt)}
                        </span>
                      </div>
                      <svg
                        className="snapshot-item-arrow"
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <polyline points="9 18 15 12 9 6" />
                      </svg>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default SnapshotShare;
