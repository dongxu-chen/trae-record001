import { useState } from 'react';
import { FileText, Upload, Sparkles, Loader2 } from 'lucide-react';
import SettingsPanel from './components/SettingsPanel';
import SummaryResult from './components/SummaryResult';
import MultiDocInput from './components/MultiDocInput';
import MultiDocSummaryResult from './components/MultiDocSummaryResult';
import { summarizeText, summarizeFile, multiDocSummarize } from './services/api';

const SAMPLE_TEXT = `人工智能（AI）正在以前所未有的速度改变着我们的世界。从自动驾驶汽车到智能语音助手，从医疗诊断到金融分析，AI技术正在渗透到我们生活的方方面面。机器学习作为AI的核心技术，通过大量数据的训练使计算机能够自主学习和改进。深度学习则进一步推动了AI的发展，通过模拟人脑神经网络的结构，实现了图像识别、自然语言处理等复杂任务的突破。

在自然语言处理领域，大型语言模型如BART、T5、GPT等取得了显著进展。这些模型能够理解和生成人类语言，为文本摘要、机器翻译、问答系统等应用提供了强大的技术支持。特别是文本摘要技术，能够帮助人们快速获取大量文档中的关键信息，大大提高了信息处理的效率。

然而，AI技术的发展也带来了一些挑战和思考。如何确保AI决策的公平性和透明性？如何保护用户隐私？如何应对AI可能带来的就业变化？这些都是我们需要认真思考和解决的问题。未来，随着技术的不断进步，我们有理由相信AI将继续为人类社会带来更多的便利和创新，同时也需要我们以负责任的态度来引导和规范其发展。

据最新统计，2025年全球AI市场规模已达到约1900亿美元，预计到2030年将增长至1.8万亿美元。仅在医疗健康领域，AI的应用就节省了超过25%的诊断时间，同时将误诊率降低了约15%。这些数字充分说明了AI技术的巨大潜力和实际价值。在纽约、旧金山和伦敦等主要科技中心，已有超过5000家AI初创公司获得了风险投资，累计融资金额超过350亿美元。`;

function App() {
  const [inputText, setInputText] = useState('');
  const [result, setResult] = useState(null);
  const [multiDocResult, setMultiDocResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('single');
  const [documents, setDocuments] = useState([]);
  const [settings, setSettings] = useState({
    summary_type: 'abstractive',
    model: 'bart',
    max_length: 150,
    min_length: 50,
    extractive_sentences: 3,
    preserve_keywords: true,
    language: null,
    enable_sliding_window: true,
    enable_fact_check: true,
    auto_correct: true,
    enable_topic_segmentation: false,
    topic_method: 'kmeans',
    num_topics: null,
    enable_quality_eval: true
  });

  const handleSingleDocSummarize = async () => {
    if (!inputText.trim() || inputText.length < 50) {
      setError('请输入至少50个字符的文本');
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await summarizeText({
        text: inputText,
        ...settings
      });
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || '生成摘要时出错，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  const handleMultiDocSummarize = async () => {
    if (documents.length < 2) {
      setError('请至少上传2个文档');
      return;
    }

    setIsLoading(true);
    setError(null);
    setMultiDocResult(null);

    try {
      const data = await multiDocSummarize({
        documents: documents.map(d => d.content),
        summary_type: settings.summary_type,
        model: settings.model,
        max_length: settings.max_length,
        num_sentences: settings.extractive_sentences,
        enable_quality_eval: settings.enable_quality_eval
      });
      setMultiDocResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || '生成多文档摘要时出错，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSummarize = () => {
    if (activeTab === 'single') {
      handleSingleDocSummarize();
    } else {
      handleMultiDocSummarize();
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.txt')) {
      setError('请上传TXT格式的文件');
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await summarizeFile(file, settings);
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || '处理文件时出错，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  const loadSampleText = () => {
    setInputText(SAMPLE_TEXT);
    setResult(null);
    setError(null);
  };

  const clearAll = () => {
    setInputText('');
    setResult(null);
    setMultiDocResult(null);
    setError(null);
    setDocuments([]);
  };

  const clearDocuments = () => {
    setDocuments([]);
    setMultiDocResult(null);
  };

  return (
    <div className="min-h-screen py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-10">
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4 flex items-center justify-center gap-3">
            <Sparkles className="w-10 h-10" />
            文本摘要生成工具
          </h1>
          <p className="text-white/80 text-lg max-w-2xl mx-auto">
            话题抽取分段 · 多文档综合摘要 · ROUGE质量评估
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            {activeTab === 'single' ? (
              <div className="bg-white rounded-2xl p-6 card-shadow">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                    <FileText className="w-6 h-6 text-purple-600" />
                    输入文本
                  </h3>
                  <div className="flex gap-2">
                    <button
                      onClick={loadSampleText}
                      className="px-4 py-2 text-sm text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
                    >
                      加载示例
                    </button>
                    <button
                      onClick={clearAll}
                      className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                      清空
                    </button>
                  </div>
                </div>

                <textarea
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="在此输入要摘要的文本内容（至少50个字符）...&#10;支持长文档，系统将自动使用滑动窗口分块处理"
                  className="w-full h-64 p-4 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent textarea-custom text-gray-700"
                />

                <div className="flex items-center justify-between mt-4">
                  <span className="text-sm text-gray-500">
                    字符数: {inputText.length}
                    {inputText.length > 5000 && (
                      <span className="ml-2 text-blue-500">· 长文档将启用滑动窗口</span>
                    )}
                  </span>
                  <label className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg cursor-pointer transition-colors">
                    <Upload className="w-4 h-4 text-gray-600" />
                    <span className="text-sm text-gray-600">上传TXT文件</span>
                    <input
                      type="file"
                      accept=".txt"
                      onChange={handleFileUpload}
                      className="hidden"
                    />
                  </label>
                </div>
              </div>
            ) : (
              <MultiDocInput
                documents={documents}
                setDocuments={setDocuments}
                onClear={clearDocuments}
              />
            )}

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-xl">
                {error}
              </div>
            )}

            <button
              onClick={handleSummarize}
              disabled={isLoading || (activeTab === 'multi' && documents.length < 2)}
              className="w-full py-4 btn-primary text-white font-semibold rounded-xl text-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  正在生成摘要...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  {activeTab === 'single' ? '生成摘要' : '生成多文档综合摘要'}
                </>
              )}
            </button>

            {activeTab === 'single' && result && <SummaryResult result={result} />}
            {activeTab === 'multi' && multiDocResult && (
              <MultiDocSummaryResult result={multiDocResult} />
            )}
          </div>

          <div className="lg:col-span-1">
            <SettingsPanel
              settings={settings}
              onSettingsChange={setSettings}
              activeTab={activeTab}
              onTabChange={setActiveTab}
            />
          </div>
        </div>

        <div className="mt-12 text-center text-white/60 text-sm">
          <p>话题抽取分段 · 多文档综合摘要 · ROUGE质量评估 · 滑动窗口增量摘要</p>
        </div>
      </div>
    </div>
  );
}

export default App;
