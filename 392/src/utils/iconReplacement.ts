import { OutdatedIcon } from '../types/advanced';
import { Icon } from '../types';

export const outdatedIcons: OutdatedIcon[] = [
  {
    oldIconId: 'fa-home',
    oldIconName: 'home (经典)',
    newIconId: 'ma-home',
    newIconName: 'home (modern)',
    reason: '经典房屋图标已过时，现代设计更倾向于简洁线条',
    improvement: '更简洁的线条，符合现代设计趋势',
  },
  {
    oldIconId: 'fa-user',
    oldIconName: 'user (经典)',
    newIconId: 'ma-person',
    newIconName: 'person (modern)',
    reason: '传统用户头像过于复杂，现代设计追求极简',
    improvement: '简化的轮廓，更好的缩放效果',
  },
  {
    oldIconId: 'fa-search',
    oldIconName: 'search (经典)',
    newIconId: 'ma-search',
    newIconName: 'search (modern)',
    reason: '搜索图标手柄过长，影响整体美感',
    improvement: '更紧凑的设计，更好的视觉平衡',
  },
  {
    oldIconId: 'fa-star',
    oldIconName: 'star (经典)',
    newIconId: 'ma-star',
    newIconName: 'star (modern)',
    reason: '五角星角度尖锐，现代设计更圆润',
    improvement: '圆角过渡，更友好的视觉感受',
  },
  {
    oldIconId: 'fa-heart',
    oldIconName: 'heart (经典)',
    newIconId: 'ma-favorite',
    newIconName: 'favorite (modern)',
    reason: '心形比例需要优化以适应现代UI',
    improvement: '更优美的曲线，更好的比例',
  },
  {
    oldIconId: 'fa-cog',
    oldIconName: 'cog (经典)',
    newIconId: 'ma-settings',
    newIconName: 'settings (modern)',
    reason: '齿轮图标齿牙过多显得杂乱',
    improvement: '简化的齿轮设计，更清晰的轮廓',
  },
  {
    oldIconId: 'fa-bell',
    oldIconName: 'bell (经典)',
    newIconId: 'ma-notifications',
    newIconName: 'notifications (modern)',
    reason: '铃铛设计过于写实，图标需要抽象化',
    improvement: '抽象化设计，更好的识别度',
  },
  {
    oldIconId: 'fa-envelope',
    oldIconName: 'envelope (经典)',
    newIconId: 'ma-email',
    newIconName: 'email (modern)',
    reason: '信封设计带有阴影，现代设计扁平化',
    improvement: '扁平化设计，符合现代UI趋势',
  },
  {
    oldIconId: 'fa-lock',
    oldIconName: 'lock (经典)',
    newIconId: 'ma-lock',
    newIconName: 'lock (modern)',
    reason: '锁的设计过于复杂，包含过多细节',
    improvement: '极简设计，保持核心识别特征',
  },
  {
    oldIconId: 'fa-eye',
    oldIconName: 'eye (经典)',
    newIconId: 'ma-visibility',
    newIconName: 'visibility (modern)',
    reason: '眼睛设计包含瞳孔细节，显得杂乱',
    improvement: '简化的轮廓，保留可识别性',
  },
  {
    oldIconId: 'fa-download',
    oldIconName: 'download (经典)',
    newIconId: 'ma-download',
    newIconName: 'download (modern)',
    reason: '箭头设计不流畅',
    improvement: '更流畅的曲线，更好的视觉引导',
  },
  {
    oldIconId: 'fa-upload',
    oldIconName: 'upload (经典)',
    newIconId: 'ma-upload',
    newIconName: 'upload (modern)',
    reason: '与下载图标同样的问题',
    improvement: '统一的设计语言，更简洁',
  },
  {
    oldIconId: 'fa-trash',
    oldIconName: 'trash (经典)',
    newIconId: 'ma-delete',
    newIconName: 'delete (modern)',
    reason: '垃圾桶设计包含盖子细节',
    improvement: '简化设计，保留核心语义',
  },
  {
    oldIconId: 'fa-edit',
    oldIconName: 'edit (经典)',
    newIconId: 'ma-edit',
    newIconName: 'edit (modern)',
    reason: '铅笔设计角度不自然',
    improvement: '更自然的角度，更好的比例',
  },
  {
    oldIconId: 'fa-check',
    oldIconName: 'check (经典)',
    newIconId: 'ma-check',
    newIconName: 'check (modern)',
    reason: '对勾笔画粗细不均',
    improvement: '统一的线条粗细，更均衡',
  },
  {
    oldIconId: 'fa-close',
    oldIconName: 'close (经典)',
    newIconId: 'ma-close',
    newIconName: 'close (modern)',
    reason: 'X 形交叉处设计粗糙',
    improvement: '更圆润的交叉点，更好的视觉效果',
  },
  {
    oldIconId: 'fa-plus',
    oldIconName: 'plus (经典)',
    newIconId: 'ma-add',
    newIconName: 'add (modern)',
    reason: '加号线条设计',
    improvement: '更圆润的末端，更友好',
  },
  {
    oldIconId: 'fa-menu',
    oldIconName: 'menu (经典)',
    newIconId: 'ma-menu',
    newIconName: 'menu (modern)',
    reason: '汉堡菜单线条间距过大',
    improvement: '更紧凑的设计，更好的触控目标',
  },
  {
    oldIconId: 'fa-calendar',
    oldIconName: 'calendar (经典)',
    newIconId: 'ma-date-range',
    newIconName: 'date_range (modern)',
    reason: '日历设计过于写实',
    improvement: '抽象化设计，保留日期语义',
  },
  {
    oldIconId: 'fa-clock',
    oldIconName: 'clock (经典)',
    newIconId: 'ma-schedule',
    newIconName: 'schedule (modern)',
    reason: '时钟指针设计复杂',
    improvement: '简化的指针，更清晰的时间语义',
  },
];

