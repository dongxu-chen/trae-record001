import React, { useState } from 'react';
import { X, Eye, FileSearch, Check, AlertCircle } from 'lucide-react';
import { usePdfContext } from '../contexts/PdfContext';

interface OcrPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const OcrPanel: React.FC<OcrPanelProps> = ({ isOpen, onClose }) => {
  const { state, addAnnotation } = usePdfContext();
  const [selectedPage, setSelectedPage] = useState<number>(state.viewer.currentPage);
  const [isRecognizing, setIsRecognizing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [ocrResults, setOcrResults] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !state.document) return null;

  const handleRecognize = async () => {
    setIsRecognizing(true);
    setProgress(0);
    setOcrResults([]);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', state.document!.file);
      formData.append('pages', JSON.stringify([selectedPage]));

      const response = await fetch('/api/ocr/recognize', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('OCR识别失败');
      }

      const { taskId } = await response.json();

      const checkStatus = async () => {
        try {
          const statusRes = await fetch(`/api/ocr/${taskId}/status`);
          const statusData = await statusRes.json();

          setProgress(statusData.progress);

          if (statusData.status === 'completed') {
            setOcrResults(statusData.results);
            setIsRecognizing(false);
          } else if (statusData.status === 'failed') {
            setError('识别失败，请重试');
            setIsRecognizing(false);
          } else if (statusData.status === 'processing') {
            setTimeout(checkStatus, 500);
          }
        } catch (err) {
          setError('查询进度失败');
          setIsRecognizing(false);
        }
      };

      checkStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : '识别失败');
      setIsRecognizing(false);
    }
  };

  const handleHighlightResult = (result: any) => {
    addAnnotation({
      type: 'highlight',
      pageIndex: selectedPage,
      position: {
        x: result.position.x,
        y: result.position.y,
        width: result.position.width || 0.15,
        height: result.position.height || 0.05,
      },
      color: '#FFEB3B',
      content: result.text.substring(0, 50),
    });
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden shadow-2xl">
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <FileSearch className="text-primary-600" size={24} />
            OCR文字识别
          </h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-4">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
              <AlertCircle size={18} />
              {error}
            </div>
          )}

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              选择页面
            </label>
            <select
              value={selectedPage}
              onChange={(e) => setSelectedPage(Number(e.target.value))}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              disabled={isRecognizing}
            >
              {Array.from({ length: state.document.numPages }, (_, i) => (
                <option key={i} value={i}>
                  第 {i + 1} 页
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleRecognize}
            disabled={isRecognizing}
            className="w-full py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isRecognizing ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                识别中 {progress}%
              </>
            ) : (
              <>
                <Eye size={20} />
                开始识别
              </>
            )}
          </button>

          {isRecognizing && (
            <div className="mt-4">
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary-600 transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          {ocrResults.length > 0 && (
            <div className="mt-6">
              <h4 className="text-sm font-medium text-gray-700 mb-3">
                识别结果 ({ocrResults.length} 项)
              </h4>
              <div className="max-h-64 overflow-auto space-y-2">
                {ocrResults.map((result, index) => (
                  <div
                    key={index}
                    className="p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-gray-500">
                        置信度: {Math.round(result.confidence * 100)}%
                      </span>
                      <button
                        onClick={() => handleHighlightResult(result)}
                        className="text-xs text-primary-600 hover:text-primary-700 flex items-center gap-1"
                      >
                        <Check size={14} />
                        高亮标注
                      </button>
                    </div>
                    <p className="text-sm text-gray-800 line-clamp-2">
                      {result.text}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default OcrPanel;
