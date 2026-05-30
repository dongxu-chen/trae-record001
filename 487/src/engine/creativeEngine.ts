import { IconStyle, IconConfig } from './types';

export interface CreativeSuggestion {
  id: string;
  name: string;
  description: string;
  config: Partial<IconConfig>;
  keywords: string[];
  tags: string[];
  animationHint?: string;
  usageContext?: string;
}

export interface CreativeResult {
  suggestions: CreativeSuggestion[];
  primaryColor: string;
  secondaryColor: string;
  recommendedStyle: IconStyle;
  mood: string;
  description: string;
}

export const creativePalette: Record<string, { primary: string; secondary: string; mood: string }> = {
  tech: { primary: '#3b82f6', secondary: '#8b5cf6', mood: '科技感' },
  nature: { primary: '#10b981', secondary: '#059669', mood: '自然清新' },
  warm: { primary: '#f59e0b', secondary: '#ef4444', mood: '温暖热情' },
  cool: { primary: '#06b6d4', secondary: '#3b82f6', mood: '冷静专业' },
  creative: { primary: '#ec4899', secondary: '#f59e0b', mood: '创意活力' },
  professional: { primary: '#1e40af', secondary: '#374151', mood: '专业稳重' },
  playful: { primary: '#f97316', secondary: '#eab308', mood: '活泼有趣' },
  elegant: { primary: '#7c3aed', secondary: '#db2777', mood: '优雅精致' },
  minimal: { primary: '#111827', secondary: '#6b7280', mood: '极简现代' },
  energetic: { primary: '#22c55e', secondary: '#84cc16', mood: '充满活力' },
};

export const styleKeywords: Record<IconStyle, string[]> = {
  outline: ['简洁', '线框', '极简', '现代', '清晰', '科技', '文档', 'UI'],
  filled: ['稳重', '填充', '实体', '稳重', '标志', '品牌', '专业', '商务'],
  gradient: ['活力', '渐变', '炫彩', '流行', 'App', '年轻化', '创意', '音乐'],
  '3d': ['立体', '3D', '游戏', '玩具', '活泼', '趣味', '儿童', '娱乐'],
};

