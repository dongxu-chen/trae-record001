
import { useState, useEffect } from 'react';
import { Swords, Shield, Zap, TrendingUp, Play, RotateCcw, BarChart3 } from 'lucide-react';
import { useCardStore } from '@/stores/cardStore';
import type { CardData, BattleResult, DeckAnalysis } from '@/types';

export default function BattleSim() {
  const { cards, fetchCards } = useCardStore();
  const [deck1, setDeck1] = useState<string[]>([]);
  const [deck2, setDeck2] = useState<string[]>([]);
  const [battleResult, setBattleResult] = useState<BattleResult | null>(null);
  const [deck1Analysis, setDeck1Analysis] = useState<DeckAnalysis | null>(null);
  const [deck2Analysis, setDeck2Analysis] = useState<DeckAnalysis | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [showLog, setShowLog] = useState(false);

  useEffect(() => {
    fetchCards();
  }, [fetchCards]);

  const toggleCardInDeck = (cardId: string, deckNumber: 1 | 2) => {
    if (deckNumber === 1) {
      if (deck1.includes(cardId)) {
        setDeck1(deck1.filter(id => id !== cardId));
      } else if (deck1.length < 10) {
        setDeck1([...deck1, cardId]);
      }
    } else {
      if (deck2.includes(cardId)) {
        setDeck2(deck2.filter(id => id !== cardId));
      } else if (deck2.length < 10) {
        setDeck2([...deck2, cardId]);
      }
    }
  };

  const analyzeDeck = async (cardIds: string[], setAnalysis: (a: DeckAnalysis | null) => void) => {
    if (cardIds.length === 0) {
      setAnalysis(null);
      return;
    }

    try {
      const response = await fetch('/api/ai/deck/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cardIds }),
      });

      const result = await response.json();
      if (result.success) {
        setAnalysis(result.data);
      }
    } catch (error) {
      console.error('Deck analysis error:', error);
    }
  };

  useEffect(() => {
    const timeout = setTimeout(() => {
      analyzeDeck(deck1, setDeck1Analysis);
    }, 300);
    return () => clearTimeout(timeout);
  }, [deck1]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      analyzeDeck(deck2, setDeck2Analysis);
    }, 300);
    return () => clearTimeout(timeout);
  }, [deck2]);

  const handleSimulate = async () => {
    if (deck1.length === 0 || deck2.length === 0) {
      setMessage({ type: 'error', text: '请为双方都选择至少一张卡牌' });
      return;
    }

    setIsSimulating(true);
    setMessage(null);
    setBattleResult(null);

    try {
      const response = await fetch('/api/ai/battle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deck1Ids: deck1, deck2Ids: deck2, maxTurns: 30 }),
      });

      const result = await response.json();
      if (result.success) {
        setBattleResult(result.data);
      } else {
        setMessage({ type: 'error', text: result.error || '模拟失败' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: '网络错误，请重试' });
    } finally {
      setIsSimulating(false);
    }
  };

  const handleReset = () => {
    setDeck1([]);
    setDeck2([]);
    setBattleResult(null);
    setDeck1Analysis(null);
    setDeck2Analysis(null);
    setMessage(null);
    setShowLog(false);
  };

  const getCardById = (id: string) => cards.find(c => c.id === id);

  const renderDeckAnalysis = (analysis: DeckAnalysis | null) => {
    if (!analysis) return null;

    return (
      <div className="mt-4 p-3 bg-dark-900/50 rounded-lg">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-parchment-200/60">卡组强度</span>
          <span className="font-bold text-gold-500">{analysis.deckStrength}</span>
        </div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-parchment-200/60">协同评分</span>
          <div className="flex items-center gap-2">
            <div className="w-20 h-2 bg-dark-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500"
                style={{ width: `${analysis.synergyScore}%` }}
              />
            </div>
            <span className="text-sm text-green-400">{analysis.synergyScore}</span>
          </div>
        </div>
        {analysis.recommendations.slice(0, 2).map((rec, i) => (
          <div key={i} className="text-xs text-parchment-200/50 mt-1">
            💡 {rec}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="h-full overflow-auto p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <Swords className="text-gold-500" size={28} />
          <h1 className="font-cinzel text-2xl text-gold-500">卡牌对战模拟</h1>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="grid grid-cols-2 gap-6">
              <div className="bg-dark-800 rounded-xl p-4 border border-blue-500/30">
                <div className="flex items-center gap-2 mb-4">
                  <Shield className="text-blue-400" size={20} />
                  <h2 className="font-cinzel text-lg text-parchment-100">卡组 1</h2>
                  <span className="ml-auto text-sm text-parchment-200/50">{deck1.length}/10</span>
                </div>

                <div className="flex flex-wrap gap-2 min-h-[80px]">
                  {deck1.map((cardId) => {
                    const card = getCardById(cardId);
                    return card ? (
                      <button
                        key={cardId}
                        onClick={() => toggleCardInDeck(cardId, 1)}
                        className="px-2 py-1 bg-blue-900/30 border border-blue-500/30 rounded text-sm text-parchment-100 hover:bg-red-900/30 hover:border-red-500/30 transition-colors"
                      >
                        {card.name}
                      </button>
                    ) : null;
                  })}
                  {deck1.length === 0 && (
                    <div className="text-parchment-200/30 text-sm">从下方选择卡牌添加</div>
                  )}
                </div>

                {renderDeckAnalysis(deck1Analysis)}
              </div>

              <div className="bg-dark-800 rounded-xl p-4 border border-red-500/30">
                <div className="flex items-center gap-2 mb-4">
                  <Zap className="text-red-400" size={20} />
                  <h2 className="font-cinzel text-lg text-parchment-100">卡组 2</h2>
                  <span className="ml-auto text-sm text-parchment-200/50">{deck2.length}/10</span>
                </div>

                <div className="flex flex-wrap gap-2 min-h-[80px]">
                  {deck2.map((cardId) => {
                    const card = getCardById(cardId);
                    return card ? (
                      <button
                        key={cardId}
                        onClick={() => toggleCardInDeck(cardId, 2)}
                        className="px-2 py-1 bg-red-900/30 border border-red-500/30 rounded text-sm text-parchment-100 hover:bg-red-900/30 hover:border-red-500/30 transition-colors"
                      >
                        {card.name}
                      </button>
                    ) : null;
                  })}
                  {deck2.length === 0 && (
                    <div className="text-parchment-200/30 text-sm">从下方选择卡牌添加</div>
                  )}
                </div>

                {renderDeckAnalysis(deck2Analysis)}
              </div>
            </div>

            <div className="flex gap-4 justify-center">
              <button
                onClick={handleSimulate}
                disabled={isSimulating || deck1.length === 0 || deck2.length === 0}
                className="px-8 py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-dark-900 font-cinzel font-bold rounded-lg hover:from-gold-500 hover:to-gold-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
              >
                {isSimulating ? (
                  <RotateCcw className="animate-spin" size={20} />
                ) : (
                  <Play size={20} />
                )}
                {isSimulating ? '模拟中...' : '开始对战'}
              </button>
              <button
                onClick={handleReset}
                className="px-6 py-3 bg-dark-700 text-parchment-200 rounded-lg hover:bg-dark-600 transition-colors flex items-center gap-2"
              >
                <RotateCcw size={20} />
                重置
              </button>
            </div>

            {message && (
              <div className={`p-4 rounded-lg text-center ${
                message.type === 'success'
                  ? 'bg-green-900/30 border border-green-500/30 text-green-400'
                  : 'bg-red-900/30 border border-red-500/30 text-red-400'
              }`}>
                {message.text}
              </div>
            )}

            {battleResult && (
              <div className="bg-dark-800 rounded-xl p-6 border border-dark-600">
                <div className="text-center mb-6">
                  <div className={`text-4xl font-cinzel font-bold ${
                    battleResult.winner === 'player1' 
                      ? 'text-blue-400' 
                      : battleResult.winner === 'player2' 
                      ? 'text-red-400' 
                      : 'text-yellow-400'
                  }`}>
                    {battleResult.winner === 'player1' ? '🏆 卡组 1 获胜！' 
                      : battleResult.winner === 'player2' ? '🏆 卡组 2 获胜！' 
                      : '⚔️ 平局！'}
                  </div>
                  <div className="text-parchment-200/50 mt-2">
                    共进行 {battleResult.turns} 回合
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-6 mb-6">
                  <div className="text-center">
                    <BarChart3 className="mx-auto text-blue-400 mb-2" size={24} />
                    <div className="text-sm text-parchment-200/50">卡组 1</div>
                    <div className="text-2xl font-bold text-parchment-100">
                      {battleResult.analysis.deck1Strength}
                    </div>
                    <div className="text-xs text-parchment-200/40">
                      造成伤害: {battleResult.stats.player1DamageDealt}
                    </div>
                  </div>
                  <div className="text-center">
                    <BarChart3 className="mx-auto text-red-400 mb-2" size={24} />
                    <div className="text-sm text-parchment-200/50">卡组 2</div>
                    <div className="text-2xl font-bold text-parchment-100">
                      {battleResult.analysis.deck2Strength}
                    </div>
                    <div className="text-xs text-parchment-200/40">
                      造成伤害: {battleResult.stats.player2DamageDealt}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="bg-dark-900/50 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-gold-500">{battleResult.stats.cardsPlayed}</div>
                    <div className="text-xs text-parchment-200/50">打出卡牌</div>
                  </div>
                  <div className="bg-dark-900/50 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-red-400">{battleResult.stats.cardsDestroyed}</div>
                    <div className="text-xs text-parchment-200/50">消灭卡牌</div>
                  </div>
                </div>

                {battleResult.analysis.keyMoments.length > 0 && (
                  <div className="mb-6">
                    <h3 className="font-cinzel text-parchment-100 mb-3">关键时刻</h3>
                    <div className="space-y-2">
                      {battleResult.analysis.keyMoments.map((moment, i) => (
                        <div key={i} className="p-2 bg-dark-900/30 rounded text-sm text-parchment-200/70">
                          ⚡ {moment}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <button
                  onClick={() => setShowLog(!showLog)}
                  className="w-full py-2 bg-dark-700 text-parchment-200 rounded-lg hover:bg-dark-600 transition-colors"
                >
                  {showLog ? '隐藏战斗日志' : '查看战斗日志'}
                </button>

                {showLog && (
                  <div className="mt-4 p-4 bg-dark-900 rounded-lg max-h-60 overflow-y-auto">
                    {battleResult.log.map((log, i) => (
                      <div key={i} className="text-sm text-parchment-200/60 py-1 border-b border-dark-700/50 last:border-0">
                        {log}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="bg-dark-800 rounded-xl p-4 border border-dark-600">
              <h2 className="font-cinzel text-lg text-parchment-100 mb-4">可用卡牌</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 max-h-[400px] overflow-y-auto pr-2">
                {cards.map((card) => {
                  const inDeck1 = deck1.includes(card.id);
                  const inDeck2 = deck2.includes(card.id);

                  return (
                    <div
                      key={card.id}
                      className={`p-3 rounded-lg border cursor-pointer transition-all ${
                        inDeck1
                          ? 'bg-blue-900/30 border-blue-500/50'
                          : inDeck2
                          ? 'bg-red-900/30 border-red-500/50'
                          : 'bg-dark-900/50 border-transparent hover:border-gold-500/30'
                      }`}
                    >
                      <div className="font-medium text-sm text-parchment-100">{card.name}</div>
                      <div className="text-xs text-parchment-200/50 mt-1">
                        {card.rarity} · 费用 {card.attributes.cost}
                      </div>
                      <div className="flex gap-2 mt-2 text-xs">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleCardInDeck(card.id, 1);
                          }}
                          className={`flex-1 py-1 rounded ${
                            inDeck1
                              ? 'bg-blue-600 text-white'
                              : 'bg-blue-900/30 text-blue-400 hover:bg-blue-900/50'
                          }`}
                          disabled={!inDeck1 && deck1.length >= 10}
                        >
                          {inDeck1 ? '移除' : '卡组1'}
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleCardInDeck(card.id, 2);
                          }}
                          className={`flex-1 py-1 rounded ${
                            inDeck2
                              ? 'bg-red-600 text-white'
                              : 'bg-red-900/30 text-red-400 hover:bg-red-900/50'
                          }`}
                          disabled={!inDeck2 && deck2.length >= 10}
                        >
                          {inDeck2 ? '移除' : '卡组2'}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-dark-800 rounded-xl p-4 border border-dark-600">
              <h3 className="font-cinzel text-parchment-100 mb-4">模拟说明</h3>
              <div className="space-y-3 text-sm text-parchment-200/60">
                <div className="flex items-start gap-2">
                  <span className="text-gold-500">1.</span>
                  <span>为卡组1和卡组2各选择1-10张卡牌</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-gold-500">2.</span>
                  <span>系统会自动分析卡组强度和协同性</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-gold-500">3.</span>
                  <span>点击"开始对战"进行模拟对战</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-gold-500">4.</span>
                  <span>查看对战结果和关键时刻</span>
                </div>
              </div>
            </div>

            <div className="bg-dark-800 rounded-xl p-4 border border-dark-600">
              <h3 className="font-cinzel text-parchment-100 mb-4">对战规则</h3>
              <div className="space-y-2 text-xs text-parchment-200/50">
                <p>• 双方各有30点生命值</p>
                <p>• 每回合法力值上限+1（最高10）</p>
                <p>• 每回合自动抽一张牌</p>
                <p>• 场上最多5张卡牌</p>
                <p>• 攻击时先攻击敌方卡牌</p>
                <p>• 敌方无卡牌时直接攻击英雄</p>
                <p>• 最多进行30回合</p>
              </div>
            </div>

            <div className="bg-dark-800 rounded-xl p-4 border border-gold-500/30">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="text-gold-500" size={18} />
                <h3 className="font-cinzel text-gold-500">分析指标</h3>
              </div>
              <div className="space-y-2 text-xs text-parchment-200/60">
                <p><span className="text-gold-500">卡组强度</span>：卡牌平均战力值</p>
                <p><span className="text-gold-500">协同评分</span>：费用曲线和类型搭配</p>
                <p><span className="text-gold-500">费用曲线</span>：低费保证前期节奏</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
