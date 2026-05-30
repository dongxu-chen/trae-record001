import React, { useCallback } from 'react';

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void;
  isDragOver: boolean;
  onDragOverChange: (over: boolean) => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onFilesSelected, isDragOver, onDragOverChange }) => {
  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const imageFiles = files.filter(file => file.type.startsWith('image/'));
    onFilesSelected(imageFiles);
    e.target.value = '';
  }, [onFilesSelected]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    onDragOverChange(true);
  }, [onDragOverChange]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    onDragOverChange(false);
  }, [onDragOverChange]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    onDragOverChange(false);
    const files = Array.from(e.dataTransfer.files || []);
    const imageFiles = files.filter(file => file.type.startsWith('image/'));
    onFilesSelected(imageFiles);
  }, [onFilesSelected, onDragOverChange]);

  return (
    <div
      className={`upload-zone ${isDragOver ? 'drag-over' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input
        type="file"
        multiple
        accept="image/jpeg,image/png,image/webp"
        onChange={handleFileChange}
        className="file-input"
        id="file-input"
      />
      <label htmlFor="file-input" className="upload-label">
        <div className="upload-icon">📁</div>
        <div className="upload-text">
          <h3>拖拽图片到此处，或点击选择文件</h3>
          <p>支持 JPEG、PNG、WebP 格式，支持批量上传</p>
        </div>
      </label>
    </div>
  );
};