export const creativeSuggestions: CreativeSuggestion[] = [
  {
    id: '1',
    name: '科技公司Logo',
    description: '适合科技公司、互联网产品的简洁标志设计',
    config: { style: 'filled', primaryColor: '#3b82f6', secondaryColor: '#8b5cf6', borderRadius: 16, padding: 28 },
    keywords: ['科技', '互联网', '软件', 'App', 'AI', '数据', '云', '技术'],
    tags: ['商务', '专业', '现代'],
    animationHint: '呼吸效果 + 渐变流动',
    usageContext: 'App图标、网站Logo、名片',
  },
  {
    id: '2',
    name: '自然环保主题',
    description: '适合环保、健康、有机食品相关品牌',
    config: { style: 'outline', primaryColor: '#10b981', secondaryColor: '#059669', borderRadius: 999, padding: 24 },
    keywords: ['环保', '自然', '健康', '绿色', '有机', '植物', '生态', '森林'],
    tags: ['清新', '健康', '有机'],
    animationHint: '叶片摇摆 + 生长动画',
    usageContext: '产品包装、宣传物料',
  },
  {
    id: '3',
    name: '创意工作室',
    description: '适合设计工作室、广告公司、创意团队',
    config: { style: 'gradient', primaryColor: '#ec4899', secondaryColor: '#f59e0b', borderRadius: 20, padding: 32 },
    keywords: ['设计', '创意', '艺术', '工作室', '广告', '品牌', '插画', '摄影'],
    tags: ['活力', '创意', '艺术'],
    animationHint: '色彩流动 + 旋转出现',
    usageContext: '作品集封面、社交媒体头像',
  },
  {
    id: '4',
    name: '游戏娱乐',
    description: '适合游戏、娱乐、休闲应用',
    config: { style: '3d', primaryColor: '#f59e0b', secondaryColor: '#ef4444', borderRadius: 24, padding: 20 },
    keywords: ['游戏', '娱乐', '玩具', '儿童', '休闲', '电竞', '直播', '视频'],
    tags: ['有趣', '活泼', '动感'],
    animationHint: '弹跳 + 旋转 + 闪光',
    usageContext: '游戏图标、应用商店图标',
  },
  {
    id: '5',
    name: '金融商务',
    description: '适合金融、银行、投资、商务服务',
    config: { style: 'filled', primaryColor: '#1e40af', secondaryColor: '#374151', borderRadius: 12, padding: 28 },
    keywords: ['金融', '银行', '投资', '理财', '商务', '保险', '支付', '财富'],
    tags: ['专业', '稳重', '可信赖'],
    animationHint: '渐变上升 + 数据流动',
    usageContext: '企业官网、金融产品',
  },
  {
    id: '6',
    name: '教育学习',
    description: '适合教育、培训、学习类产品',
    config: { style: 'gradient', primaryColor: '#06b6d4', secondaryColor: '#8b5cf6', borderRadius: 16, padding: 24 },
    keywords: ['教育', '学习', '学校', '培训', '课程', '知识', '读书', '研究'],
    tags: ['智慧', '成长', '启发'],
    animationHint: '灯泡点亮 + 书页翻动',
    usageContext: '教育App、在线课程',
  },
  {
    id: '7',
    name: '健康医疗',
    description: '适合医疗、健康、健身相关产品',
    config: { style: 'outline', primaryColor: '#ef4444', secondaryColor: '#3b82f6', borderRadius: 20, padding: 28 },
    keywords: ['健康', '医疗', '医院', '健身', '运动', '医药', '护理', '养生'],
    tags: ['关怀', '专业', '安全'],
    animationHint: '心跳脉动 + 能量流动',
    usageContext: '健康App、医疗产品',
  },
  {
    id: '8',
    name: '美食餐饮',
    description: '适合餐饮、美食、食品相关品牌',
    config: { style: 'filled', primaryColor: '#ea580c', secondaryColor: '#f59e0b', borderRadius: 24, padding: 24 },
    keywords: ['美食', '餐饮', '食品', '咖啡', '餐厅', '烘焙', '甜点', '烹饪'],
    tags: ['美味', '温暖', '享受'],
    animationHint: '热气上升 + 闪光',
    usageContext: '外卖App、餐厅菜单',
  },
  {
    id: '9',
    name: '旅行出行',
    description: '适合旅游、出行、地图相关产品',
    config: { style: 'gradient', primaryColor: '#0ea5e9', secondaryColor: '#14b8a6', borderRadius: 16, padding: 20 },
    keywords: ['旅行', '旅游', '地图', '导航', '酒店', '机票', '出行', '度假'],
    tags: ['探索', '自由', '冒险'],
    animationHint: '飞机飞过 + 地图展开',
    usageContext: '旅游App、地图应用',
  },
  {
    id: '10',
    name: '社交沟通',
    description: '适合社交、通讯、社区类产品',
    config: { style: '3d', primaryColor: '#ec4899', secondaryColor: '#8b5cf6', borderRadius: 999, padding: 24 },
    keywords: ['社交', '聊天', '通讯', '社区', '朋友', '消息', '直播', '分享'],
    tags: ['连接', '互动', '温暖'],
    animationHint: '消息气泡弹出 + 涟漪扩散',
    usageContext: '社交App、即时通讯',
  },
  {
    id: '11',
    name: '极简现代',
    description: '极简主义设计，适合现代品牌和产品',
    config: { style: 'outline', primaryColor: '#111827', secondaryColor: '#6b7280', borderRadius: 8, padding: 32 },
    keywords: ['极简', '现代', '简约', '北欧', '设计', 'MUJI', '白色', '干净'],
    tags: ['极简', '高级', '纯粹'],
    animationHint: '线条描绘 + 淡入淡出',
    usageContext: '高端品牌、设计工作室',
  },
  {
    id: '12',
    name: '音乐艺术',
    description: '适合音乐、艺术、文化相关品牌',
    config: { style: 'gradient', primaryColor: '#8b5cf6', secondaryColor: '#ec4899', borderRadius: 20, padding: 28 },
    keywords: ['音乐', '艺术', '歌曲', '乐器', '演奏', 'DJ', '唱片', '演唱会'],
    tags: ['艺术', '情感', '表达'],
    animationHint: '音波震动 + 色彩律动',
    usageContext: '音乐App、乐队Logo',
  },
];

