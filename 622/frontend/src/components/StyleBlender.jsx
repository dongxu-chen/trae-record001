import React, { useState, useEffect } from 'react';
import { getStyles, getExtendedStyles, transferMixed, trainModel, getPersonalizedModels } from '../services/api';

const STYLE_PRESETS_INFO = {
  vangogh: { name: '梵高', color: '#FFB347' },
  picasso: { name: '毕加索', color: '#87CEEB' },
  monet: { name: '莫奈', color: '#98FB98' },
  kanagawa: { name: '神奈川', color: '#DDA0DD' },
  cyberpunk: { name: '赛博朋克', color: '#FF69B4' },
  watercolor: { name: '水彩', color: '#40E0D0' },
  oil_painting: { name: '油画', color: '#CD853F' },
  sketch: { name: '素描', color: '#A9A9A9' }
};

const StyleBlender = ({ contentId, onResult, feedbackCount = 0 }) => {
  const [styles, setStyles] = useState([]);
  const [personalizedModels, setPersonalizedModels] = useState([]);
  const [styleWeights, setStyleWeights] = useState({});
  const [selectedStyles, setSelectedStyles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [intensity, setIntensity] = useState(0.7);
  const [showTrainPanel, setShowTrainPanel] = useState(false);
  const [modelName, setModelName] = useState('');
  const [training, setTraining] = useState(false);

  useEffect(() => {
    loadStyles();
    loadPersonalizedModels();
  }, []);

  const loadStyles = async () => {
    try {
      const response = await getStyles();
      setStyles(response.data.styles);
      const initialWeights = {};
      response.data.styles.forEach(s => {
        initialWeights[s.id] = 0.33;
      });
      setStyleWeights(initialWeights);
    } catch (error) {
      console.error('Failed to load styles:', error);
    }
  };

  const loadPersonalizedModels = async () => {
    try {
      const response = await getPersonalizedModels('default');
      setPersonalizedModels(response.data.models);
    } catch (error) {
      console.error('Failed to load personalized models:', error);
    }
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

  const handleWeightChange = (styleId, weight) => {
    setStyleWeights(prev => ({
      ...prev,
      [styleId]: parseFloat(weight)
    }));
  };

  const getActiveWeights = () => {
    const weights = {};
    selectedStyles.forEach(styleId => {
      weights[styleId] = styleWeights[styleId] || 0.5;
    });
    return weights;
  };

  const handleBlend = async () => {
    if (!contentId || selectedStyles.length === 0) return;
    
    setLoading(true);
    setResult(null);
    
    try {
      const weights = getActiveWeights();
      const response = await transferMixed({
        content_id: contentId,
        style_weights: weights,
        intensity: intensity,
        model_type: 'sd_turbo',
        preview: false
      });
      
      setResult(response.data);
      if (onResult) onResult(response.data);
    } catch (error) {
      console.error('Failed to blend styles:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTrainModel = async () => {
    if (!modelName.trim() || feedbackCount < 3) return;
    
    setTraining(true);
    try {
      const response = await trainModel({
        user_id: 'default',
        name: modelName.trim(),
        base_styles: getActiveWeights()
      });
      
      setShowTrainPanel(false);
      setModelName('');
      loadPersonalizedModels();
      
      setTimeout(() => {
        alert(`个性化模型训练成功！\n模型名称：${response.data.model.name}\n可在风格列表中选择使用。`);
      }, 100);
    } catch (error) {
      alert(error.response?.data?.error || '训练失败，请稍后重试');
    } finally {
      setTraining(false);
    }
  };

  const presetCombinations = [
    { name: '印象派混合', styles: { vangogh: 0.5, monet: 0.5 } },
    { name: '现代艺术', styles: { cyberpunk: 0.4, picasso: 0.3, oil_painting: 0.3 } },
    { name: '东方韵味', styles: { kanagawa: 0.6, watercolor: 0.4 } },
    { name: '柔和笔触', styles: { watercolor: 0.5, monet: 0.3, sketch: 0.2 } }
  ];

  const applyPreset = (preset) => {
    setSelectedStyles(Object.keys(preset.styles));
    setStyleWeights(prev => ({
      ...prev,
      ...preset.styles
    }));
  };

  const totalWeight = selectedStyles.reduce((sum, s) => sum + (styleWeights[s] || 0), 0);

  return (
    <div className="bg-white rounded-xl shadow-lg p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-gray-800">🎨 风格融合</h3>
        <button
          onClick={() => setShowTrainPanel(!showTrainPanel)}
          disabled={feedbackCount < 3}
          className={`px-3 py-1 text-sm rounded-lg transition-all
            ${feedbackCount >= 3
              ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:shadow-md'
              : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
        >
          ✨ 训练模型 {feedbackCount >= 3 ? `(${feedbackCount}/3)` : `(${feedbackCount}/3)`}
        </button>
      </div>

      {showTrainPanel && (
        <div className="mb-5 p-4 bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg border border-purple-200">
          <h4 className="font-semibold text-purple-800 mb-3">训练个性化风格模型</h4>
          <p className="text-sm text-gray-600 mb-3">
            系统将根据您的评分历史学习您的偏好，生成专属的风格模型。
          </p>
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              placeholder="为您的风格模型命名..."
              className="flex-1 px-3 py-2 border border-purple-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-400"
            />
            <button
              onClick={handleTrainModel}
              disabled={training || !modelName.trim()}
              className="px-4 py-2 bg-purple-600 text-white text-sm rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-all"
            >
              {training ? '训练中...' : '开始训练'}
            </button>
          </div>
          {selectedStyles.length > 0 && (
            <p className="text-xs text-gray-500">
              💡 已选择的风格权重将作为训练基础
            </p>
          )}
        </div>
      )}

      {personalizedModels.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-medium text-gray-600 mb-2">👤 我的个性化模型</p>
          <div className="flex flex-wrap gap-2">
            {personalizedModels.map(model => (
              <span
                key={model.id}
                className="px-2 py-1 bg-gradient-to-r from-purple-100 to-pink-100 text-purple-700 text-xs rounded-full border border-purple-200"
              >
                {model.name}
                <span className="ml-1 text-purple-400">({model.trained_on}条反馈)</span>
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="mb-4">
        <p className="text-xs font-medium text-gray-600 mb-2">⚡ 快速预设</p>
        <div className="flex flex-wrap gap-2">
          {presetCombinations.map((preset, idx) => (
            <button
              key={idx}
              onClick={() => applyPreset(preset)}
              className="px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-all"
            >
              {preset.name}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-4">
        <p className="text-xs font-medium text-gray-600 mb-2">
          选择风格并调整权重 ({selectedStyles.length}个已选)
        </p>
        <div className="space-y-2 max-h-64 overflow-y-auto pr-2">
          {styles.map(style => {
            const info = STYLE_PRESETS_INFO[style.id] || { name: style.name, color: '#888' };
            const isSelected = selectedStyles.includes(style.id);
            const weight = styleWeights[style.id] || 0.33;
            const normalizedWeight = totalWeight > 0 ? (weight / totalWeight * 100).toFixed(0) : 0;
            
            return (
              <div
                key={style.id}
                onClick={() => toggleStyle(style.id)}
                className={`p-3 rounded-lg border-2 cursor-pointer transition-all
                  ${isSelected
                    ? 'border-blue-400 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300 bg-white'
                  }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: info.color }}
                    />
                    <span className="text-sm font-medium text-gray-800">{info.name}</span>
                    {isSelected && (
                      <span className="text-xs font-bold text-blue-600 bg-blue-100 px-1.5 py-0.5 rounded">
                        {normalizedWeight}%
                      </span>
                    )}
                  </div>
                  <span className={`text-xs ${isSelected ? 'text-blue-500' : 'text-gray-400'}`}>
                    {isSelected ? '✓' : ''}
                  </span>
                </div>
                
                {isSelected && (
                  <div className="flex items-center gap-2">
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      value={weight}
                      onChange={(e) => handleWeightChange(style.id, e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      className="flex-1 h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />
                    <span className="text-xs text-gray-500 w-8">{weight.toFixed(2)}</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="mb-4">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium text-gray-600">融合强度</span>
          <span className="text-xs text-gray-500">{(intensity * 100).toFixed(0)}%</span>
        </div>
        <input
          type="range"
          min="0.1"
          max="1"
          step="0.05"
          value={intensity}
          onChange={(e) => setIntensity(parseFloat(e.target.value))}
          className="w-full h-2 bg-gradient-to-r from-gray-200 to-gray-300 rounded-lg appearance-none cursor-pointer accent-blue-500"
        />
      </div>

      <button
        onClick={handleBlend}
        disabled={loading || selectedStyles.length === 0 || !contentId}
        className={`w-full py-3 rounded-lg font-semibold text-white transition-all
          ${loading || selectedStyles.length === 0 || !contentId
            ? 'bg-gray-300 cursor-not-allowed'
            : 'bg-gradient-to-r from-blue-500 to-purple-500 hover:shadow-lg hover:scale-[1.02]'
          }`}
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <span className="animate-spin">⏳</span> 融合中...
          </span>
        ) : (
          <>🔮 生成融合风格</>
        )}
      </button>

      {result && (
        <div className="mt-4 p-3 bg-green-50 rounded-lg border border-green-200">
          <p className="text-xs text-green-700 font-medium">
            ✅ 融合完成！用时 {result.inference_time_ms}ms
          </p>
          <img
            src={`http://localhost:8000${result.output_url}`}
            alt="Blended result"
            className="mt-2 w-full rounded-lg"
          />
        </div>
      )}
    </div>
  );
};

export default StyleBlender;
