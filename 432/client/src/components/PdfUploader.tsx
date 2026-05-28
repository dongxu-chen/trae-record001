import React, { useState, useCallback, useRef } from 'react';
import { Upload, FileText } from 'lucide-react';
import { usePdfContext } from '../contexts/PdfContext';
import * as pdfjsLib from 'pdfjs-dist';
import { parseOutline } from '../utils/outlineUtils';
import { generateId } from '../utils/coordinateUtils';

pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js`;

const PdfUploader: React.FC = () => {
  const { dispatch } = usePdfContext();
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(async (file: File) => {
    if (file.type !== 'application/pdf') {
      alert('请上传PDF文件');
      return;
    }

    setIsLoading(true);
    try {
      const arrayBuffer = await file.arrayBuffer();
      const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

      const pageSizes = [];
      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const viewport = page.getViewport({ scale: 1 });
        pageSizes.push({ width: viewport.width, height: viewport.height });
      }

      const rawOutline = await pdf.getOutline();
      const outlines = await parseOutline(rawOutline, pdf);

      dispatch({
        type: 'SET_DOCUMENT',
        payload: {
          id: generateId(),
          name: file.name,
          file,
          numPages: pdf.numPages,
          annotations: [],
          outlines,
          pageSizes,
        },
      });
    } catch (error) {
      console.error('Error loading PDF:', error);
      alert('PDF加载失败，请重试');
    } finally {
      setIsLoading(false);
    }
  }, [dispatch]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="flex items-center justify-center h-full bg-gradient-to-br from-gray-50 to-gray-100">
      <div
        className={`upload-zone text-center max-w-lg ${isDragging ? 'dragging' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={handleClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleInputChange}
          className="hidden"
        />
        
        {isLoading ? (
          <div className="py-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary-100 flex items-center justify-center">
              <div className="w-8 h-8 border-3 border-primary-600 border-t-transparent rounded-full animate-spin" />
            </div>
            <p className="text-gray-600">正在加载PDF...</p>
          </div>
        ) : (
          <>
            <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-br from-primary-100 to-primary-200 flex items-center justify-center">
              {isDragging ? (
                <FileText className="w-10 h-10 text-primary-600" />
              ) : (
                <Upload className="w-10 h-10 text-primary-600" />
              )}
            </div>
            <h2 className="text-xl font-semibold text-gray-800 mb-2">
              上传PDF文件
            </h2>
            <p className="text-gray-500 mb-4">
              拖拽PDF文件到此处，或点击选择文件
            </p>
            <button
              className="px-6 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                handleClick();
              }}
            >
              选择PDF文件
            </button>
            <p className="text-xs text-gray-400 mt-4">
              支持拖拽上传 • 最大50MB
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export default PdfUploader;
