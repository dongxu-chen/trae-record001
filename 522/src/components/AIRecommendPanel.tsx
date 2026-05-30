import { useState, useEffect, useCallback } from 'react';
import { Brain, Sparkles, Sun, Zap, Star, ChevronRight, Loader2 } from 'lucide-react';
import { FilterRecommendation, analyzeImageContent, recommendFilters } from '@/utils/imageAnalyzer';
import { FILTER_DEFINITIONS } from '@/utils/shaderManager';
import useFilterStore from '@/store/filterStore';
import { cn } from '@/lib/utils';

const filterIcons: Record<string, React.ReactNode> = {
  dreamy: <Sparkles size={18} />,
  backlight: <Sun size={18} />,
  neon: <Zap size={18} />,
  starburst: <Star size={18} />,
};

interface AIRecommendPanelProps {
  imageElement: HTMLImageElement | null;
}

export default function AIRecommendPanel({ imageElement }: AIRecommendPanelProps) {
  const [recommendations, setRecommendations] = useState<FilterRecommendation[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzed, setAnalyzed] = useState(false);
  const { setActiveFilter, setFilterIntensity, setFilterParam } = useFilterStore();

  const analyze = useCallback(async () => {
    if (!imageElement) return;

    setIsAnalyzing(true);
    setAnalyzed(false);

    await new Promise((resolve) => setTimeout(resolve, 600));

    const analysis = analyzeImageContent(imageElement);
    const recs = recommendFilters(analysis);

    setRecommendations(recs);
    setIsAnalyzing(false);
    setAnalyzed(true);
  }, [imageElement]);

  useEffect(() => {
    if (imageElement && !analyzed) {
      setRecommendations([]);
      setAnalyzed(false);
    }
  }, [imageElement]);

  const applyRecommendation = (rec: FilterRecommendation) => {
    setActiveFilter(rec.filterId);
    setFilterIntensity(rec.suggestedIntensity);
    for (const [key, value] of Object.entries(rec.suggestedParams)) {
      setFilterParam(key, value);
    }
  };

  const scoreToPercent = (score: number) => Math.round(score * 100);

  return (
    <div className="glass-panel rounded-xl overflow-hidden">
      <div className="p-4 border-b border-surface-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neon-purple to-neon-cyan flex items-center justify-center">
              <Brain size={16} className="text-white" />
            </div>
            <div>
              <h3 className="font-display font-semibold text-sm neon-text">AI 智能推荐</h3>
              <p className="text-xs text-gray-500">分析图像内容推荐滤镜</p>
            </div>
          </div>
          <button
            onClick={analyze}
            disabled={!imageElement || isAnalyzing}
            className={cn(
              'px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200',
              isAnalyzing
                ? 'bg-neon-purple/20 text-neon-purple'
                : 'bg-surface-card hover:bg-surface-hover border border-surface-border'
            )}
          >
            {isAnalyzing ? (
              <span className="flex items-center gap-1">
                <Loader2 size={12} className="animate-spin" />
                分析中
              </span>
            ) : (
              '开始分析'
            )}
          </button>
        </div>
      </div>

      {analyzed && recommendations.length > 0 && (
        <div className="p-3 space-y-2">
          {recommendations.map((rec, index) => {
            const filterDef = FILTER_DEFINITIONS.find((f) => f.id === rec.filterId);
            const filterColor = filterDef?.color || '#B24BF3';
            const icon = filterIcons[rec.filterId] || <Sparkles size={18} />;
            const percent = scoreToPercent(rec.score);

            return (
              <button
                key={rec.filterId}
                onClick={() => applyRecommendation(rec)}
                className="w-full p-3 rounded-lg bg-surface-card hover:bg-surface-hover transition-all duration-200 text-left group"
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{
                      backgroundColor: `${filterColor}20`,
                      color: filterColor,
                    }}
                  >
                    {icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {index === 0 && (
                          <span className="text-[10px] px-1.5 py-0.5 bg-gradient-to-r from-neon-amber/20 to-neon-purple/20 text-neon-amber rounded font-medium">
                            最佳
                          </span>
                        )}
                        <span className="text-sm font-medium">{rec.filterName}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-mono" style={{ color: filterColor }}>
                          {percent}%
                        </span>
                        <ChevronRight
                          size={14}
                          className="text-gray-500 group-hover:text-gray-300 transition-colors"
                        />
                      </div>
                    </div>
                    <div className="mt-1.5 h-1 bg-surface-dark rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${percent}%`,
                          background: `linear-gradient(to right, ${filterColor}, ${filterColor}80)`,
                        }}
                      />
                    </div>
                    <p className="text-xs text-gray-500 mt-1.5 line-clamp-1">{rec.reason}</p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}

      {analyzed && recommendations.length === 0 && (
        <div className="p-4 text-center text-sm text-gray-500">
          未能生成推荐，请尝试其他图片
        </div>
      )}

      {!analyzed && !isAnalyzing && (
        <div className="p-4 text-center">
          <p className="text-xs text-gray-500">上传图片后点击"开始分析"</p>
        </div>
      )}
    </div>
  );
}
