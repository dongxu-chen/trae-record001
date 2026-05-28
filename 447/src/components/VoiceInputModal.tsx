import { useEffect, useRef, useState, useCallback } from 'react';
import { X, Mic, MicOff, Check, RotateCcw, Volume2, VolumeX } from 'lucide-react';
import katex from 'katex';
import { useEditorStore } from '@/store/useEditorStore';
import {
  voiceTextToLatex,
  VoiceRecognitionManager,
  speakText,
  type RecognitionResult,
} from '@/utils/voiceToLatex';

export default function VoiceInputModal() {
  const { showVoiceInputModal, toggleVoiceInputModal, setLatex } = useEditorStore();
  const [isListening, setIsListening] = useState(false);
  const [interimText, setInterimText] = useState('');
  const [finalText, setFinalText] = useState('');
  const [convertedLatex, setConvertedLatex] = useState('');
  const [confidence, setConfidence] = useState(0);
  const [error, setError] = useState('');
  const [isSpeaking, setIsSpeaking] = useState(false);
  const managerRef = useRef<VoiceRecognitionManager | null>(null);

  useEffect(() => {
    if (!showVoiceInputModal) return;
    setInterimText('');
    setFinalText('');
    setConvertedLatex('');
    setConfidence(0);
    setError('');
    setIsListening(false);

    return () => {
      if (managerRef.current) {
        managerRef.current.abort();
        managerRef.current = null;
      }
    };
  }, [showVoiceInputModal]);

  const handleResult = useCallback((result: RecognitionResult) => {
    if (result.isFinal) {
      const newFinal = finalText + ' ' + result.transcript;
      setFinalText(newFinal.trim());
      setInterimText('');
      const { latex, confidence: conf } = voiceTextToLatex(newFinal.trim());
      setConvertedLatex(latex);
      setConfidence(conf);
    } else {
      setInterimText(result.transcript);
      const fullText = (finalText + ' ' + result.transcript).trim();
      const { latex, confidence: conf } = voiceTextToLatex(fullText);
      setConvertedLatex(latex);
      setConfidence(conf);
    }
  }, [finalText]);

  const handleError = useCallback((errMsg: string) => {
    setError(errMsg);
    setIsListening(false);
  }, []);

  const handleEnd = useCallback(() => {
    setIsListening(false);
  }, []);

  const startListening = useCallback(() => {
    if (!managerRef.current) {
      managerRef.current = new VoiceRecognitionManager(
        handleResult,
        handleError,
        handleEnd,
      );
    }
    setError('');
    managerRef.current.start();
    setIsListening(true);
  }, [handleResult, handleError, handleEnd]);

  const stopListening = useCallback(() => {
    if (managerRef.current) {
      managerRef.current.stop();
    }
    setIsListening(false);
  }, []);

  const clearAll = useCallback(() => {
    setInterimText('');
    setFinalText('');
    setConvertedLatex('');
    setConfidence(0);
    setError('');
    if (managerRef.current) {
      managerRef.current.abort();
    }
    setIsListening(false);
  }, []);

  const insertLatex = useCallback(() => {
    if (convertedLatex) {
      setLatex(convertedLatex);
      toggleVoiceInputModal();
    }
  }, [convertedLatex, setLatex, toggleVoiceInputModal]);

  const speakPreview = useCallback(() => {
    if (!convertedLatex) return;
    setIsSpeaking(true);
    speakText(convertedLatex.replace(/\\/g, ' ').replace(/[{}]/g, ' '));
    setTimeout(() => setIsSpeaking(false), 2000);
  }, [convertedLatex]);

  if (!showVoiceInputModal) return null;

  const isSupported = VoiceRecognitionManager.isSupported();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-fade-in" onClick={toggleVoiceInputModal}>
      <div
        className="bg-bg-secondary rounded-xl shadow-2xl w-[520px] animate-scale-in overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-border-custom">
          <span className="text-sm font-medium text-text-primary">语音输入公式</span>
          <button onClick={toggleVoiceInputModal} className="p-1 text-text-muted hover:text-text-primary transition-colors rounded hover:bg-bg-tertiary">
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {!isSupported ? (
            <div className="p-4 bg-warning/10 text-warning text-sm rounded-lg">
              当前浏览器不支持语音识别功能。请使用 Chrome、Edge 或 Safari 浏览器。
            </div>
          ) : error ? (
            <div className="p-4 bg-danger/10 text-danger text-sm rounded-lg flex items-center gap-2">
              <MicOff size={16} />
              {error}
            </div>
          ) : (
            <>
              <div className="flex flex-col items-center gap-3 py-4">
                <button
                  onClick={isListening ? stopListening : startListening}
                  className={`w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300 ${
                    isListening
                      ? 'bg-danger animate-glow-pulse scale-110'
                      : 'bg-accent hover:bg-accent-hover hover:scale-105'
                  }`}
                >
                  {isListening ? (
                    <Mic size={32} className="text-white" />
                  ) : (
                    <Mic size={32} className="text-bg-primary" />
                  )}
                </button>

                <div className="text-center">
                  {isListening ? (
                    <div className="flex items-center gap-1">
                      <span className="w-2 h-2 bg-danger rounded-full animate-pulse" />
                      <span className="text-sm text-text-primary font-medium">正在听...</span>
                    </div>
                  ) : (
                    <span className="text-sm text-text-muted">点击麦克风开始说话</span>
                  )}
                </div>

                {isListening && (
                  <div className="flex items-end gap-0.5 h-8">
                    {Array.from({ length: 16 }).map((_, i) => (
                      <div
                        key={i}
                        className="w-1 bg-accent rounded-full animate-pulse"
                        style={{
                          height: `${Math.random() * 24 + 8}px`,
                          animationDelay: `${i * 0.05}s`,
                        }}
                      />
                    ))}
                  </div>
                )}
              </div>

              {(finalText || interimText) && (
                <div className="space-y-1.5">
                  <span className="text-xs text-text-muted uppercase tracking-wide">识别文本</span>
                  <div className="bg-bg-tertiary rounded-lg p-3 text-sm text-text-primary min-h-[40px] border border-border-custom">
                    <span className="text-text-secondary">{finalText}</span>
                    <span className="text-text-muted opacity-60"> {interimText}</span>
                  </div>
                </div>
              )}

              {convertedLatex && (
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-text-muted uppercase tracking-wide">转换结果</span>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-text-muted">
                        置信度: <span className={`font-medium ${
                          confidence > 0.7 ? 'text-accent' : confidence > 0.5 ? 'text-warning' : 'text-danger'
                        }`}>
                          {Math.round(confidence * 100)}%
                        </span>
                      </span>
                      <button
                        onClick={speakPreview}
                        className="p-1 text-text-muted hover:text-accent transition-colors rounded hover:bg-bg-tertiary"
                        title="朗读预览"
                      >
                        {isSpeaking ? <Volume2 size={14} className="text-accent animate-pulse" /> : <VolumeX size={14} />}
                      </button>
                    </div>
                  </div>
                  <div className="bg-bg-tertiary rounded-lg p-3 font-mono text-sm text-accent break-all border border-border-custom">
                    {convertedLatex}
                  </div>
                  <div className="katex-preview bg-bg-primary rounded-lg p-3 overflow-x-auto min-h-[50px] flex items-center justify-center">
                    <div
                      dangerouslySetInnerHTML={{
                        __html: (() => {
                          try {
                            return katex.renderToString(convertedLatex, { displayMode: true, throwOnError: false });
                          } catch {
                            return '<span style="color:#EF4444">预览失败</span>';
                          }
                        })(),
                      }}
                    />
                  </div>
                </div>
              )}

              <div className="p-3 bg-accent/5 border border-accent/20 rounded-lg">
                <div className="text-xs text-accent font-medium mb-1.5">语音命令提示</div>
                <div className="grid grid-cols-2 gap-1 text-[11px] text-text-secondary">
                  <span>"分数 x 分之 y" → x/y</span>
                  <span>"根号 2" → √2</span>
                  <span>"积分 从 0 到 无穷" → ∫₀^∞</span>
                  <span>"求和 从 n=1 到 无穷" → ∑ₙ=1^∞</span>
                  <span>"x 的 3 次方" → x³</span>
                  <span>"阿尔法 + 贝塔" → α+β</span>
                  <span>"矩阵 3 行 3 列" → 3×3矩阵</span>
                  <span>"绝对值 x" → |x|</span>
                </div>
              </div>
            </>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-border-custom">
          <button
            onClick={clearAll}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-text-secondary bg-bg-tertiary rounded-lg hover:text-text-primary transition-colors"
          >
            <RotateCcw size={14} />
            清除
          </button>
          {convertedLatex && (
            <button
              onClick={insertLatex}
              className="flex items-center gap-1.5 px-4 py-1.5 text-sm bg-accent text-bg-primary font-medium rounded-lg hover:bg-accent-hover transition-colors"
            >
              <Check size={14} />
              插入公式
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
