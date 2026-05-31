
import type { CardData, AICardRequest, BalanceAnalysis } from '../types/index.js';

const SKILL_NAMES_BY_TYPE: Record<string, string[]> = {
  attack: ['猛击', '连续攻击', '致命一击', '狂暴打击', '穿刺', '破甲', '旋风斩', '突袭'],
  defense: ['格挡', '铁壁', '坚守', '嘲讽', '护盾', '反击姿态', '坚不可摧', '壁垒'],
  magic: ['火球术', '闪电链', '冰霜新星', '暗影箭', '奥术飞弹', '元素爆发', '魔法飞弹', '精神冲击'],
  support: ['治疗术', '祝福', '净化', '强化', '庇护', '生命源泉', '能量注入', '群体护盾'],
};

const SKILL_DESCRIPTIONS: Record<string, string[]> = {
  attack: [
    '造成{0}点伤害',
    '对目标造成{0}点物理伤害',
    '攻击时有{1}%概率暴击',
    '无视{2}点护甲',
  ],
  defense: [
    '增加{0}点护甲',
    '受到伤害减少{1}%',
    '嘲讽所有敌方单位',
    '反弹{2}%受到的伤害',
  ],
  magic: [
    '造成{0}点魔法伤害',
    '有{1}%概率使目标眩晕',
    '降低目标{2}点攻击力',
    '对所有敌人造成{0}点伤害',
  ],
  support: [
    '恢复{0}点生命值',
    '增加友方{1}点攻击力',
    '净化一个负面效果',
    '使目标获得护盾吸收{2}点伤害',
  ],
};

const CARD_NAMES_BY_STYLE: Record<string, string[]> = {
  fantasy: ['暗影', '圣光', '巨龙', '精灵', '法师', '骑士', '游侠', '死灵', '元素', '远古'],
  'sci-fi': ['机甲', '量子', '能量', '机械', '纳米', '全息', '赛博', '星际', '泰坦', '先锋'],
  minimal: ['守卫', '战士', '法师', '弓手', '刺客', '牧师', '骑士', '巨人', '精灵', '龙'],
  classic: ['战士', '法师', '牧师', '盗贼', '猎人', '萨满', '圣骑士', '术士', '德鲁伊', '死亡骑士'],
};

const ELEMENTS = ['fire', 'water', 'earth', 'wind', 'light', 'dark'];

const TYPES: Array<'attack' | 'defense' | 'magic' | 'support'> = ['attack', 'defense', 'magic', 'support'];

const RARITY_MULTIPLIERS: Record<string, number> = {
  common: 1,
  rare: 1.3,
  epic: 1.6,
  legendary: 2,
};

const TEMPLATE_BY_STYLE: Record<string, string> = {
  fantasy: 'template-dark-fantasy',
  'sci-fi': 'template-sci-fi',
  minimal: 'template-minimal',
  classic: 'template-classic',
};

