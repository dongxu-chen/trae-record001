
import type { CardData, BattleCard, BattleState, BattleResult, DeckAnalysis } from '../types/index.js';

function shuffle<T>(array: T[]): T[] {
  const result = [...array];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

function createBattleCard(card: CardData): BattleCard {
  return {
    ...card,
    currentHealth: card.attributes.health,
    buffs: [],
    debuffs: [],
  };
}

function calculateCardPower(card: CardData): number {
  const attributes = card.attributes || { attack: 0, defense: 0, health: 0, cost: 1 };
  const skills = card.skills || [];
  const rarity = card.rarity || 'common';
  
  const rarityMultiplier = rarity === 'legendary' ? 2 : rarity === 'epic' ? 1.6 : rarity === 'rare' ? 1.3 : 1;
  
  let skillPower = 0;
  for (const skill of skills) {
    const match = skill.description?.match(/\d+/);
    skillPower += match ? parseInt(match[0]) : 5;
  }
  
  const attack = attributes.attack || 0;
  const defense = attributes.defense || 0;
  const health = attributes.health || 0;
  const cost = Math.max(1, attributes.cost || 1);
  
  const basePower = attack * 2 + defense * 1.5 + health + skillPower;
  return basePower * rarityMultiplier / cost;
}

function applyDamage(target: BattleCard, damage: number): number {
  const actualDamage = Math.max(0, damage - target.attributes.defense);
  target.currentHealth -= actualDamage;
  return actualDamage;
}

export function simulateBattle(
  deck1Cards: CardData[],
  deck2Cards: CardData[],
  maxTurns: number = 30
): BattleResult {
  const log: string[] = [];
  const keyMoments: string[] = [];
  
  let player1DamageDealt = 0;
  let player2DamageDealt = 0;
  let cardsPlayed = 0;
  let cardsDestroyed = 0;

  const deck1 = shuffle(deck1Cards.map(c => c.id));
  const deck2 = shuffle(deck2Cards.map(c => c.id));

  const cardMap: Record<string, CardData> = {};
  for (const card of [...deck1Cards, ...deck2Cards]) {
    cardMap[card.id] = card;
  }

  const state: BattleState = {
    turn: 1,
    phase: 'draw',
    player1: {
      deck: deck1.slice(3),
      hand: deck1.slice(0, 3),
      field: [],
      graveyard: [],
      health: 30,
      mana: 1,
      maxMana: 1,
    },
    player2: {
      deck: deck2.slice(3),
      hand: deck2.slice(0, 3),
      field: [],
      graveyard: [],
      health: 30,
      mana: 1,
      maxMana: 1,
    },
    log: [],
  };

  log.push('⚔️ 战斗开始！');
  log.push(`玩家1卡组: ${deck1Cards.length}张卡牌`);
  log.push(`玩家2卡组: ${deck2Cards.length}张卡牌`);

  let currentPlayer: 'player1' | 'player2' = 'player1';

  while (state.turn <= maxTurns) {
    const player = state[currentPlayer];
    const opponent = currentPlayer === 'player1' ? state.player2 : state.player1;

    state.phase = 'draw';
    if (player.deck.length > 0) {
      const drawnCard = player.deck.shift()!;
      player.hand.push(drawnCard);
      log.push(`回合${state.turn} - ${currentPlayer === 'player1' ? '玩家1' : '玩家2'} 抽牌`);
    }

    player.maxMana = Math.min(10, player.maxMana + 1);
    player.mana = player.maxMana;

    state.phase = 'main';
    let playedCardThisTurn = false;
    for (let i = player.hand.length - 1; i >= 0; i--) {
      const cardId = player.hand[i];
      const card = cardMap[cardId];
      if (card && card.attributes.cost <= player.mana && player.field.length < 5) {
        player.hand.splice(i, 1);
        player.field.push(createBattleCard(card));
        player.mana -= card.attributes.cost;
        playedCardThisTurn = true;
        cardsPlayed++;
        log.push(`${currentPlayer === 'player1' ? '玩家1' : '玩家2'} 打出 ${card.name} (费用:${card.attributes.cost})`);
        
        if (card.rarity === 'legendary') {
          keyMoments.push(`回合${state.turn}: ${currentPlayer === 'player1' ? '玩家1' : '玩家2'} 打出传说卡牌 ${card.name}`);
        }
      }
    }

    if (!playedCardThisTurn && player.hand.length > 0) {
      const cardId = player.hand[0];
      const card = cardMap[cardId];
      if (card) {
        log.push(`${currentPlayer === 'player1' ? '玩家1' : '玩家2'} 无法打出 ${card.name} (费用不足)`);
      }
    }

    state.phase = 'battle';
    for (const attacker of player.field) {
      if (opponent.field.length > 0) {
        const targetIndex = Math.floor(Math.random() * opponent.field.length);
        const target = opponent.field[targetIndex];
        const damage = applyDamage(target, attacker.attributes.attack);
        if (currentPlayer === 'player1') player1DamageDealt += damage;
        else player2DamageDealt += damage;
        
        log.push(`${attacker.name} 攻击 ${target.name}，造成 ${damage} 点伤害`);
        
        if (target.currentHealth <= 0) {
          opponent.field.splice(targetIndex, 1);
          opponent.graveyard.push(target.id);
          cardsDestroyed++;
          log.push(`💀 ${target.name} 被消灭！`);
          
          if (target.rarity === 'legendary') {
            keyMoments.push(`回合${state.turn}: ${target.name} 被消灭！`);
          }
        }
      } else {
        const damage = Math.max(1, attacker.attributes.attack - 2);
        opponent.health -= damage;
        if (currentPlayer === 'player1') player1DamageDealt += damage;
        else player2DamageDealt += damage;
        
        log.push(`${attacker.name} 直接攻击对手，造成 ${damage} 点伤害！`);
        
        if (opponent.health <= 10 && opponent.health > 0) {
          keyMoments.push(`回合${state.turn}: ${currentPlayer === 'player1' ? '玩家2' : '玩家1'} 生命值危急！(${opponent.health}点)`);
        }
      }
    }

    if (state.player1.health <= 0 || state.player2.health <= 0) {
      break;
    }

    state.phase = 'end';
    currentPlayer = currentPlayer === 'player1' ? 'player2' : 'player1';
    if (currentPlayer === 'player1') {
      state.turn++;
    }
  }

  let winner: 'player1' | 'player2' | 'draw' = 'draw';
  if (state.player1.health <= 0 && state.player2.health > 0) {
    winner = 'player2';
    log.push('🏆 玩家2获胜！');
  } else if (state.player2.health <= 0 && state.player1.health > 0) {
    winner = 'player1';
    log.push('🏆 玩家1获胜！');
  } else if (state.player1.health > state.player2.health) {
    winner = 'player1';
    log.push('⏰ 时间到！玩家1生命值更高，获胜！');
  } else if (state.player2.health > state.player1.health) {
    winner = 'player2';
    log.push('⏰ 时间到！玩家2生命值更高，获胜！');
  } else {
    log.push('⏰ 时间到！平局！');
  }

  const deck1Strength = Math.round(deck1Cards.reduce((sum, c) => sum + calculateCardPower(c), 0) / deck1Cards.length);
  const deck2Strength = Math.round(deck2Cards.reduce((sum, c) => sum + calculateCardPower(c), 0) / deck2Cards.length);

  return {
    winner,
    turns: state.turn,
    log,
    stats: {
      player1DamageDealt,
      player2DamageDealt,
      cardsPlayed,
      cardsDestroyed,
    },
    analysis: {
      deck1Strength,
      deck2Strength,
      keyMoments: keyMoments.slice(0, 5),
    },
  };
}

export function analyzeDeck(cards: CardData[]): DeckAnalysis {
  if (cards.length === 0) {
    return {
      deckStrength: 0,
      curve: [],
      typeDistribution: {},
      rarityDistribution: {},
      recommendations: ['卡组为空，请添加卡牌'],
      synergyScore: 0,
    };
  }

  const curve: Array<{ cost: number; count: number }> = [];
  const typeDistribution: Record<string, number> = {};
  const rarityDistribution: Record<string, number> = {};

  for (let i = 1; i <= 10; i++) {
    curve.push({ cost: i, count: 0 });
  }

  for (const card of cards) {
    const costIndex = card.attributes.cost - 1;
    if (costIndex >= 0 && costIndex < 10) {
      curve[costIndex].count++;
    }

    typeDistribution[card.type] = (typeDistribution[card.type] || 0) + 1;
    rarityDistribution[card.rarity] = (rarityDistribution[card.rarity] || 0) + 1;
  }

  const totalPower = cards.reduce((sum, c) => sum + calculateCardPower(c), 0);
  const deckStrength = Math.round(totalPower / cards.length);

  const recommendations: string[] = [];
  const lowCostCards = curve.filter(c => c.cost <= 2).reduce((s, c) => s + c.count, 0);
  const midCostCards = curve.filter(c => c.cost >= 3 && c.cost <= 5).reduce((s, c) => s + c.count, 0);
  const highCostCards = curve.filter(c => c.cost >= 6).reduce((s, c) => s + c.count, 0);

  if (cards.length < 20) {
    recommendations.push(`卡组数量较少 (${cards.length}张)，建议增加到20-30张`);
  }
  if (lowCostCards < cards.length * 0.25) {
    recommendations.push('低费卡牌(1-2费)较少，建议增加一些以保证前期节奏');
  }
  if (highCostCards > cards.length * 0.3) {
    recommendations.push('高费卡牌(6+费)较多，可能导致前期卡手');
  }
  if (typeDistribution['attack'] === undefined) {
    recommendations.push('卡组中缺少攻击型卡牌，建议添加');
  }
  if (typeDistribution['defense'] === undefined) {
    recommendations.push('卡组中缺少防御型卡牌，建议添加');
  }
  if (midCostCards >= cards.length * 0.4 && lowCostCards >= cards.length * 0.2) {
    recommendations.push('费用曲线良好，前期和中期都有足够的选择');
  }

  let synergyScore = 50;
  if (lowCostCards >= cards.length * 0.2 && midCostCards >= cards.length * 0.3) {
    synergyScore += 15;
  }
  if (Object.keys(typeDistribution).length >= 3) {
    synergyScore += 10;
  }
  if (cards.length >= 20 && cards.length <= 30) {
    synergyScore += 10;
  }
  if (rarityDistribution['legendary'] && rarityDistribution['legendary'] > cards.length * 0.15) {
    synergyScore += 15;
  }
  synergyScore = Math.min(100, synergyScore);

  return {
    deckStrength,
    curve,
    typeDistribution,
    rarityDistribution,
    recommendations: recommendations.length > 0 ? recommendations : ['卡组构建良好！'],
    synergyScore,
  };
}