export function analyzeKeywords(input: string): {
  matchedKeywords: string[];
  categories: string[];
  recommendedPalette: string;
  recommendedStyle: IconStyle;
} {
  const lowerInput = input.toLowerCase();
  const matchedKeywords: string[] = [];
  const categories: Set<string> = new Set();

  creativeSuggestions.forEach((suggestion) => {
    suggestion.keywords.forEach((keyword) => {
      if (lowerInput.includes(keyword.toLowerCase())) {
        matchedKeywords.push(keyword);
        suggestion.tags.forEach((tag) => categories.add(tag));
      }
    });
  });

  let recommendedPalette = 'tech';
  let recommendedStyle: IconStyle = 'filled';

  if (lowerInput.includes('极简') || lowerInput.includes('简约') || lowerInput.includes('线框')) {
    recommendedStyle = 'outline';
    recommendedPalette = 'minimal';
  } else if (lowerInput.includes('渐变') || lowerInput.includes('炫彩') || lowerInput.includes('活力')) {
    recommendedStyle = 'gradient';
    recommendedPalette = 'creative';
  } else if (lowerInput.includes('3d') || lowerInput.includes('立体') || lowerInput.includes('游戏')) {
    recommendedStyle = '3d';
    recommendedPalette = 'playful';
  } else if (lowerInput.includes('自然') || lowerInput.includes('环保') || lowerInput.includes('健康')) {
    recommendedPalette = 'nature';
  } else if (lowerInput.includes('金融') || lowerInput.includes('商务') || lowerInput.includes('专业')) {
    recommendedPalette = 'professional';
  } else if (lowerInput.includes('科技') || lowerInput.includes('技术') || lowerInput.includes('AI')) {
    recommendedPalette = 'tech';
  } else if (lowerInput.includes('创意') || lowerInput.includes('艺术') || lowerInput.includes('设计')) {
    recommendedPalette = 'creative';
  } else if (lowerInput.includes('温暖') || lowerInput.includes('热情') || lowerInput.includes('美食')) {
    recommendedPalette = 'warm';
  } else if (lowerInput.includes('优雅') || lowerInput.includes('精致') || lowerInput.includes('时尚')) {
    recommendedPalette = 'elegant';
  }

  if (matchedKeywords.length === 0 && lowerInput.length > 0) {
    Object.entries(styleKeywords).forEach(([style, keywords]) => {
      keywords.forEach((keyword) => {
        if (lowerInput.includes(keyword.toLowerCase())) {
          recommendedStyle = style as IconStyle;
        }
      });
    });
  }

  return {
    matchedKeywords,
    categories: Array.from(categories),
    recommendedPalette,
    recommendedStyle,
  };
}

export function generateCreativeSuggestions(input: string): CreativeResult {
  const analysis = analyzeKeywords(input);
  const palette = creativePalette[analysis.recommendedPalette] || creativePalette.tech;

  const scoredSuggestions = creativeSuggestions
    .map((suggestion) => {
      let score = 0;
      const lowerInput = input.toLowerCase();

      suggestion.keywords.forEach((keyword) => {
        if (lowerInput.includes(keyword.toLowerCase())) {
          score += 10;
        }
      });

      if (suggestion.config.style === analysis.recommendedStyle) {
        score += 5;
      }

      return { ...suggestion, score };
    })
    .sort((a, b) => b.score - a.score)
    .filter((s) => s.score > 0)
    .slice(0, 4);

  const finalSuggestions =
    scoredSuggestions.length > 0
      ? scoredSuggestions
      : creativeSuggestions.slice(0, 4).map((s) => ({ ...s, score: 0 }));

  return {
    suggestions: finalSuggestions,
    primaryColor: palette.primary,
    secondaryColor: palette.secondary,
    recommendedStyle: analysis.recommendedStyle,
    mood: palette.mood,
    description:
      analysis.matchedKeywords.length > 0
        ? `根据您输入的关键词「${input}」，我们推荐「${palette.mood}」风格的设计方案`
        : `为您推荐几款热门的图标设计方案，点击即可应用`,
  };
}
