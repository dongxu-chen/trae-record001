
import { useState, useEffect } from 'react';
import { Scale, AlertTriangle, CheckCircle, Info, TrendingUp } from 'lucide-react';
import { useCardStore } from '@/stores/cardStore';
import type { CardData, BalanceAnalysis } from '@/types';

const GRADE_COLORS: Record<string, string> = {
  S: 'text-yellow-400',
  A: 'text-green-400',
  B: 'text-blue-400',
  C: 'text-gray-400',
  D: 'text-orange-400',
  F: 'text-red-400',
};

const GRADE_BG: Record<string, string> = {
  S: 'bg-yellow-400/10 border-yellow-400/30',
  A: 'bg-green-400/10 border-green-400/30',
  B: 'bg-blue-400/10 border-blue-400/30',
  C: 'bg-gray-400/10 border-gray-400/30',
  D: 'bg-orange-400/10 border-orange-400/30',
  F: 'bg-red-400/10 border-red-400/30',
};

export default function BalanceAnalysisPage() {
  const { cards, fetchCards } = useCardStore();
  const [selectedCard, setSelectedCard] = useState<CardData | null>(null);
  const [analysis, setAnalysis] = useState<BalanceAnalysis | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    fetchCards();
  }, [fetchCards]);

  const handleAnalyze = async (card: CardData) => {
    setSelectedCard(card);
    setIsAnalyzing(true);
    setMessage(null);

    try {
      const response = await fetch('/api/ai/balance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(card),
      });

      const result = await response.json();
      if (result.success) {
        setAnalysis(result.data);
      } else {
        setMessage({ type: 'error', text: result.error || '分析失败' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: '网络错误，请重试' });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getIssueIcon = (type: string) => {
    switch (type) {
      case 'error': return <AlertTriangle size={16} className="text-red-400" />;
      case 'warning': return <AlertTriangle size={16} className="text-yellow-400" />;
      default: return <Info size={16} className="text-blue-400" />;
    }
  };

  return (
    <div className="h-full overflow-auto p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <Scale className="text-gold-500" size={28} />
          <h1 className="font-cinzel text-2xl text-gold-500">卡牌平衡分析</h1>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <div className="bg-dark-800 rounded-xl p-4 border border-dark-600">
              <h2 className="font-cinzel text-lg text-parchment-100 mb-4">选择卡牌</h2>
              <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
                {cards.map((card) => (
                  <button
                    key={card.id}
                    onClick={() => handleAnalyze(card)}
                    className={`w-full p-3 rounded-lg text-left transition-all ${
                      selectedCard?.id === card.id
                        ? 'bg-dark-700 border border-gold-500/30'
                        : 'bg-dark-900/50 hover:bg-dark-700/50 border border-transparent'
                    }`}
                  >
                    <div className="font-medium text-parchment-100">{card.name}</div>
                    <div className="text-xs text-parchment-200/50 mt-1">
                      {card.rarity} · {card.type} · 费用 {card.attributes.cost}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="lg:col-span-2 space-y-6">
            {isAnalyzing ? (
              <div className="bg-dark-800 rounded-xl p-8 border border-dark-600 text-center">
                <TrendingUp className="mx-auto text-gold-500 animate-pulse" size={48} />
                <p className="mt-4 text-parchment-200/60">正在分析卡牌平衡性...</p>
              </div>
            ) : analysis && selectedCard ? (
              <>
                <div className="bg-dark-800 rounded-xl p-6 border border-dark-600">
                  <div className="flex items-start justify-between">
                    <div>
                      <h2 className="font-cinzel text-xl text-parchment-100">{selectedCard.name}</h2>
                      <p className="text-parchment-200/50 mt-1">平衡分析报告</p>
                    </div>
                    <div className={`px-6 py-4 rounded-xl border-2 ${GRADE_BG[analysis.grade]}`}>
                      <div className={`text-4xl font-bold font-cinzel ${GRADE_COLORS[analysis.grade]}`}>
                        {analysis.grade}
                      </div>
                      <div className="text-xs text-parchment-200/50 text-center mt-1">
                        {analysis.score} 分
                      </div>
                    </div>
                  </div>

                  <div className="mt-6">
                    <div className="w-full h-3 bg-dark-900 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 transition-all duration-500"
                        style={{ width: `${analysis.score}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-xs text-parchment-200/40 mt-1">
                      <span>0</span>
                      <span>50</span>
                      <span>100</span>
                    </div>
                  </div>
                </div>

                <div className="bg-dark-800 rounded-xl p-6 border border-dark-600">
                  <h3 className="font-cinzel text-lg text-parchment-100 mb-4">数据统计</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-dark-900/50 rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-gold-500">{analysis.stats.totalPower.toFixed(1)}</div>
                      <div className="text-xs text-parchment-200/50 mt-1">总战力</div>
                    </div>
                    <div className="bg-dark-900/50 rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-blue-400">{analysis.stats.costEfficiency.toFixed(2)}</div>
                      <div className="text-xs text-parchment-200/50 mt-1">费用效率</div>
                    </div>
                    <div className="bg-dark-900/50 rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-purple-400">{analysis.stats.skillPower}</div>
                      <div className="text-xs text-parchment-200/50 mt-1">技能强度</div>
                    </div>
                    <div className="bg-dark-900/50 rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-green-400">{analysis.stats.rarityScore}</div>
                      <div className="text-xs text-parchment-200/50 mt-1">稀有度评分</div>
                    </div>
                  </div>

                  <div className="mt-4">
                    <div className="text-sm text-parchment-200/50 mb-2">属性分布</div>
                    <div className="flex gap-2">
                      {Object.entries(analysis.stats.attributeDistribution).map(([key, value]) => (
                        <div key={key} className="flex-1">
                          <div className="text-xs text-parchment-200/40 mb-1 capitalize">{key}</div>
                          <div className="w-full h-2 bg-dark-900 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-gold-500"
                              style={{ width: `${(value / 20) * 100}%` }}
                            />
                          </div>
                          <div className="text-xs text-parchment-100 mt-1">{value}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="bg-dark-800 rounded-xl p-6 border border-dark-600">
                  <h3 className="font-cinzel text-lg text-parchment-100 mb-4">问题检测</h3>
                  {analysis.issues.length > 0 ? (
                    <div className="space-y-3">
                      {analysis.issues.map((issue, i) => (
                        <div
                          key={i}
                          className={`p-3 rounded-lg border ${
                            issue.type === 'error'
                              ? 'bg-red-900/20 border-red-500/30'
                              : issue.type === 'warning'
                              ? 'bg-yellow-900/20 border-yellow-500/30'
                              : 'bg-blue-900/20 border-blue-500/30'
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            {getIssueIcon(issue.type)}
                            <div className="flex-1">
                              <div className="text-sm text-parchment-200/50 mb-1">{issue.category}</div>
                              <div className="text-parchment-100">{issue.message}</div>
                              {issue.suggestion && (
                                <div className="text-sm text-parchment-200/60 mt-1">
                                  💡 {issue.suggestion}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-parchment-200/40">
                      <CheckCircle size={48} className="mx-auto mb-3 text-green-500" />
                      <p>未发现明显平衡问题</p>
                    </div>
                  )}
                </div>

                <div className="bg-dark-800 rounded-xl p-6 border border-dark-600">
                  <h3 className="font-cinzel text-lg text-parchment-100 mb-4">优化建议</h3>
                  <ul className="space-y-2">
                    {analysis.recommendations.map((rec, i) => (
                      <li key={i} className="flex items-start gap-2 text-parchment-200/80">
                        <span className="text-gold-500">•</span>
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            ) : (
              <div className="bg-dark-800 rounded-xl p-8 border border-dark-600 text-center">
                <Scale className="mx-auto text-parchment-200/30" size={48} />
                <p className="mt-4 text-parchment-200/50">从左侧选择一张卡牌进行平衡分析</p>
              </div>
            )}

            {message && (
              <div className={`p-4 rounded-lg ${
                message.type === 'success'
                  ? 'bg-green-900/30 border border-green-500/30 text-green-400'
                  : 'bg-red-900/30 border border-red-500/30 text-red-400'
              }`}>
                {message.text}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
