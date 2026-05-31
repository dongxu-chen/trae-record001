import { useEffect } from 'react';
import { Sparkles, Type, Code, Loader2, Globe, Tag, FileCode, Lightbulb } from 'lucide-react';
import { motion } from 'framer-motion';
import { useStore } from '../store/useStore';
import StyleSelector from '../components/StyleSelector';
import RecommendationCard from '../components/RecommendationCard';
import { cn } from '../lib/utils';

const Home = () => {
  const {
    input,
    inputType,
    context,
    targetStyle,
    recommendations,
    isLoading,
    error,
    detectedLanguage,
    detectedType,
    typeInference,
    processingTime,
    settings,
    copiedId,
    setInput,
    setInputType,
    setContext,
    setTargetStyle,
    getRecommendations,
    copyToClipboard,
    recordSelection,
    loadSettings
  } = useStore();

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    getRecommendations();
  };

  const handleCopy = (id: string, name: string, style: string) => {
    copyToClipboard(id, name);
    recordSelection(input, name, style as any);
  };

  const handleFeedback = (name: string, style: string, feedback: 'like' | 'dislike') => {
    const historyItem = useStore.getState().history.find(
      h => h.selectedName === name && h.style === style
    );
    if (historyItem) {
      useStore.getState().submitFeedback(historyItem.id, feedback);
    } else {
      recordSelection(input, name, style as any);
    }
  };

  const languageNames: Record<string, string> = {
    zh: '中文',
    en: 'English',
    ja: '日本語',
    ko: '한국어',
    other: '其他'
  };

  const typeNames: Record<string, string> = {
    variable: '变量',
    function: '函数',
    class: '类',
    constant: '常量',
    boolean: '布尔值'
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50/30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <h2 className="text-3xl font-bold text-gray-900 mb-2">
            智能变量命名推荐
          </h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            输入变量描述或代码上下文，AI 将为您推荐符合规范的变量名
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="lg:col-span-2"
          >
            <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <div className="mb-6">
                <label className="text-sm font-medium text-gray-700 mb-3 block">
                  输入类型
                </label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setInputType('description')}
                    className={cn(
                      'flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-sm font-medium transition-all duration-200',
                      inputType === 'description'
                        ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/30'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    )}
                  >
                    <Type className="w-4 h-4" />
                    文本描述
                  </button>
                  <button
                    type="button"
                    onClick={() => setInputType('code')}
                    className={cn(
                      'flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-sm font-medium transition-all duration-200',
                      inputType === 'code'
                        ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/30'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    )}
                  >
                    <Code className="w-4 h-4" />
                    代码上下文
                  </button>
                </div>
              </div>

              <div className="mb-6">
                <label className="text-sm font-medium text-gray-700 mb-2 block">
                  {inputType === 'description' ? '变量描述' : '代码片段'}
                </label>
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={
                    inputType === 'description'
                      ? '例如：用户登录时间、获取商品列表、是否启用缓存...'
                      : '粘贴代码片段，系统将分析上下文并推荐合适的变量名...'
                  }
                  className={cn(
                    'w-full h-32 px-4 py-3 rounded-xl border resize-none transition-all duration-200 focus:outline-none focus:ring-2',
                    inputType === 'code'
                      ? 'font-mono text-sm bg-gray-900 text-gray-100 border-gray-800 focus:ring-blue-500/50'
                      : 'bg-gray-50 border-gray-200 focus:bg-white focus:ring-blue-500/30 focus:border-blue-500'
                  )}
                />
              </div>

              <div className="mb-6">
                <label className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                  <FileCode className="w-4 h-4" />
                  上下文代码（可选）
                </label>
                <textarea
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  placeholder="粘贴相关代码上下文，帮助系统更准确地推断类型...
例如: class UserService { ... } 或 function processData() { ... }"
                  className="w-full h-24 px-4 py-3 rounded-xl border resize-none transition-all duration-200 focus:outline-none focus:ring-2 font-mono text-sm bg-gray-900 text-gray-100 border-gray-800 focus:ring-blue-500/50"
                />
              </div>

              <div className="mb-6">
                <StyleSelector value={targetStyle} onChange={setTargetStyle} />
              </div>

              {error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="w-full flex items-center justify-center gap-2 py-3 px-6 bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-medium rounded-xl shadow-lg shadow-blue-500/30 hover:shadow-xl hover:shadow-blue-500/40 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    生成中...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    生成推荐
                  </>
                )}
              </button>
            </form>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="lg:col-span-3"
          >
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 min-h-[600px]">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
                <h3 className="text-lg font-semibold text-gray-900">推荐结果</h3>
                <div className="flex flex-wrap items-center gap-3 text-sm text-gray-500">
                  {detectedLanguage && (
                    <div className="flex items-center gap-1">
                      <Globe className="w-4 h-4" />
                      {languageNames[detectedLanguage] || detectedLanguage}
                    </div>
                  )}
                  {detectedType && (
                    <div className="flex items-center gap-1">
                      <Tag className="w-4 h-4" />
                      {typeNames[detectedType] || detectedType}
                    </div>
                  )}
                  {processingTime > 0 && (
                    <div className="text-gray-400">{processingTime}ms</div>
                  )}
                </div>
              </div>

              {typeInference && typeInference.hints.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-xl"
                >
                  <div className="flex items-start gap-2">
                    <Lightbulb className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="text-sm font-medium text-amber-800 mb-1">
                        类型推断 (置信度: {(typeInference.confidence * 100).toFixed(0)}%)
                      </div>
                      <div className="text-xs text-amber-700 space-y-1">
                        {typeInference.hints.slice(0, 3).map((hint, i) => (
                          <div key={i}>• {hint}</div>
                        ))}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {recommendations.length > 0 ? (
                <div className="space-y-3">
                  {recommendations.map((rec, index) => (
                    <RecommendationCard
                      key={rec.id}
                      recommendation={rec}
                      index={index}
                      copiedId={copiedId}
                      showConfidence={settings.showConfidence}
                      onCopy={(id, name) => handleCopy(id, name, rec.style)}
                      onFeedback={handleFeedback}
                    />
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-80 text-gray-400">
                  <Sparkles className="w-16 h-16 mb-4 opacity-50" />
                  <p className="text-center">
                    输入变量描述或代码上下文<br />
                    点击「生成推荐」获取建议
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default Home;
