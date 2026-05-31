import React, { useState, useRef, useCallback } from 'react';
import axios from 'axios';
import './ImageEditor.css';

function ImageEditor() {
  const [image, setImage] = useState(null);
  const [processedImage, setProcessedImage] = useState(null);
  const [brushSize, setBrushSize] = useState(20);
  const [isDrawing, setIsDrawing] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [algorithm, setAlgorithm] = useState('edge-guided');
  const [inpaintRadius, setInpaintRadius] = useState(3);
  const [guideEdges, setGuideEdges] = useState(true);
  const [preserveTexture, setPreserveTexture] = useState(true);
  const [detectedRegions, setDetectedRegions] = useState([]);
  const [isDetecting, setIsDetecting] = useState(false);
  const [history, setHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  const imageCanvasRef = useRef(null);
  const maskCanvasRef = useRef(null);
  const lastPosRef = useRef(null);

  const MAX_HISTORY = 30;

  const pushHistory = useCallback((maskDataUrl) => {
    setHistory(prev => {
      const newHistory = prev.slice(0, historyIndex + 1);
      newHistory.push(maskDataUrl);
      if (newHistory.length > MAX_HISTORY) {
        newHistory.shift();
      }
      return newHistory;
    });
    setHistoryIndex(prev => Math.min(prev + 1, MAX_HISTORY - 1));
  }, [historyIndex]);

  const undo = useCallback(() => {
    if (historyIndex <= 0) return;
    const newIndex = historyIndex - 1;
    setHistoryIndex(newIndex);
    restoreMask(history[newIndex]);
  }, [historyIndex, history]);

  const redo = useCallback(() => {
    if (historyIndex >= history.length - 1) return;
    const newIndex = historyIndex + 1;
    setHistoryIndex(newIndex);
    restoreMask(history[newIndex]);
  }, [historyIndex, history]);

  const restoreMask = (dataUrl) => {
    const maskCanvas = maskCanvasRef.current;
    if (!maskCanvas || !dataUrl) return;
    const ctx = maskCanvas.getContext('2d');
    const img = new Image();
    img.onload = () => {
      ctx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
      ctx.drawImage(img, 0, 0);
    };
    img.src = dataUrl;
  };

  const drawImageOnCanvas = useCallback((img) => {
    const canvas = imageCanvasRef.current;
    const maskCanvas = maskCanvasRef.current;
    if (!canvas || !maskCanvas) return;

    const maxWidth = 800;
    const maxHeight = 600;
    let width = img.width;
    let height = img.height;

    if (width > maxWidth) {
      height = (maxWidth / width) * height;
      width = maxWidth;
    }
    if (height > maxHeight) {
      width = (maxHeight / height) * width;
      height = maxHeight;
    }

    canvas.width = width;
    canvas.height = height;
    maskCanvas.width = width;
    maskCanvas.height = height;

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, width, height);
    ctx.drawImage(img, 0, 0, width, height);

    const maskCtx = maskCanvas.getContext('2d');
    maskCtx.clearRect(0, 0, width, height);
    maskCtx.fillStyle = 'black';
    maskCtx.fillRect(0, 0, width, height);

    setProcessedImage(null);
    setDetectedRegions([]);
    setHistory([]);
    setHistoryIndex(-1);

    const initialMask = maskCanvas.toDataURL('image/png');
    setHistory([initialMask]);
    setHistoryIndex(0);
  }, []);

  const handleImageUpload = useCallback((file) => {
    if (!file || !file.type.startsWith('image/')) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        setImage(img);
        drawImageOnCanvas(img);
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  }, [drawImageOnCanvas]);

  const handleFileInput = (e) => {
    handleImageUpload(e.target.files[0]);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    handleImageUpload(e.dataTransfer.files[0]);
  };

  const getCanvasPosition = (e) => {
    const canvas = maskCanvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    if (e.touches) {
      return {
        x: (e.touches[0].clientX - rect.left) * scaleX,
        y: (e.touches[0].clientY - rect.top) * scaleY
      };
    }
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY
    };
  };

  const startDrawing = (e) => {
    if (!image) return;
    e.preventDefault();
    setIsDrawing(true);
    lastPosRef.current = getCanvasPosition(e);
  };

  const draw = (e) => {
    if (!isDrawing || !image) return;
    e.preventDefault();

    const pos = getCanvasPosition(e);
    const lastPos = lastPosRef.current;

    const maskCtx = maskCanvasRef.current.getContext('2d');
    maskCtx.lineWidth = brushSize;
    maskCtx.lineCap = 'round';
    maskCtx.lineJoin = 'round';
    maskCtx.strokeStyle = 'white';

    maskCtx.beginPath();
    maskCtx.moveTo(lastPos.x, lastPos.y);
    maskCtx.lineTo(pos.x, pos.y);
    maskCtx.stroke();

    lastPosRef.current = pos;
  };

  const stopDrawing = () => {
    if (isDrawing) {
      setIsDrawing(false);
      lastPosRef.current = null;
      const maskDataUrl = maskCanvasRef.current.toDataURL('image/png');
      pushHistory(maskDataUrl);
    }
  };

  const clearMask = () => {
    const maskCanvas = maskCanvasRef.current;
    if (!maskCanvas) return;
    const maskCtx = maskCanvas.getContext('2d');
    maskCtx.fillStyle = 'black';
    maskCtx.fillRect(0, 0, maskCanvas.width, maskCanvas.height);
    setProcessedImage(null);
    setDetectedRegions([]);
    const maskDataUrl = maskCanvas.toDataURL('image/png');
    pushHistory(maskDataUrl);
  };

  const detectText = async () => {
    if (!image || isDetecting) return;

    setIsDetecting(true);
    try {
      const imageDataUrl = imageCanvasRef.current.toDataURL('image/png');
      const response = await axios.post('/api/detect-text', {
        image: imageDataUrl,
        options: {
          padding: 5,
          minConfidence: 0.15
        }
      });

      if (response.data.success && response.data.mask) {
        const maskCanvas = maskCanvasRef.current;
        const ctx = maskCanvas.getContext('2d');
        const maskImg = new Image();
        maskImg.onload = () => {
          ctx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
          ctx.drawImage(maskImg, 0, 0);
          const maskDataUrl = maskCanvas.toDataURL('image/png');
          pushHistory(maskDataUrl);
        };
        maskImg.src = response.data.mask;

        setDetectedRegions(response.data.regions);
      }
    } catch (error) {
      console.error('文字检测出错:', error);
      alert('文字检测出错，请重试');
    } finally {
      setIsDetecting(false);
    }
  };

  const autoDetectAndInpaint = async () => {
    if (!image || isProcessing) return;

    setIsProcessing(true);
    try {
      const imageDataUrl = imageCanvasRef.current.toDataURL('image/png');
      const response = await axios.post('/api/detect-and-inpaint', {
        image: imageDataUrl,
        algorithm,
        radius: inpaintRadius,
        options: { guideEdges, preserveTexture },
        detectOptions: { padding: 5, minConfidence: 0.15 }
      });

      if (response.data.success) {
        setProcessedImage(response.data.result);
        setDetectedRegions(response.data.regions || []);
      }
    } catch (error) {
      console.error('自动检测修复出错:', error);
      alert('处理图片时出错，请重试');
    } finally {
      setIsProcessing(false);
    }
  };

  const processImage = async () => {
    if (!image || isProcessing) return;

    setIsProcessing(true);
    try {
      const imageDataUrl = imageCanvasRef.current.toDataURL('image/png');
      const maskDataUrl = maskCanvasRef.current.toDataURL('image/png');

      const response = await axios.post('/api/inpaint', {
        image: imageDataUrl,
        mask: maskDataUrl,
        algorithm,
        radius: inpaintRadius,
        options: { guideEdges, preserveTexture }
      });

      setProcessedImage(response.data.result);
    } catch (error) {
      console.error('处理图片时出错:', error);
      alert('处理图片时出错，请重试');
    } finally {
      setIsProcessing(false);
    }
  };

  const downloadImage = () => {
    if (!processedImage) return;
    const link = document.createElement('a');
    link.download = 'processed-image.png';
    link.href = processedImage;
    link.click();
  };

  const resetAll = () => {
    setImage(null);
    setProcessedImage(null);
    setDetectedRegions([]);
    setHistory([]);
    setHistoryIndex(-1);
  };

  const canUndo = historyIndex > 0;
  const canRedo = historyIndex < history.length - 1;

  return (
    <div className="image-editor">
      <div className="editor-container">
        <div className="upload-section">
          {!image ? (
            <div
              className={`drop-zone ${isDragging ? 'dragging' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => document.getElementById('file-input').click()}
            >
              <input
                id="file-input"
                type="file"
                accept="image/*"
                onChange={handleFileInput}
                style={{ display: 'none' }}
              />
              <div className="drop-content">
                <div className="upload-icon">📁</div>
                <p>点击或拖拽图片到此处上传</p>
                <p className="hint">支持 JPG、PNG、WebP 格式</p>
              </div>
            </div>
          ) : (
            <div className="canvas-wrapper">
              <div className="canvas-container">
                <canvas ref={imageCanvasRef} className="image-canvas" />
                <canvas
                  ref={maskCanvasRef}
                  className="mask-canvas"
                  onMouseDown={startDrawing}
                  onMouseMove={draw}
                  onMouseUp={stopDrawing}
                  onMouseLeave={stopDrawing}
                  onTouchStart={startDrawing}
                  onTouchMove={draw}
                  onTouchEnd={stopDrawing}
                />
                {detectedRegions.length > 0 && (
                  <div className="detection-overlay">
                    {detectedRegions.map((region, idx) => (
                      <div
                        key={idx}
                        className="detection-box"
                        style={{
                          left: `${(region.bbox.x / (imageCanvasRef.current?.width || 1)) * 100}%`,
                          top: `${(region.bbox.y / (imageCanvasRef.current?.height || 1)) * 100}%`,
                          width: `${(region.bbox.width / (imageCanvasRef.current?.width || 1)) * 100}%`,
                          height: `${(region.bbox.height / (imageCanvasRef.current?.height || 1)) * 100}%`
                        }}
                      >
                        <span className="confidence-label">
                          {(region.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {processedImage && (
                <div className="result-container">
                  <h3>处理结果</h3>
                  <img src={processedImage} alt="Processed" className="result-image" />
                </div>
              )}
            </div>
          )}
        </div>

        <div className="tools-section">
          <div className="tool-group">
            <h3>🔍 文字检测</h3>
            <div className="button-group horizontal">
              <button
                className="btn btn-detect"
                onClick={detectText}
                disabled={!image || isDetecting}
              >
                {isDetecting ? '检测中...' : '🔍 检测文字'}
              </button>
              <button
                className="btn btn-auto"
                onClick={autoDetectAndInpaint}
                disabled={!image || isProcessing}
              >
                {isProcessing ? '处理中...' : '⚡ 一键擦除'}
              </button>
            </div>
            {detectedRegions.length > 0 && (
              <p className="detection-info">
                检测到 {detectedRegions.length} 个文字区域
              </p>
            )}
          </div>

          <div className="tool-group">
            <h3>🎨 画笔工具</h3>
            <div className="tool-item">
              <label>画笔大小: {brushSize}px</label>
              <input
                type="range"
                min="5"
                max="100"
                value={brushSize}
                onChange={(e) => setBrushSize(Number(e.target.value))}
                disabled={!image}
              />
            </div>
            <div className="brush-preview">
              <div className="brush-circle" style={{ width: brushSize, height: brushSize }} />
            </div>
          </div>

          <div className="tool-group">
            <h3>⏪ 历史记录</h3>
            <div className="button-group horizontal">
              <button
                className="btn btn-secondary btn-small"
                onClick={undo}
                disabled={!canUndo}
              >
                ↩ 撤销
              </button>
              <button
                className="btn btn-secondary btn-small"
                onClick={redo}
                disabled={!canRedo}
              >
                ↪ 重做
              </button>
              <span className="history-info">
                {historyIndex + 1}/{history.length}
              </span>
            </div>
          </div>

          <div className="tool-group">
            <h3>⚙️ 修复算法</h3>
            <div className="tool-item">
              <label>选择算法:</label>
              <select
                value={algorithm}
                onChange={(e) => setAlgorithm(e.target.value)}
                disabled={!image}
              >
                <option value="telea">Telea 算法 (快速)</option>
                <option value="edge-guided">边缘引导修复 (推荐)</option>
                <option value="texture-preserving">纹理保持修复</option>
                <option value="ns">Navier-Stokes (高质量)</option>
                <option value="hybrid">混合算法</option>
                <option value="advanced">高级修复 (最佳质量)</option>
              </select>
            </div>
            <div className="tool-item">
              <label>修复半径: {inpaintRadius}px</label>
              <input
                type="range"
                min="1"
                max="10"
                value={inpaintRadius}
                onChange={(e) => setInpaintRadius(Number(e.target.value))}
                disabled={!image}
              />
            </div>
            <div className="tool-item checkbox-item">
              <label>
                <input
                  type="checkbox"
                  checked={guideEdges}
                  onChange={(e) => setGuideEdges(e.target.checked)}
                  disabled={!image}
                />
                边缘引导
              </label>
            </div>
            <div className="tool-item checkbox-item">
              <label>
                <input
                  type="checkbox"
                  checked={preserveTexture}
                  onChange={(e) => setPreserveTexture(e.target.checked)}
                  disabled={!image}
                />
                纹理保持
              </label>
            </div>
          </div>

          <div className="tool-group">
            <h3>📋 操作</h3>
            <div className="button-group">
              <button
                className="btn btn-primary"
                onClick={processImage}
                disabled={!image || isProcessing}
              >
                {isProcessing ? '处理中...' : '✨ 开始擦除'}
              </button>
              <button className="btn btn-secondary" onClick={clearMask} disabled={!image}>
                🧹 清除涂抹
              </button>
              {processedImage && (
                <button className="btn btn-success" onClick={downloadImage}>
                  💾 下载结果
                </button>
              )}
              <button className="btn btn-danger" onClick={resetAll}>
                🔄 重新上传
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ImageEditor;
