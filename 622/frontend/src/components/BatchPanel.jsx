import React, { useState, useEffect } from 'react';
import { getStyles, uploadImage, batchTransfer, batchTransferMixed } from '../services/api';

const BatchPanel = () => {
  const [styles, setStyles] = useState([]);
  const [selectedStyles, setSelectedStyles] = useState([]);
  const [uploadedImages, setUploadedImages] = useState([]);
  const [intensity, setIntensity] = useState(0.7);
  const [mode, setMode] = useState('single');
  const [styleWeights, setStyleWeights] = useState({});
  const [styleCombinations, setStyleCombinations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadStyles();
  }, []);

  const loadStyles = async () => {
    try {
      const response = await getStyles();
      setStyles(response.data.styles);
      const weights = {};
      response.data.styles.forEach(s => {
        weights[s.id] = 0.5;
      });
      setStyleWeights(weights);
    } catch (error) {
      console.error('Failed to load styles:', error);
    }
  };

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    setUploading(true);
    const newImages = [];

    for (const file of files) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        const response = await uploadImage(formData);
        newImages.push({
          id: response.data.id,
          name: file.name,
          url: `http://localhost:8000${response.data.processed_url}`
        });
      } catch (error) {
        console.error(`Failed to upload ${file.name}:`, error);
      }
    }

    setUploadedImages(prev => [...prev, ...newImages]);
    setUploading(false);
    e.target.value = '';
  };

  const removeImage = (id) => {
    setUploadedImages(prev => prev.filter(img => img.id !== id));
  };

  const toggleStyle = (styleId) => {
    setSelectedStyles(prev => {
      if (prev.includes(styleId)) {
        return prev.filter(s => s !== styleId);
      } else {
        return [...prev, styleId];
      }
    });
  };

  const addCombination = () => {
    if (selectedStyles.length === 0) return;
    const weights = {};
    selectedStyles.forEach(s => {
      weights[s] = styleWeights[s] || 0.5;
    });
    setStyleCombinations(prev => [...prev, {
      id: Date.now(),
      name: `组合 ${prev.length + 1}`,
      weights
    }]);
  };

  const removeCombination = (id) => {
    setStyleCombinations(prev => prev.filter(c => c.id !== id));
  };

  const handleBatchProcess = async () => {
    if (uploadedImages.length === 0) {
      alert('请先上传图片');
      return;
    }

    if (mode === 'single' && selectedStyles.length === 0) {
      alert('请选择至少一个风格');
      return;
    }

    if (mode === 'mixed' && styleCombinations.length === 0) {
      alert('请先添加至少一个风格组合');
      return;
    }

    setLoading(true);
    setResults([]);

    try {
      const contentIds = uploadedImages.map(img => img.id);
      let response;

      if (mode === 'single') {
        response = await batchTransfer({
          content_ids: contentIds,
          style_ids: selectedStyles,
          intensity: intensity,
          model_type: 'sd_turbo'
        });
      } else {
        response = await batchTransferMixed({
          content_ids: contentIds,
          style_combinations: styleCombinations.map(c => c.weights),
          intensity: intensity,
          model_type: 'sd_turbo'
        });
      }

      const processedResults = response.data.results.map((r, idx) => {
        const srcImg = uploadedImages[Math.floor(idx / (mode === 'single' ? selectedStyles.length : styleCombinations.length))];
        return {
          ...r,
          source_name: srcImg?.name,
          source_url: srcImg?.url
        };
      });

      setResults(processedResults);
    } catch (error) {
      console.error('Batch processing failed:', error);
      alert('批量处理失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const downloadImage = async (url, filename) => {
    try {
      const response = await fetch(`http://localhost:8000${url}`);
      const blob = await response.blob();
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  const downloadAll = () => {
    results.filter(r => r.success).forEach((r, idx) => {
      setTimeout(() => {
        downloadImage(r.output_url, `batch_result_${idx + 1}.jpg`);
      }, idx * 200);
    });
  };

  const estimatedCount = uploadedImages.length * (
    mode === 'single' ? selectedStyles.length : styleCombinations.length
  );

  const estimatedTime = (estimatedCount * 0.4).toFixed(1);

  return (
    <div className="bg-white rounded-xl shadow-lg p-5">
      <h3 className="text-lg font-bold text-gray-800 mb-4">📦 批量生成</h3>

      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setMode('single')}
          className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all
            ${mode === 'single'
              ? 'bg-blue-500 text-white shadow-md'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
        >
          🎨 多风格批量
        </button>
        <button
          onClick={() => setMode('mixed')}
          className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all
            ${mode === 'mixed'
              ? 'bg-purple-500 text-white shadow-md'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
        >
          🔮 风格组合批量
        </button>
      </div>

      <div className="mb-4">
        <p className="text-xs font-medium text-gray-600 mb-2">
          📷 上传图片 ({uploadedImages.length}张)
        </p>
        <label className="block">
          <div className="flex items-center justify-center w-full h-24 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-all">
            {uploading ? (
              <div className="text-center">
                <div className="animate-spin text-2xl mb-1">⏳</div>
                <p className="text-xs text-gray-500">上传中...</p>
              </div>
            ) : (
              <div className="text-center">
                <p className="text-2xl mb-1">+</p>
                <p className="text-xs text-gray-500">点击或拖拽上传多张图片</p>
              </div>
            )}
          </div>
          <input
            type="file"
            multiple
            accept="image/*"
            onChange={handleFileUpload}
            className="hidden"
            disabled={uploading}
          />
        </label>

        {uploadedImages.length > 0 && (
          <div className="mt-3 grid grid-cols-4 gap-2 max-h-32 overflow-y-auto">
            {uploadedImages.map(img => (
              <div key={img.id} className="relative group">
                <img
                  src={img.url}
                  alt={img.name}
                  className="w-full h-16 object-cover rounded"
                />
                <button
                  onClick={() => removeImage(img.id)}
                  className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-xs rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  ×
                </button>
                <p className="text-[10px] text-gray-500 truncate mt-0.5">{img.name}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {mode === 'single' && (
        <div className="mb-4">
          <p className="text-xs font-medium text-gray-600 mb-2">
            选择风格 ({selectedStyles.length}个)
          </p>
          <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto">
            {styles.map(style => (
              <div
                key={style.id}
                onClick={() => toggleStyle(style.id)}
                className={`p-2 rounded-lg border-2 cursor-pointer text-xs transition-all
                  ${selectedStyles.includes(style.id)
                    ? 'border-blue-400 bg-blue-50 text-blue-700 font-medium'
                    : 'border-gray-200 hover:border-gray-300 text-gray-700'
                  }`}
              >
                <div className="flex items-center gap-1.5">
                  <span>{selectedStyles.includes(style.id) ? '✓' : '○'}</span>
                  <span>{style.name}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {mode === 'mixed' && (
        <div className="mb-4">
          <p className="text-xs font-medium text-gray-600 mb-2">
            创建风格组合 ({styleCombinations.length}个)
          </p>

          <div className="mb-3 p-3 bg-gray-50 rounded-lg">
            <p className="text-[11px] text-gray-500 mb-2">1. 选择风格并调整权重</p>
            <div className="space-y-2 max-h-32 overflow-y-auto mb-2">
              {styles.map(style => (
                <div key={style.id} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={selectedStyles.includes(style.id)}
                    onChange={() => toggleStyle(style.id)}
                    className="w-3.5 h-3.5 accent-blue-500"
                  />
                  <span className="text-xs w-16 truncate">{style.name}</span>
                  {selectedStyles.includes(style.id) && (
                    <>
                      <input
                        type="range"
                        min="0.1"
                        max="1"
                        step="0.1"
                        value={styleWeights[style.id] || 0.5}
                        onChange={(e) => setStyleWeights(prev => ({
                          ...prev,
                          [style.id]: parseFloat(e.target.value)
                        }))}
                        className="flex-1 h-1.5 accent-purple-500"
                      />
                      <span className="text-xs text-gray-500 w-8">
                        {((styleWeights[style.id] || 0.5) * 100).toFixed(0)}%
                      </span>
                    </>
                  )}
                </div>
              ))}
            </div>
            <button
              onClick={addCombination}
              disabled={selectedStyles.length === 0}
              className={`w-full py-1.5 text-xs rounded-lg transition-all
                ${selectedStyles.length > 0
                  ? 'bg-purple-500 text-white hover:bg-purple-600'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                }`}
            >
              + 添加此组合
            </button>
          </div>

          {styleCombinations.length > 0 && (
            <div className="space-y-2">
              <p className="text-[11px] text-gray-500">2. 已添加的组合</p>
              {styleCombinations.map(comb => (
                <div key={comb.id} className="flex items-center justify-between p-2 bg-purple-50 rounded-lg border border-purple-200">
                  <div>
                    <p className="text-xs font-medium text-purple-700">{comb.name}</p>
                    <p className="text-[10px] text-purple-500">
                      {Object.entries(comb.weights).map(([k, v]) =>
                        `${styles.find(s => s.id === k)?.name || k} ${(v * 100).toFixed(0)}%`
                      ).join(' + ')}
                    </p>
                  </div>
                  <button
                    onClick={() => removeCombination(comb.id)}
                    className="text-red-400 hover:text-red-600 text-lg px-1"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="mb-4">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium text-gray-600">强度</span>
          <span className="text-xs text-gray-500">{(intensity * 100).toFixed(0)}%</span>
        </div>
        <input
          type="range"
          min="0.1"
          max="1"
          step="0.05"
          value={intensity}
          onChange={(e) => setIntensity(parseFloat(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
        />
      </div>

      {uploadedImages.length > 0 && (mode === 'single' ? selectedStyles.length > 0 : styleCombinations.length > 0) && (
        <div className="mb-4 p-3 bg-amber-50 rounded-lg border border-amber-200">
          <p className="text-xs text-amber-700">
            📊 预计生成 <strong>{estimatedCount}</strong> 张图片，约 <strong>{estimatedTime}秒</strong>
          </p>
        </div>
      )}

      <button
        onClick={handleBatchProcess}
        disabled={loading || uploadedImages.length === 0 || (mode === 'single' ? selectedStyles.length === 0 : styleCombinations.length === 0)}
        className={`w-full py-3 rounded-lg font-semibold text-white transition-all
          ${loading || uploadedImages.length === 0 || (mode === 'single' ? selectedStyles.length === 0 : styleCombinations.length === 0)
            ? 'bg-gray-300 cursor-not-allowed'
            : 'bg-gradient-to-r from-green-500 to-teal-500 hover:shadow-lg hover:scale-[1.02]'
          }`}
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <span className="animate-spin">⏳</span> 批量处理中...
          </span>
        ) : (
          <>🚀 开始批量生成</>
        )}
      </button>

      {results.length > 0 && (
        <div className="mt-5">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-semibold text-gray-800">
              处理结果 ({results.filter(r => r.success).length}/{results.length})
            </h4>
            <button
              onClick={downloadAll}
              className="px-3 py-1 bg-green-500 text-white text-xs rounded-lg hover:bg-green-600 transition-all"
            >
              ⬇️ 全部下载
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3 max-h-96 overflow-y-auto">
            {results.map((result, idx) => (
              <div key={idx} className={`rounded-lg overflow-hidden border-2 ${result.success ? 'border-green-200' : 'border-red-200'}`}>
                {result.success ? (
                  <>
                    <img
                      src={`http://localhost:8000${result.output_url}`}
                      alt={`Result ${idx + 1}`}
                      className="w-full h-32 object-cover"
                    />
                    <div className="p-2 bg-gray-50">
                      <p className="text-[10px] text-gray-600 truncate mb-1">
                        原图: {result.source_name}
                      </p>
                      <p className="text-[10px] text-gray-500 mb-1">
                        {result.style_id
                          ? `风格: ${styles.find(s => s.id === result.style_id)?.name || result.style_id}`
                          : `组合: ${result.style_combination !== undefined ? result.style_combination + 1 : 'N/A'}`
                        }
                      </p>
                      <button
                        onClick={() => downloadImage(result.output_url, `result_${idx + 1}.jpg`)}
                        className="w-full py-1 bg-blue-500 text-white text-[10px] rounded hover:bg-blue-600"
                      >
                        下载
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="h-32 flex items-center justify-center bg-red-50">
                    <div className="text-center p-2">
                      <p className="text-red-500 text-lg">❌</p>
                      <p className="text-[10px] text-red-500 mt-1">处理失败</p>
                      <p className="text-[9px] text-red-400 mt-0.5 truncate">{result.error}</p>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default BatchPanel;
