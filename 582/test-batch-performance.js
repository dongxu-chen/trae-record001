
const now = new Date().toISOString();

const sampleCards = [
  {
    id: 'card-shadow-dragon',
    name: '暗影龙',
    type: 'attack',
    rarity: 'legendary',
    element: 'dark',
    attributes: { attack: 9, defense: 3, health: 7, cost: 8 },
    skills: [
      { name: '暗影吐息', description: '对所有敌方单位造成3点暗影伤害', tags: ['aoe', 'dark'], icon: 'breath' },
      { name: '恐惧光环', description: '降低相邻敌方单位2点攻击力', tags: ['aura', 'debuff'], icon: 'fear' },
    ],
    description: '从深渊中苏醒的远古巨龙，它的吐息能吞噬一切光明。',
    flavorText: '当最后一片阴影降临，暗影龙便会展翅飞翔。',
    templateId: 'template-dark-fantasy',
    createdAt: now,
    updatedAt: now,
  },
  {
    id: 'card-ice-mage',
    name: '寒冰法师',
    type: 'magic',
    rarity: 'rare',
    element: 'water',
    attributes: { attack: 5, defense: 4, health: 5, cost: 5 },
    skills: [
      { name: '冰霜新星', description: '冻结目标单位1回合', tags: ['freeze', 'control'], icon: 'frost' },
    ],
    description: '掌控寒冰之力的法师，能将敌人的血液化为冰晶。',
    flavorText: '在她的世界里，时间如同被冻结的河流。',
    templateId: 'template-dark-fantasy',
    createdAt: now,
    updatedAt: now,
  },
  {
    id: 'card-mech-warrior',
    name: '机甲战士',
    type: 'attack',
    rarity: 'epic',
    element: 'earth',
    attributes: { attack: 7, defense: 6, health: 8, cost: 7 },
    skills: [
      { name: '超载打击', description: '下一次攻击造成双倍伤害', tags: ['buff', 'damage'], icon: 'overload' },
      { name: '铁壁', description: '本回合防御力+3', tags: ['buff', 'defense'], icon: 'shield' },
    ],
    description: '融合了最尖端科技的战斗机器，火力与防御兼备。',
    flavorText: '钢铁之躯，不屈之心。',
    templateId: 'template-sci-fi',
    createdAt: now,
    updatedAt: now,
  },
  {
    id: 'card-hologram',
    name: '全息幻影',
    type: 'support',
    rarity: 'rare',
    attributes: { attack: 1, defense: 2, health: 3, cost: 3 },
    skills: [
      { name: '数据干扰', description: '使目标技能冷却+1', tags: ['debuff', 'tech'], icon: 'glitch' },
    ],
    description: '虚拟世界中诞生的数字生命，能操纵信息流干扰对手。',
    flavorText: '0和1之间，藏着无限可能。',
    templateId: 'template-sci-fi',
    createdAt: now,
    updatedAt: now,
  },
  {
    id: 'card-wind-runner',
    name: '疾风行者',
    type: 'defense',
    rarity: 'common',
    element: 'wind',
    attributes: { attack: 3, defense: 5, health: 4, cost: 3 },
    skills: [
      { name: '闪避', description: '有30%概率闪避攻击', tags: ['evasion', 'passive'], icon: 'dodge' },
    ],
    description: '随风而行的游侠，身形如风般难以捉摸。',
    flavorText: '你抓不住风，就像抓不住明天。',
    templateId: 'template-minimal',
    createdAt: now,
    updatedAt: now,
  },
  {
    id: 'card-holy-knight',
    name: '圣光骑士',
    type: 'defense',
    rarity: 'epic',
    element: 'light',
    attributes: { attack: 4, defense: 8, health: 9, cost: 6 },
    skills: [
      { name: '神圣护盾', description: '为友方单位施加2点护盾', tags: ['shield', 'holy'], icon: 'shield' },
      { name: '审判之光', description: '对暗属性敌人造成额外4点伤害', tags: ['damage', 'holy'], icon: 'smite' },
    ],
    description: '誓守光明的圣骑士，以正义之盾守护同伴。',
    flavorText: '光明不灭，誓言永存。',
    templateId: 'template-classic',
    createdAt: now,
    updatedAt: now,
  },
];

function generateTestCards(count) {
  const cards = [];
  for (let i = 0; i < count; i++) {
    const baseCard = sampleCards[i % sampleCards.length];
    cards.push({
      ...baseCard,
      id: `test-card-${i}`,
      name: `${baseCard.name} #${i + 1}`,
      createdAt: now,
      updatedAt: now,
    });
  }
  return cards;
}

async function testBatchGeneration() {
  const cardCount = 50;
  const testCards = generateTestCards(cardCount);
  
  console.log(`\n🚀 开始测试 ${cardCount} 张卡牌批量生成...`);
  console.log(`并发数: 12`);
  console.log(`目标时间: 10秒内\n`);
  
  const startTime = Date.now();
  
  try {
    const response = await fetch('http://localhost:3001/api/export/generate/batch', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ cards: testCards }),
    });
    
    const endTime = Date.now();
    const duration = (endTime - startTime) / 1000;
    
    const result = await response.json();
    
    console.log('📊 测试结果:');
    console.log('────────────────────────────────');
    console.log(`✅ 成功生成: ${result.count} 张卡牌`);
    console.log(`⏱️  服务器耗时: ${result.duration}`);
    console.log(`⏱️  总耗时(含网络): ${duration.toFixed(2)}s`);
    console.log(`⚡ 平均每张: ${(duration / cardCount * 1000).toFixed(2)}ms`);
    console.log(`🎯 目标达成: ${duration <= 10 ? '✅ 是' : '❌ 否'}`);
    console.log('────────────────────────────────\n');
    
    if (result.success && duration <= 10) {
      console.log('🎉 性能测试通过！批量生成速度达到10秒内目标！');
    } else {
      console.log('⚠️  性能测试未通过，需要优化。');
    }
    
    return result.success && duration <= 10;
  } catch (error) {
    console.error('❌ 测试失败:', error.message);
    return false;
  }
}

testBatchGeneration();
