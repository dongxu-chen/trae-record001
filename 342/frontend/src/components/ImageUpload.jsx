import React, { useRef, useState } from 'react';

const ACCEPTED_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/bmp', 'image/webp'];

export default function ImageUpload({ onFileSelect, loading, onReset }) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (loading) return;
    const file = e.dataTransfer.files?.[0];
    if (file && ACCEPTED_TYPES.includes(file.type)) {
      onFileSelect(file);
    }
  };

  const handleSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) onFileSelect(file);
  };

  return (
    <div
      className={`upload-area ${dragOver ? 'drag-over' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => !loading && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
        onChange={handleSelect}
      />
      <div className="upload-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
      </div>
      <p className="upload-text">
        {loading ? '处理中...' : '拖拽流程图图片到此处，或点击上传'}
      </p>
      <p className="upload-hint">支持 PNG / JPEG / BMP / WebP，最大 10MB</p>
      {onReset && (
        <button
          className="reset-btn"
          onClick={(e) => { e.stopPropagation(); onReset(); }}
          disabled={loading}
        >
          清除
        </button>
      )}
    </div>
  );
}