export const checkForOutdatedIcons = (
  projectIcons: string[]
): OutdatedIcon[] => {
  return outdatedIcons.filter(item => 
    projectIcons.includes(item.oldIconId) || 
    projectIcons.some(id => id.includes(item.oldIconName.split(' ')[0]))
  );
};

export const getReplacementSuggestions = (
  iconName: string
): OutdatedIcon | null => {
  const lowerName = iconName.toLowerCase();
  return outdatedIcons.find(item => 
    lowerName.includes(item.oldIconName.toLowerCase()) ||
    lowerName.includes(item.oldIconId.toLowerCase())
  ) || null;
};

export const analyzeProjectIcons = (
  iconIds: string[]
): {
  outdatedCount: number;
  suggestions: OutdatedIcon[];
  summary: string;
} => {
  const suggestions = checkForOutdatedIcons(iconIds);
  const outdatedCount = suggestions.length;
  
  let summary = '';
  if (outdatedCount === 0) {
    summary = '太棒了！您的图标库都是最新的设计风格。';
  } else if (outdatedCount <= 3) {
    summary = `发现 ${outdatedCount} 个可以优化的图标，建议考虑更新。`;
  } else {
    summary = `发现 ${outdatedCount} 个过时图标，建议进行整体风格更新。`;
  }
  
  return {
    outdatedCount,
    suggestions,
    summary,
  };
};

export const generateUpdatePlan = (
  suggestions: OutdatedIcon[]
): {
  priority: 'high' | 'medium' | 'low';
  steps: string[];
  estimatedTime: string;
} => {
  let priority: 'high' | 'medium' | 'low' = 'low';
  const steps: string[] = [];
  
  if (suggestions.length >= 10) {
    priority = 'high';
    steps.push('进行整体图标库评估');
    steps.push('制定更新计划');
    steps.push('分批次替换高优先级图标');
    steps.push('更新设计规范文档');
  } else if (suggestions.length >= 5) {
    priority = 'medium';
    steps.push('替换核心页面中的过时图标');
    steps.push('更新组件库中的图标引用');
    steps.push('在下次版本发布时完成更新');
  } else {
    priority = 'low';
    steps.push('在日常维护中逐步替换');
    steps.push('更新图标时优先使用新版图标');
  }
  
  const estimatedTime = `${Math.max(1, Math.ceil(suggestions.length / 3))} 小时`;
  
  return { priority, steps, estimatedTime };
};
