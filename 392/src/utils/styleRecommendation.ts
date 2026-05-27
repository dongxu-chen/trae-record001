import { IconStyle, UserStyleProfile, StyleRecommendation } from '../types/advanced';
import { Icon, UploadedIcon } from '../types';

export const iconStyles: IconStyle[] = [
  {
    id: 'minimal',
    name: '极简风格',
    description: '简洁线条，干净现代的设计语言',
    keywords: ['简单', '干净', '现代', '扁平', '线框'],
    colorPalette: ['#000000', '#333333', '#666666', '#999999'],
    complexity: 'simple',
    roundedness: 'medium',
    strokeWidth: 'thin',
  },
  {
    id: 'material',
    name: 'Material Design',
    description: 'Google Material Design 风格，圆润饱满',
    keywords: ['material', '谷歌', '圆润', '现代', '物理'],
    colorPalette: ['#2196F3', '#4CAF50', '#FF9800', '#F44336'],
    complexity: 'medium',
    roundedness: 'rounded',
    strokeWidth: 'medium',
  },
  {
    id: 'fontawesome',
    name: 'FontAwesome',
    description: 'FontAwesome 经典风格，社区最喜爱',
    keywords: ['fa', '经典', '社区', '流行', '通用'],
    colorPalette: ['#183153', '#339AF0', '#FFD43B', '#228BE6'],
    complexity: 'medium',
    roundedness: 'medium',
    strokeWidth: 'medium',
  },
  {
    id: 'outline',
    name: '线框风格',
    description: '精致的线条轮廓，优雅精致',
    keywords: ['线框', '轮廓', '精致', '优雅', '线条'],
    colorPalette: ['#495057', '#868E96', '#ADB5BD', '#CED4DA'],
    complexity: 'simple',
    roundedness: 'medium',
    strokeWidth: 'thin',
  },
  {
    id: 'bold',
    name: '粗体风格',
    description: '醒目有力的设计，适合强调',
    keywords: ['粗体', '有力', '醒目', '重', '强调'],
    colorPalette: ['#212529', '#343A40', '#495057', '#6C757D'],
    complexity: 'medium',
    roundedness: 'medium',
    strokeWidth: 'thick',
  },
  {
    id: 'playful',
    name: '趣味风格',
    description: '活泼圆润，充满趣味和亲和力',
    keywords: ['趣味', '可爱', '活泼', '友好', '卡通'],
    colorPalette: ['#FF6B6B', '#4ECDC4', '#FFE66D', '#95E1D3'],
    complexity: 'medium',
    roundedness: 'rounded',
    strokeWidth: 'medium',
  },
  {
    id: 'sharp',
    name: '锐利风格',
    description: '棱角分明，专业商务感',
    keywords: ['锐利', '棱角', '专业', '商务', '直线'],
    colorPalette: ['#2D3748', '#4A5568', '#718096', '#A0AEC0'],
    complexity: 'simple',
    roundedness: 'sharp',
    strokeWidth: 'medium',
  },
  {
    id: 'gradient',
    name: '渐变风格',
    description: '现代渐变效果，视觉冲击力强',
    keywords: ['渐变', '色彩', '现代', '时尚', '华丽'],
    colorPalette: ['#667eea', '#764ba2', '#f093fb', '#f5576c'],
    complexity: 'complex',
    roundedness: 'rounded',
    strokeWidth: 'medium',
  },
];

export const analyzeUserStyleProfile = (
  recentIcons: Icon[],
  uploadedIcons: UploadedIcon[],
  usageHistory: Record<string, number>
): UserStyleProfile => {
  const preferredColors: string[] = [];
  const recentCategories: string[] = [];
  const usageCount: Record<string, number> = {};
  
  let totalComplexity = 0;
  let count = 0;
  
  for (const icon of recentIcons) {
    recentCategories.push(icon.category);
    if (icon.tags) {
      for (const tag of icon.tags) {
        usageCount[tag] = (usageCount[tag] || 0) + (usageHistory[icon.id] || 1);
      }
    }
    count++;
  }
  
  for (const uploaded of uploadedIcons) {
    preferredColors.push('#4F46E5');
    recentCategories.push(uploaded.category);
    count++;
  }
  
  const sortedUsage = Object.entries(usageCount)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([key]) => key);
  
  const preferredStyles = determinePreferredStyles(sortedUsage, recentCategories);
  
  return {
    preferredStyles,
    preferredColors: [...new Set(preferredColors)],
    recentCategories: [...new Set(recentCategories)].slice(0, 5),
    usageCount,
    averageComplexity: count > 0 ? totalComplexity / count : 0.5,
  };
};

const determinePreferredStyles = (
  topTags: string[],
  categories: string[]
): string[] => {
  const styleScores: Record<string, number> = {};
  
  for (const style of iconStyles) {
    let score = 0;
    for (const tag of topTags) {
      if (style.keywords.some(k => tag.toLowerCase().includes(k.toLowerCase()))) {
        score += 10;
      }
    }
    for (const category of categories) {
      if (style.keywords.some(k => category.toLowerCase().includes(k.toLowerCase()))) {
        score += 5;
      }
    }
    styleScores[style.id] = score;
  }
  
  return Object.entries(styleScores)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([id]) => id);
};

export const generateStyleRecommendations = (
  profile: UserStyleProfile
): StyleRecommendation[] => {
  const recommendations: StyleRecommendation[] = [];
  
  for (const styleId of profile.preferredStyles) {
    const style = iconStyles.find(s => s.id === styleId);
    if (style) {
      recommendations.push({
        style,
        confidence: 0.85,
        reason: `基于您最近使用的 ${profile.recentCategories.slice(0, 2).join('、')} 类图标推荐`,
      });
    }
  }
  
  if (recommendations.length < 3) {
    const remainingStyles = iconStyles.filter(s => 
      !recommendations.some(r => r.style.id === s.id)
    );
    
    for (let i = 0; i < Math.min(3 - recommendations.length, remainingStyles.length); i++) {
      recommendations.push({
        style: remainingStyles[i],
        confidence: 0.5,
        reason: '热门推荐风格',
      });
    }
  }
  
  return recommendations;
};

export const getIconsForStyle = (
  styleId: string,
  icons: Icon[]
): Icon[] => {
  const style = iconStyles.find(s => s.id === styleId);
  if (!style) return icons;
  
  return icons.filter(icon => {
    const iconText = `${icon.name} ${icon.tags.join(' ')} ${icon.category}`.toLowerCase();
    return style.keywords.some(k => iconText.includes(k.toLowerCase()));
  }).slice(0, 20);
};
