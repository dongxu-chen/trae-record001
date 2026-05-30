import React, { useState, useCallback } from 'react';
import {
  generateCreativeSuggestions,
  CreativeSuggestion,
  CreativeResult,
} from '../engine/creativeEngine';
import { IconConfig, IconStyle } from '../engine/types';
import {
  Sparkles,
  Search,
  Wand2,
  Check,
  Palette,
  Zap,
  Lightbulb,
  Tag,
} from 'lucide-react';

interface AICreativePanelProps {
  currentConfig: IconConfig;
  onApplySuggestion: (config: Partial<IconConfig>) => void;
}

export function AICreativePanel({ currentConfig, onApplySuggestion }: AICreativePanelProps) {
  const [keyword, setKeyword] = useState('');
  const [result, setResult] = useState<CreativeResult | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [appliedId, setAppliedId] = useState<string | null>(null);

  const generate = useCallback(() => {
    if (!keyword.trim()) return;

    setIsGenerating(true);
    setTimeout(() => {
      const creativeResult = generateCreativeSuggestions(keyword);
      setResult(creativeResult);
      setIsGenerating(false);
    }, 600);
  }, [keyword]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      generate();
    }
  };

  const applySuggestion = (suggestion: CreativeSuggestion) => {
    onApplySuggestion(suggestion.config);
    setAppliedId(suggestion.id);
    setTimeout(() => setAppliedId(null), 2000);
  };

  const getStyleLabel = (style: IconStyle) => {
    const labels: Record<IconStyle, string> = {
      outline: '线框',
      filled: '填充',
      gradient: '渐变',
      '3d': '3D立体',
    };
    return labels[style];
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl p-6">
      <div className="flex items-center gap-3 pb-4 border-b border-gray-100 mb-6">
        <div className="p-2 bg-gradient-to-br from-pink-500 to-orange-500 rounded-xl">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-800">AI 图标创意</h3>
          <p className="text-sm text-gray-500">输入关键词，获取智能设计方案</p>
        </div>
      </div>

      <div className="space-y-4">
        <div className="relative">
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="例如：科技公司、环保品牌、游戏App..."
            className="w-full pl-12 pr-24 py-4 border-2 border-gray-200 rounded-xl focus:border-pink-500 focus:ring-4 focus:ring-pink-100 transition-all duration-200 text-base"
          />
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <button
            onClick={generate}
            disabled={isGenerating || !keyword.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1 px-4 py-2 bg-gradient-to-r from-pink-500 to-orange-500 text-white rounded-lg text-sm font-medium hover:from-pink-600 hover:to-orange-600 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Wand2 className="w-4 h-4" />
            {isGenerating ? '生成中' : '生成'}
          </button>
        </div>

        <div className="flex flex-wrap gap-2">
          {['科技', '环保', '游戏', '金融', '教育', '健康', '美食', '极简', '音乐'].map((tag) => (
            <button
              key={tag}
              onClick={() => {
                setKeyword(tag);
              }}
              className="flex items-center gap-1 px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full text-sm hover:bg-pink-100 hover:text-pink-600 transition-colors"
            >
              <Tag className="w-3 h-3" />
              {tag}
            </button>
          ))}
        </div>

        {result && (
          <div className="mt-6 space-y-4 animate-fadeIn">
            <div className="p-4 bg-gradient-to-r from-pink-50 to-orange-50 rounded-xl border border-pink-100">
              <div className="flex items-start gap-3">
                <Lightbulb className="w-5 h-5 text-orange-500 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-gray-800 font-medium mb-2">{result.description}</p>
                  <div className="flex flex-wrap gap-3 items-center">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-600">推荐风格:</span>
                      <span className="px-2 py-1 bg-white rounded text-sm font-medium text-pink-600">
                        {getStyleLabel(result.recommendedStyle)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-600">情绪色调:</span>
                      <span className="px-2 py-1 bg-white rounded text-sm font-medium text-orange-600">
                        {result.mood}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Palette className="w-4 h-4 text-gray-500" />
                      <div className="flex gap-1">
                        <div
                          className="w-5 h-5 rounded-full border-2 border-white shadow-sm"
                          style={{ backgroundColor: result.primaryColor }}
                        />
                        <div
                          className="w-5 h-5 rounded-full border-2 border-white shadow-sm"
                          style={{ backgroundColor: result.secondaryColor }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid gap-3">
              {result.suggestions.map((suggestion) => (
                <div
                  key={suggestion.id}
                  className="p-4 border-2 border-gray-100 rounded-xl hover:border-pink-200 hover:bg-pink-50/30 transition-all duration-200 group"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-semibold text-gray-800">{suggestion.name}</h4>
                        <div
                          className="w-4 h-4 rounded-full"
                          style={{ backgroundColor: suggestion.config.primaryColor }}
                        />
                      </div>
                      <p className="text-sm text-gray-500 mb-2">{suggestion.description}</p>
                      <div className="flex flex-wrap gap-2">
                        <span className="px-2 py-0.5 bg-blue-50 text-blue-600 rounded text-xs">
                          {getStyleLabel(suggestion.config.style as IconStyle)}
                        </span>
                        {suggestion.tags.map((tag) => (
                          <span
                            key={tag}
                            className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                      {suggestion.usageContext && (
                        <p className="text-xs text-gray-400 mt-2">
                          适用场景: {suggestion.usageContext}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={() => applySuggestion(suggestion)}
                      className={`flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                        appliedId === suggestion.id
                          ? 'bg-green-500 text-white'
                          : 'bg-pink-100 text-pink-600 hover:bg-pink-200'
                      }`}
                    >
                      {appliedId === suggestion.id ? (
                        <>
                          <Check className="w-4 h-4" />
                          已应用
                        </>
                      ) : (
                        <>
                          <Zap className="w-4 h-4" />
                          应用
                        </>
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {!result && !isGenerating && (
          <div className="text-center py-8 text-gray-400">
            <Sparkles className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>输入关键词，让AI为您推荐图标设计方案</p>
          </div>
        )}

        {isGenerating && (
          <div className="text-center py-8">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-pink-100 text-pink-600 rounded-full animate-pulse">
              <Wand2 className="w-5 h-5 animate-spin" />
              <span className="font-medium">正在为您生成创意方案...</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
