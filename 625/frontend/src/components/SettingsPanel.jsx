import { Settings, Sliders, Bot, AlignLeft, Layers, ShieldCheck, BarChart3, FileStack } from 'lucide-react';

const SettingsPanel = ({ settings, onSettingsChange, activeTab, onTabChange }) => {
  return (
    <div className="bg-white rounded-2xl p-6 card-shadow">
      <div className="flex mb-6 bg-gray-100 rounded-xl p-1">
        <button
          onClick={() => onTabChange('single')}
          className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
            activeTab === 'single'
              ? 'bg-white text-purple-700 shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <FileStack className="w-4 h-4 inline mr-1" />
          单文档
        </button>
        <button
          onClick={() => onTabChange('multi')}
          className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
            activeTab === 'multi'
              ? 'bg-white text-purple-700 shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Layers className="w-4 h-4 inline mr-1" />
          多文档
        </button>
      </div>

      <h3 className="text-xl font-bold text-gray-800 flex items-center gap-2 mb-6">
        <Settings className="w-6 h-6 text-purple-600" />
        摘要设置
      </h3>

      <div className="space-y-6">
        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-3">
            <Bot className="w-4 h-4" />
            摘要类型
          </label>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => onSettingsChange({ ...settings, summary_type: 'abstractive' })}
              className={`p-3 rounded-xl border-2 transition-all ${
                settings.summary_type === 'abstractive'
                  ? 'border-purple-500 bg-purple-50 text-purple-700'
                  : 'border-gray-200 hover:border-gray-300 text-gray-600'
              }`}
            >
              <div className="font-medium">生成式</div>
              <div className="text-xs mt-1 opacity-70">AI生成新文本</div>
            </button>
            <button
              onClick={() => onSettingsChange({ ...settings, summary_type: 'extractive' })}
              className={`p-3 rounded-xl border-2 transition-all ${
                settings.summary_type === 'extractive'
                  ? 'border-purple-500 bg-purple-50 text-purple-700'
                  : 'border-gray-200 hover:border-gray-300 text-gray-600'
              }`}
            >
              <div className="font-medium">抽取式</div>
              <div className="text-xs mt-1 opacity-70">提取关键句子</div>
            </button>
          </div>
        </div>

        {(settings.summary_type === 'abstractive' || activeTab !== 'multi') && (
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-3">
              <Bot className="w-4 h-4" />
              选择模型
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => onSettingsChange({ ...settings, model: 'bart' })}
                className={`p-3 rounded-xl border-2 transition-all ${
                  settings.model === 'bart'
                    ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                    : 'border-gray-200 hover:border-gray-300 text-gray-600'
                }`}
              >
                <div className="font-medium">BART</div>
                <div className="text-xs mt-1 opacity-70">Facebook AI</div>
              </button>
              <button
                onClick={() => onSettingsChange({ ...settings, model: 't5' })}
                className={`p-3 rounded-xl border-2 transition-all ${
                  settings.model === 't5'
                    ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                    : 'border-gray-200 hover:border-gray-300 text-gray-600'
                }`}
              >
                <div className="font-medium">T5</div>
                <div className="text-xs mt-1 opacity-70">Google AI</div>
              </button>
            </div>
          </div>
        )}

        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-3">
            <Sliders className="w-4 h-4" />
            摘要长度设置
          </label>
          
          {settings.summary_type === 'abstractive' ? (
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs text-gray-500 mb-2">
                  <span>最小长度</span>
                  <span>{settings.min_length} 字符</span>
                </div>
                <input
                  type="range"
                  min="20"
                  max="200"
                  value={settings.min_length}
                  onChange={(e) => onSettingsChange({ ...settings, min_length: parseInt(e.target.value) })}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-600"
                />
              </div>
              <div>
                <div className="flex justify-between text-xs text-gray-500 mb-2">
                  <span>最大长度（强制停止）</span>
                  <span>{settings.max_length} 字符</span>
                </div>
                <input
                  type="range"
                  min="50"
                  max="500"
                  value={settings.max_length}
                  onChange={(e) => onSettingsChange({ ...settings, max_length: parseInt(e.target.value) })}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-600"
                />
                <p className="text-xs text-gray-400 mt-1">达到长度时将强制中断解码</p>
              </div>
            </div>
          ) : (
            <div>
              <div className="flex justify-between text-xs text-gray-500 mb-2">
                <span>句子数量</span>
                <span>{settings.extractive_sentences} 句</span>
              </div>
              <input
                type="range"
                min="1"
                max="20"
                value={settings.extractive_sentences}
                onChange={(e) => onSettingsChange({ ...settings, extractive_sentences: parseInt(e.target.value) })}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-600"
              />
            </div>
          )}
        </div>

        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
          <div className="flex items-center gap-2">
            <AlignLeft className="w-4 h-4 text-gray-600" />
            <span className="text-sm font-medium text-gray-700">保留关键信息</span>
          </div>
          <button
            onClick={() => onSettingsChange({ ...settings, preserve_keywords: !settings.preserve_keywords })}
            className={`relative w-12 h-6 rounded-full transition-colors ${
              settings.preserve_keywords ? 'bg-purple-600' : 'bg-gray-300'
            }`}
          >
            <span
              className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                settings.preserve_keywords ? 'translate-x-7' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-gray-600" />
            <div>
              <span className="text-sm font-medium text-gray-700">滑动窗口</span>
              <p className="text-xs text-gray-400">长文档分块+增量摘要</p>
            </div>
          </div>
          <button
            onClick={() => onSettingsChange({ ...settings, enable_sliding_window: !settings.enable_sliding_window })}
            className={`relative w-12 h-6 rounded-full transition-colors ${
              settings.enable_sliding_window ? 'bg-purple-600' : 'bg-gray-300'
            }`}
          >
            <span
              className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                settings.enable_sliding_window ? 'translate-x-7' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-600" />
            <div>
              <span className="text-sm font-medium text-gray-700">话题分段</span>
              <p className="text-xs text-gray-400">按话题分段输出摘要</p>
            </div>
          </div>
          <button
            onClick={() => onSettingsChange({ ...settings, enable_topic_segmentation: !settings.enable_topic_segmentation })}
            className={`relative w-12 h-6 rounded-full transition-colors ${
              settings.enable_topic_segmentation ? 'bg-blue-600' : 'bg-gray-300'
            }`}
          >
            <span
              className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                settings.enable_topic_segmentation ? 'translate-x-7' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-gray-600" />
            <div>
              <span className="text-sm font-medium text-gray-700">事实性校验</span>
              <p className="text-xs text-gray-400">数字模板+实体修正</p>
            </div>
          </div>
          <button
            onClick={() => onSettingsChange({ ...settings, enable_fact_check: !settings.enable_fact_check })}
            className={`relative w-12 h-6 rounded-full transition-colors ${
              settings.enable_fact_check ? 'bg-purple-600' : 'bg-gray-300'
            }`}
          >
            <span
              className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                settings.enable_fact_check ? 'translate-x-7' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {settings.enable_fact_check && (
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-green-600" />
              <div>
                <span className="text-sm font-medium text-gray-700">自动修正</span>
                <p className="text-xs text-gray-400">自动替换错误数字和实体</p>
              </div>
            </div>
            <button
              onClick={() => onSettingsChange({ ...settings, auto_correct: !settings.auto_correct })}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                settings.auto_correct ? 'bg-green-600' : 'bg-gray-300'
              }`}
            >
              <span
                className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  settings.auto_correct ? 'translate-x-7' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        )}

        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-indigo-600" />
            <div>
              <span className="text-sm font-medium text-gray-700">质量评估</span>
              <p className="text-xs text-gray-400">ROUGE指标+人类相关性</p>
            </div>
          </div>
          <button
            onClick={() => onSettingsChange({ ...settings, enable_quality_eval: !settings.enable_quality_eval })}
            className={`relative w-12 h-6 rounded-full transition-colors ${
              settings.enable_quality_eval ? 'bg-indigo-600' : 'bg-gray-300'
            }`}
          >
            <span
              className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                settings.enable_quality_eval ? 'translate-x-7' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {settings.enable_topic_segmentation && (
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-3">
              <Layers className="w-4 h-4" />
              话题提取方法
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => onSettingsChange({ ...settings, topic_method: 'kmeans' })}
                className={`p-3 rounded-xl border-2 transition-all ${
                  settings.topic_method === 'kmeans'
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:border-gray-300 text-gray-600'
                }`}
              >
                <div className="font-medium">K-Means</div>
                <div className="text-xs mt-1 opacity-70">聚类算法</div>
              </button>
              <button
                onClick={() => onSettingsChange({ ...settings, topic_method: 'lda' })}
                className={`p-3 rounded-xl border-2 transition-all ${
                  settings.topic_method === 'lda'
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:border-gray-300 text-gray-600'
                }`}
              >
                <div className="font-medium">LDA</div>
                <div className="text-xs mt-1 opacity-70">主题模型</div>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SettingsPanel;
