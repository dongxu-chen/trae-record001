import React, { useState, useRef } from 'react';
import axios from 'axios';

function VideoUploader({ apiBase, onUploadComplete }) {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleUpload = async (file) => {
    if (!file) return;

    const validTypes = ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-matroska', 'video/webm', 'video/x-flv'];
    const validExts = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v'];
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();

    if (!validTypes.includes(file.type) && !validExts.includes(ext)) {
      setError('不支持的视频格式，请上传 MP4/AVI/MOV/MKV/WebM 格式');
      return;
    }

    if (file.size > 500 * 1024 * 1024) {
      setError('文件大小不能超过 500MB');
      return;
    }

    setError(null);
    setUploading(true);

    const formData = new FormData();
    formData.append('video', file);

    try {
      const response = await axios.post(`${apiBase}/upload`, formData, {
        onUploadProgress: (e) => {
          const pct = Math.round((e.loaded / e.total) * 100);
          setProgress(pct);
        }
      });

      if (response.data.success) {
        onUploadComplete(response.data.video);
      } else {
        setError(response.data.error || '上传失败');
      }
    } catch (err) {
      setError(err.response?.data?.error || '上传失败，请重试');
    } finally {
      setUploading(false);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleUpload(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleUpload(e.target.files[0]);
    }
  };

  return (
    <div className="uploader-container">
      <div
        className={`upload-zone ${dragActive ? 'drag-active' : ''} ${uploading ? 'uploading' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="video/*"
          onChange={handleChange}
          style={{ display: 'none' }}
        />

        {uploading ? (
          <div className="upload-progress">
            <div className="progress-ring">
              <svg viewBox="0 0 100 100">
                <circle className="progress-bg" cx="50" cy="50" r="45" />
                <circle
                  className="progress-fill"
                  cx="50" cy="50" r="45"
                  style={{ strokeDashoffset: 283 - (283 * progress / 100) }}
                />
              </svg>
              <span className="progress-text">{progress}%</span>
            </div>
            <p className="upload-status">正在上传视频...</p>
          </div>
        ) : (
          <div className="upload-prompt">
            <span className="material-icons-round upload-icon">cloud_upload</span>
            <h2>拖拽视频文件到这里</h2>
            <p>或点击选择文件</p>
            <div className="upload-formats">
              支持 MP4 / AVI / MOV / MKV / WebM，最大 500MB
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="upload-error">
          <span className="material-icons-round">error</span>
          {error}
        </div>
      )}

      <div className="upload-features">
        <div className="feature-card">
          <span className="material-icons-round">auto_awesome</span>
          <h3>智能高光检测</h3>
          <p>自动识别运动高潮、画面变化、音量峰值等精彩片段</p>
        </div>
        <div className="feature-card">
          <span className="material-icons-round">content_cut</span>
          <h3>灵活剪辑</h3>
          <p>自定义剪辑时长，支持多场景智能拼接</p>
        </div>
        <div className="feature-card">
          <span className="material-icons-round">file_download</span>
          <h3>多格式导出</h3>
          <p>支持 MP4、WebM、AVI、MOV、GIF 多种格式导出</p>
        </div>
      </div>
    </div>
  );
}

export default VideoUploader;
