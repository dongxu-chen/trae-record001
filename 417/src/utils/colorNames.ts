import chroma from 'chroma-js';
import type { ColorNameResult } from '@/types';

export const COLOR_NAMES: { name: string; hex: string }[] = [
  { name: '纯白', hex: '#FFFFFF' },
  { name: '银灰', hex: '#C0C0C0' },
  { name: '灰色', hex: '#808080' },
  { name: '炭黑', hex: '#36454F' },
  { name: '纯黑', hex: '#000000' },
  { name: '红色', hex: '#FF0000' },
  { name: '橙红', hex: '#FF4500' },
  { name: '珊瑚红', hex: '#FF7F50' },
  { name: '西瓜红', hex: '#FF6B6B' },
  { name: '深红', hex: '#8B0000' },
  { name: '酒红', hex: '#722F37' },
  { name: '宝石红', hex: '#E0115F' },
  { name: '猩红', hex: '#DC143C' },
  { name: '橙色', hex: '#FFA500' },
  { name: '深橙', hex: '#FF8C00' },
  { name: '琥珀', hex: '#FFBF00' },
  { name: '杏黄', hex: '#FBCEB1' },
  { name: '南瓜橙', hex: '#FF7518' },
  { name: '黄色', hex: '#FFFF00' },
  { name: '金黄', hex: '#FFD700' },
  { name: '柠檬黄', hex: '#FFF44F' },
  { name: '芥末黄', hex: '#C4A42A' },
  { name: '米黄', hex: '#F5DEB3' },
  { name: '象牙白', hex: '#FFFFF0' },
  { name: '绿色', hex: '#00FF00' },
  { name: '草绿', hex: '#7CFC00' },
  { name: '森林绿', hex: '#228B22' },
  { name: '深绿', hex: '#006400' },
  { name: '薄荷绿', hex: '#98FF98' },
  { name: '橄榄绿', hex: '#808000' },
  { name: '松绿', hex: '#01796F' },
  { name: '青色', hex: '#00FFFF' },
  { name: '蒂芙尼蓝', hex: '#0ABAB5' },
  { name: '青绿', hex: '#00FFCC' },
  { name: '水绿', hex: '#00CED1' },
  { name: '蓝绿', hex: '#088F8F' },
  { name: '蓝色', hex: '#0000FF' },
  { name: '天蓝', hex: '#87CEEB' },
  { name: '天空蓝', hex: '#87CEFA' },
  { name: '湖蓝', hex: '#1E90FF' },
  { name: '皇家蓝', hex: '#4169E1' },
  { name: '藏蓝', hex: '#000080' },
  { name: '午夜蓝', hex: '#191970' },
  { name: '海军蓝', hex: '#000080' },
  { name: '宝蓝', hex: '#191970' },
  { name: '紫色', hex: '#800080' },
  { name: '薰衣草', hex: '#E6E6FA' },
  { name: '深紫', hex: '#4B0082' },
  { name: '洋紫', hex: '#9932CC' },
  { name: '品红', hex: '#FF00FF' },
  { name: '兰花紫', hex: '#DA70D6' },
  { name: '紫罗兰', hex: '#EE82EE' },
  { name: '粉色', hex: '#FFC0CB' },
  { name: '亮粉', hex: '#FF69B4' },
  { name: '深粉', hex: '#FF1493' },
  { name: '腮红粉', hex: '#DE5D83' },
  { name: '婴儿粉', hex: '#F4C2C2' },
  { name: '棕色', hex: '#A52A2A' },
  { name: '巧克力', hex: '#7B3F00' },
  { name: '咖啡', hex: '#6F4E37' },
  { name: '驼色', hex: '#C19A6B' },
  { name: '沙色', hex: '#C2B280' },
  { name: '卡其', hex: '#C3B091' },
  { name: '青铜', hex: '#CD7F32' },
  { name: '赤陶', hex: '#E2725B' },
];

export function getColorName(targetHex: string): ColorNameResult {
  let bestMatch = COLOR_NAMES[0];
  let minDistance = Infinity;

  try {
    const target = chroma(targetHex);
    COLOR_NAMES.forEach((color) => {
      const distance = chroma.distance(target, color.hex, 'lab');
      if (distance < minDistance) {
        minDistance = distance;
        bestMatch = color;
      }
    });
  } catch {
    return { name: '未知颜色', hex: targetHex, distance: 100 };
  }

  return {
    name: bestMatch.name,
    hex: bestMatch.hex,
    distance: Math.round(minDistance * 100) / 100,
  };
}
