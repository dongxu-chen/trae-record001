import React, { useState } from 'react';
import axios from 'axios';
import './BatchProcessor.css';

function BatchProcessor() {
  const [files, setFiles] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isClassifying, setIsClassifying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [classification, setClassification] = useState(null);
  const [useAutoParams, setUseAutoParams] = useState(true);
  const [groupOverrides, setGroupOverrides] = useState({
    simple: { algorithm: 'telea', radius: 2, preserveTexture: false, guideEdges: false },
    medium: { algorithm: 'edge-guided', radius: 3, preserveTexture: true, guideEdges: true },
    complex: { algorithm: 'texture-preserving', radius: 4, preserveTexture: true, guideEdges: true },
    'very-complex': { algorithm: 'advanced', radius: 5, preserveTexture: true, guideEdges: true }
  });

  const complexityColors = {
    simple: '#28a745',
    medium: '#ffc107',
    complex: '#fd7e14',
    'very-complex': '#dc3545'
  };

  const complexityNames = {
    simple: '简单背景',
    medium: '中等复杂度',
    complex: '复杂背景',
    'very-complex': '非常复杂'
  };

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    const imageFiles = selectedFiles.filter(f => f.type.startsWith('image/'));
    addFiles(imageFiles);
  };

  const addFiles = (newFiles) => {
    const filesWithPreview = newFiles.map(file => ({
      file,
      id: Date.now() + Math.random(),
      name: file.name,
      preview: URL.createObjectURL(file),
      status: 'pending',
      classification: null,
      result: null
    }));
    setFiles(prev => [...prev, ...filesWithPreview]);
    setClassification(null);
    setResults([]);
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
    const droppedFiles = Array.from(e.dataTransfer.files);
    const imageFiles = droppedFiles.filter(f => f.type.startsWith('image/'));
    addFiles(imageFiles);
  };

  const removeFile = (id) => {
    setFiles(prev => prev.filter(f => f.id !== id));
    setResults(prev => prev.filter(r => r.id !== id));
    if (classification) {
      setClassification(null);
    }
  };

  const clearAll = () => {
    files.forEach(f => URL.revokeObjectURL(f.preview));
    setFiles([]);
    setResults([]);
    setProgress(0);
    setClassification(null);
  };

  const fileToBase64 = (file) => {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.readAsDataURL(file);
    });
  };

  const classifyImages = async () => {
    if (files.length === 0 || isClassifying) return;

    setIsClassifying(true);
    setProgress(0);

    try {
      const imagesData = await Promise.all(
        files.map(async (f) => ({
          image: await fileToBase64(f.file),
          name: f.name
        }))
      );

      const response = await axios.post('/api/batch-classify', { images: imagesData });

      if (response.data.success) {
        setClassification(response.data.classification);
        
        const updatedFiles = files.map((f, idx) => {
          const classInfo = response.data.classification.images.find(c => c.name === f.name);
          return { ...f, classification: classInfo || null };
        });
        setFiles(updatedFiles);
      }
    } catch (error) {
      console.error('分类图片时出错:', error);
      alert('分类图片时出错，请重试');
    } finally {
      setIsClassifying(false);
      setProgress(100);
    }
  };

  const generateDefaultMask = (width, height) => {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = 'black';
    ctx.fillRect(0, 0, width, height);
    return canvas.toDataURL('image/png');
  };

  const processBatch = async () => {
    if (files.length === 0 || isProcessing) return;

    setIsProcessing(true);
    setProgress(0);
    setResults([]);

    try {
      const imagesData = await Promise.all(
        files.map(async (f) => {
          const imageBase64 = await fileToBase64(f.file);
          
          const img = new Image();
          img.src = imageBase64;
          await new Promise(resolve => { img.onload = resolve; });
          
          const maskBase64 = f.mask || generateDefaultMask(img.width, img.height);

          return {
            image: imageBase64,
            mask: maskBase64,
            name: f.name,
            classification: f.classification
          };
        })
      );

      const response = await axios.post('/api/batch-inpaint-grouped', {
        images: imagesData,
        groupOverrides,
        useAutoParams
      });

      if (response.data.success) {
        const processedResults = response.data.results.map((r, idx) => ({
          id: files[idx].id,
          name: r.name,
          original: imagesData[idx].image,
          result: r.result,
          status: r.success ? 'success' : 'error',
          error: r.error,
          complexityLevel: r.complexityLevel,
          algorithm: r.algorithm,
          radius: r.radius
        }));
        setResults(processedResults);
      }
    } catch (error) {
      console.error('批量处理时出错:', error);
      alert('批量处理时出错，请重试');
    } finally {
      setIsProcessing(false);
      setProgress(100);
    }
  };

  const downloadAll = () => {
    results.forEach((result, index) => {
      if (result.status === 'success') {
        setTimeout(() => {
          const link = document.createElement('a');
          link.download = `processed_${result.name}`;
          link.href = result.result;
          link.click();
        }, index * 500);
      }
    });
  };

  const downloadResult = (result) => {
    const link = document.createElement('a');
    link.download = `processed_${result.name}`;
    link.href = result.result;
    link.click();
  };

  const updateGroupParam = (group, param, value) => {
    setGroupOverrides(prev => ({
      ...prev,
      [group]: {
        ...prev[group],
        [param]: value
      }
    }));
  };

  return (
    <div className="batch-processor">
      <div className="batch-container">
        <div className="upload-section">
          <div
            className={`drop-zone ${isDragging ? 'dragging' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => document.getElementById('batch-file-input').click()}
          >
            <input
              id="batch-file-input"
              type="file"
              accept="image/*"
              multiple
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
            <div className="drop-content">
              <div className="upload-icon">📦</div>
              <p>点击或拖拽多张图片到此处</p>
              <p className="hint">支持批量选择，自动分类处理</p>
            </div>
          </div>

          {files.length > 0 && (
            <div className="files-list">
              <div className="files-header">
                <h3>待处理图片 ({files.length})</h3>
                <div className="header-actions">
                  {!classification && (
                    <button
                      className="btn-classify"
                      onClick={classifyImages}
                      disabled={isClassifying}
                    >
                      {isClassifying ? '分类中...' : '🔍 智能分类'}
                    </button>
                  )}
                  <button className="btn-clear" onClick={clearAll}>
                    清空全部
                  </button>
                </div>
              </div>

              {classification && (
                <div className="classification-summary">
                  <h4>📊 分类结果</h4>
                  <div className="group-summary">
                    {Object.entries(classification.groups).map(([level, group]) => (
                      <div
                        key={level}
                        className="group-badge"
                        style={{ backgroundColor: complexityColors[level] }}
                      >
                        {complexityNames[level]}: {group.length}张
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="files-grid">
                {files.map(file => (
                  <div key={file.id} className="file-item">
                    <img src={file.preview} alt={file.name} className="file-thumb" />
                    <div className="file-info">
                      <span className="file-name">{file.name}</span>
                      {file.classification && (
                        <span
                          className="complexity-badge"
                          style={{ backgroundColor: complexityColors[file.classification.level] }}
                        >
                          {complexityNames[file.classification.level]}
                        </span>
                      )}
                    </div>
                    <button
                      className="btn-remove"
                      onClick={() => removeFile(file.id)}
                      title="移除"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="settings-section">
          {classification && (
            <div className="settings-group grouped-params">
              <h3>⚙️ 分组参数配置</h3>
              
              <div className="auto-param-toggle">
                <label>
                  <input
                    type="checkbox"
                    checked={useAutoParams}
                    onChange={(e) => setUseAutoParams(e.target.checked)}
                  />
                  使用智能分组参数
                </label>
              </div>

              {Object.entries(groupOverrides).map(([level, params]) => (
                <div key={level} className="group-param-section">
                  <div
                    className="group-header"
                    style={{ borderLeftColor: complexityColors[level] }}
                  >
                    <span className="group-title">{complexityNames[level]}</span>
                    <span className="group-count">
                      ({classification.groups[level]?.length || 0}张)
                    </span>
                  </div>
                  
                  <div className="param-grid">
                    <div className="param-item">
                      <label>修复算法:</label>
                      <select
                        value={params.algorithm}
                        onChange={(e) => updateGroupParam(level, 'algorithm', e.target.value)}
                        disabled={useAutoParams}
                      >
                        <option value="telea">Telea (快速)</option>
                        <option value="edge-guided">边缘引导</option>
                        <option value="texture-preserving">纹理保持</option>
                        <option value="ns">Navier-Stokes</option>
                        <option value="hybrid">混合算法</option>
                        <option value="advanced">高级修复</option>
                      </select>
                    </div>

                    <div className="param-item">
                      <label>修复半径: {params.radius}</label>
                      <input
                        type="range"
                        min="1"
                        max="10"
                        value={params.radius}
                        onChange={(e) => updateGroupParam(level, 'radius', Number(e.target.value))}
                        disabled={useAutoParams}
                      />
                    </div>

                    <div className="param-item checkbox-item">
                      <label>
                        <input
                          type="checkbox"
                          checked={params.guideEdges}
                          onChange={(e) => updateGroupParam(level, 'guideEdges', e.target.checked)}
                          disabled={useAutoParams}
                        />
                        边缘引导
                      </label>
                    </div>

                    <div className="param-item checkbox-item">
                      <label>
                        <input
                          type="checkbox"
                          checked={params.preserveTexture}
                          onChange={(e) => updateGroupParam(level, 'preserveTexture', e.target.checked)}
                          disabled={useAutoParams}
                        />
                        纹理保持
                      </label>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {!classification && files.length > 0 && (
            <div className="settings-group">
              <h3>💡 提示</h3>
              <p>先点击「智能分类」按钮，系统将自动分析图片复杂度并分组，然后可以针对不同复杂度的图片配置独立的修复参数。</p>
            </div>
          )}

          <div className="action-buttons">
            {classification && (
              <button
                className="btn btn-primary btn-large"
                onClick={processBatch}
                disabled={isProcessing}
              >
                {isProcessing ? `处理中 ${progress}%...` : '🚀 开始分组处理'}
              </button>
            )}

            {results.length > 0 && (
              <button
                className="btn btn-success btn-large"
                onClick={downloadAll}
              >
                📥 下载全部结果
              </button>
            )}
          </div>

          {isProcessing && (
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progress}%` }} />
              <span className="progress-text">{progress}%</span>
            </div>
          )}
        </div>
      </div>

      {results.length > 0 && (
        <div className="results-section">
          <h3>📊 处理结果 ({results.filter(r => r.status === 'success').length}/{results.length})</h3>
          <div className="results-grid">
            {results.map(result => (
              <div key={result.id} className={`result-card ${result.status}`}>
                {result.status === 'success' ? (
                  <>
                    <div className="result-images">
                      <div className="result-image-wrapper">
                        <span className="image-label">原图</span>
                        <img src={result.original} alt="Original" />
                      </div>
                      <div className="result-image-wrapper">
                        <span className="image-label">处理后</span>
                        <img src={result.result} alt="Processed" />
                      </div>
                    </div>
                    <div className="result-meta">
                      <span
                        className="result-complexity"
                        style={{ backgroundColor: complexityColors[result.complexityLevel] }}
                      >
                        {complexityNames[result.complexityLevel]}
                      </span>
                      <span className="result-algo">{result.algorithm}</span>
                    </div>
                    <div className="result-actions">
                      <span className="result-name">{result.name}</span>
                      <button
                        className="btn-download-small"
                        onClick={() => downloadResult(result)}
                      >
                        下载
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="error-message">
                    ❌ {result.name} 处理失败
                    <p>{result.error}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default BatchProcessor;