function seededRandom(seed: number): number {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

function pickRandom<T>(arr: T[], seed: number): T {
  return arr[Math.floor(seededRandom(seed) * arr.length)];
}

function analyzeDescription(description: string): {
  typeHint?: string;
  elementHint?: string;
  rarityHint?: string;
  keywords: string[];
} {
  const lowerDesc = description.toLowerCase();
  const keywords: string[] = [];
  
  let typeHint: string | undefined;
  let elementHint: string | undefined;
  let rarityHint: string | undefined;

  if (lowerDesc.includes('攻击') || lowerDesc.includes('战士') || lowerDesc.includes('输出')) {
    typeHint = 'attack';
    keywords.push('attack');
  }
  if (lowerDesc.includes('防御') || lowerDesc.includes('坦克') || lowerDesc.includes('守护')) {
    typeHint = 'defense';
    keywords.push('defense');
  }
  if (lowerDesc.includes('魔法') || lowerDesc.includes('法师') || lowerDesc.includes('法术')) {
    typeHint = 'magic';
    keywords.push('magic');
  }
  if (lowerDesc.includes('治疗') || lowerDesc.includes('辅助') || lowerDesc.includes('支援')) {
    typeHint = 'support';
    keywords.push('support');
  }

  if (lowerDesc.includes('火') || lowerDesc.includes('炎')) elementHint = 'fire';
  if (lowerDesc.includes('水') || lowerDesc.includes('冰')) elementHint = 'water';
  if (lowerDesc.includes('土') || lowerDesc.includes('岩')) elementHint = 'earth';
  if (lowerDesc.includes('风') || lowerDesc.includes('雷')) elementHint = 'wind';
  if (lowerDesc.includes('光') || lowerDesc.includes('圣')) elementHint = 'light';
  if (lowerDesc.includes('暗') || lowerDesc.includes('影')) elementHint = 'dark';

  if (lowerDesc.includes('传说') || lowerDesc.includes('神话') || lowerDesc.includes('终极')) rarityHint = 'legendary';
  if (lowerDesc.includes('史诗') || lowerDesc.includes('稀有') || lowerDesc.includes('高级')) rarityHint = 'epic';
  if (lowerDesc.includes('精良') || lowerDesc.includes('优秀')) rarityHint = 'rare';
  if (lowerDesc.includes('普通') || lowerDesc.includes('基础')) rarityHint = 'common';

  return { typeHint, elementHint, rarityHint, keywords };
}

function generateCardName(description: string, style: string, seed: number): string {
  const styleNames = CARD_NAMES_BY_STYLE[style] || CARD_NAMES_BY_STYLE.classic;
  const prefix = pickRandom(styleNames, seed);
  const suffix = pickRandom(styleNames, seed + 1000);
  
  const words = description.split(/[，。！？,.\s]+/).filter(w => w.length > 0);
  if (words.length > 0 && words[0].length <= 6) {
    return words[0];
  }
  
  return prefix + suffix;
}

function generateSkills(
  type: string,
  rarity: string,
  seed: number
): Array<{ name: string; description: string; tags: string[]; icon: string }> {
  const multiplier = RARITY_MULTIPLIERS[rarity] || 1;
  const skillCount = rarity === 'legendary' ? 3 : rarity === 'epic' ? 2 : 1;
  
  const skills: Array<{ name: string; description: string; tags: string[]; icon: string }> = [];
  const skillNames = SKILL_NAMES_BY_TYPE[type] || SKILL_NAMES_BY_TYPE.attack;
  const skillDescs = SKILL_DESCRIPTIONS[type] || SKILL_DESCRIPTIONS.attack;

  for (let i = 0; i < skillCount; i++) {
    const skillSeed = seed + i * 100;
    const name = pickRandom(skillNames, skillSeed);
    const descTemplate = pickRandom(skillDescs, skillSeed + 50);
    
    const damage = Math.floor((10 + seededRandom(skillSeed + 10) * 10) * multiplier);
    const chance = Math.floor(20 + seededRandom(skillSeed + 20) * 30);
    const armor = Math.floor((3 + seededRandom(skillSeed + 30) * 5) * multiplier);
    
    const description = descTemplate
      .replace('{0}', String(damage))
      .replace('{1}', String(chance))
      .replace('{2}', String(armor));

    skills.push({
      name,
      description,
      tags: [type],
      icon: type,
    });
  }

  return skills;
}

function generateAttributes(
  type: string,
  rarity: string,
  seed: number
): { attack: number; defense: number; health: number; cost: number } {
  const multiplier = RARITY_MULTIPLIERS[rarity] || 1;
  const baseCost = Math.floor(2 + seededRandom(seed) * 6 * multiplier);
  
  let attack = 3;
  let defense = 3;
  let health = 5;

  switch (type) {
    case 'attack':
      attack = Math.floor((6 + seededRandom(seed + 1) * 4) * multiplier);
      defense = Math.floor((2 + seededRandom(seed + 2) * 3) * multiplier);
      health = Math.floor((6 + seededRandom(seed + 3) * 4) * multiplier);
      break;
    case 'defense':
      attack = Math.floor((2 + seededRandom(seed + 1) * 3) * multiplier);
      defense = Math.floor((6 + seededRandom(seed + 2) * 4) * multiplier);
      health = Math.floor((10 + seededRandom(seed + 3) * 5) * multiplier);
      break;
    case 'magic':
      attack = Math.floor((5 + seededRandom(seed + 1) * 4) * multiplier);
      defense = Math.floor((2 + seededRandom(seed + 2) * 2) * multiplier);
      health = Math.floor((5 + seededRandom(seed + 3) * 3) * multiplier);
      break;
    case 'support':
      attack = Math.floor((3 + seededRandom(seed + 1) * 2) * multiplier);
      defense = Math.floor((4 + seededRandom(seed + 2) * 3) * multiplier);
      health = Math.floor((8 + seededRandom(seed + 3) * 4) * multiplier);
      break;
  }

  return {
    attack: Math.max(1, Math.min(15, attack)),
    defense: Math.max(1, Math.min(15, defense)),
    health: Math.max(3, Math.min(20, health)),
    cost: Math.max(1, Math.min(10, baseCost)),
  };
}

function generateDescription(type: string, rarity: string, element?: string): string {
  const typeDesc: Record<string, string> = {
    attack: '勇猛的战士，擅长近身格斗',
    defense: '坚韧的守护者，保护队友免受伤害',
    magic: '神秘的法师，操控元素之力',
    support: '仁慈的治疗者，支援队友恢复力量',
  };

  const elementDesc: Record<string, string> = {
    fire: '，操控烈焰的力量',
    water: '，掌控寒冰与流水',
    earth: '，与大地融为一体',
    wind: '，如风一般迅捷',
    light: '，沐浴在神圣光芒中',
    dark: '，被暗影之力环绕',
  };

  const rarityDesc: Record<string, string> = {
    common: '',
    rare: '，实力出众',
    epic: '，拥有强大的力量',
    legendary: '，传说中的存在',
  };

  return (typeDesc[type] || typeDesc.attack) + (elementDesc[element || ''] || '') + (rarityDesc[rarity] || '') + '。';
}

function generateFlavorText(style: string, seed: number): string {
  const texts = [
    '在古老的传说中，它曾改变过战争的走向。',
    '它的故事被吟游诗人们世代传唱。',
    '只有真正的勇者才能驾驭这份力量。',
    '每一次挥击，都蕴含着远古的意志。',
    '命运的齿轮因它而转动。',
  ];
  return pickRandom(texts, seed);
}

export function generateAICard(request: AICardRequest): Omit<CardData, 'id' | 'createdAt' | 'updatedAt'> {
  const { description, style = 'fantasy', rarity: reqRarity, type: reqType } = request;
  
  const seed = description.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const analysis = analyzeDescription(description);
  
  const type = reqType || analysis.typeHint || pickRandom(TYPES, seed);
  const rarity = reqRarity || analysis.rarityHint || 'common';
  const element = analysis.elementHint || pickRandom(ELEMENTS, seed + 500);
  const templateId = TEMPLATE_BY_STYLE[style] || TEMPLATE_BY_STYLE.fantasy;

  const name = generateCardName(description, style, seed);
  const attributes = generateAttributes(type, rarity, seed);
  const skills = generateSkills(type, rarity, seed);
  const cardDescription = generateDescription(type, rarity, element);
  const flavorText = generateFlavorText(style, seed + 2000);

  return {
    name,
    type: type as CardData['type'],
    rarity: rarity as CardData['rarity'],
    element: element as CardData['element'],
    attributes,
    skills,
    description: cardDescription,
    flavorText,
    templateId,
  };
}

export function analyzeCardBalance(card: CardData): BalanceAnalysis {
  const issues: BalanceAnalysis['issues'] = [];
  let score = 100;

  const { attributes, rarity, skills, type } = card;
  const multiplier = RARITY_MULTIPLIERS[rarity] || 1;

  const expectedAttack = 5 * multiplier;
  const expectedDefense = 4 * multiplier;
  const expectedHealth = 7 * multiplier;
  const expectedCost = 4 * multiplier;

  if (attributes.attack > expectedAttack * 1.5) {
    issues.push({
      type: 'warning',
      category: '属性',
      message: `攻击力过高: ${attributes.attack} (预期约 ${Math.round(expectedAttack)})`,
      suggestion: '考虑降低攻击力或增加费用',
    });
    score -= 10;
  }
  if (attributes.attack < expectedAttack * 0.5) {
    issues.push({
      type: 'warning',
      category: '属性',
      message: `攻击力过低: ${attributes.attack} (预期约 ${Math.round(expectedAttack)})`,
      suggestion: '考虑增加攻击力',
    });
    score -= 5;
  }

  if (attributes.defense > expectedDefense * 1.5) {
    issues.push({
      type: 'warning',
      category: '属性',
      message: `防御力过高: ${attributes.defense} (预期约 ${Math.round(expectedDefense)})`,
      suggestion: '考虑降低防御力或增加费用',
    });
    score -= 10;
  }

  if (attributes.health > expectedHealth * 1.5) {
    issues.push({
      type: 'error',
      category: '属性',
      message: `生命值过高: ${attributes.health} (预期约 ${Math.round(expectedHealth)})`,
      suggestion: '强烈建议降低生命值',
    });
    score -= 15;
  }

  if (attributes.cost < expectedCost * 0.5 && attributes.attack + attributes.defense + attributes.health > 15) {
    issues.push({
      type: 'error',
      category: '费用',
      message: '费用效率过高，属性强大但费用太低',
      suggestion: '需要增加费用或削弱属性',
    });
    score -= 20;
  }

  const expectedSkillCount = rarity === 'legendary' ? 3 : rarity === 'epic' ? 2 : 1;
  if (skills.length > expectedSkillCount) {
    issues.push({
      type: 'warning',
      category: '技能',
      message: `技能数量过多: ${skills.length} (${rarity} 通常最多 ${expectedSkillCount} 个)`,
      suggestion: '考虑减少技能数量',
    });
    score -= 8;
  }

  if (type === 'defense' && attributes.defense < 3) {
    issues.push({
      type: 'info',
      category: '类型',
      message: '防御型卡牌防御力偏低',
      suggestion: '考虑增加防御力以符合卡牌定位',
    });
  }
  if (type === 'attack' && attributes.attack < 4) {
    issues.push({
      type: 'info',
      category: '类型',
      message: '攻击型卡牌攻击力偏低',
      suggestion: '考虑增加攻击力以符合卡牌定位',
    });
  }

  const totalPower = attributes.attack + attributes.defense + attributes.health / 2;
  const costEfficiency = totalPower / Math.max(1, attributes.cost);

  const attributeDistribution = {
    attack: attributes.attack,
    defense: attributes.defense,
    health: attributes.health,
    cost: attributes.cost,
  };

  const skillPower = skills.length * 10 + skills.reduce((sum, s) => {
    const match = s.description.match(/\d+/);
    return sum + (match ? parseInt(match[0]) : 5);
  }, 0);

  const rarityScore = rarity === 'legendary' ? 100 : rarity === 'epic' ? 75 : rarity === 'rare' ? 50 : 25;

  let grade: BalanceAnalysis['grade'] = 'C';
  if (score >= 90) grade = 'S';
  else if (score >= 80) grade = 'A';
  else if (score >= 70) grade = 'B';
  else if (score >= 60) grade = 'C';
  else if (score >= 50) grade = 'D';
  else grade = 'F';

  const recommendations: string[] = [];
  if (score < 70) {
    recommendations.push('建议重新平衡这张卡牌的数值');
  }
  if (costEfficiency > 5) {
    recommendations.push('费用效率过高，可能需要增加费用');
  }
  if (totalPower < 10) {
    recommendations.push('总体战力偏低，考虑增强属性');
  }
  if (recommendations.length === 0) {
    recommendations.push('这张卡牌的平衡性良好');
  }

  return {
    score: Math.max(0, score),
    grade,
    issues,
    stats: {
      totalPower,
      costEfficiency,
      attributeDistribution,
      skillPower,
      rarityScore,
    },
    recommendations,
  };
}
