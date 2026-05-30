import { create } from 'zustand';
import { LEDStore, PresetConfig } from './types';

const generateId = () => Math.random().toString(36).substr(2, 9);

const defaultPresets: PresetConfig[] = [
  {
    name: '演唱会应援',
    lines: [
      { text: '我爱明星 永远支持', color: '#ff0088' },
      { text: 'CONCERT 2024', color: '#00ffff' }
    ],
    font: { size: 48, glow: true, glowIntensity: 15 },
    background: { effect: 'particles', effectColor: '#ff0088' },
    scroll: { direction: 'left', speed: 3 }
  },
  {
    name: '新闻播报',
    lines: [
      { text: '今日头条：重大新闻事件更新中...', color: '#ffffff' },
      { text: 'BREAKING NEWS', color: '#ff3333' }
    ],
    font: { size: 36, glow: true, glowIntensity: 8 },
    background: { color: '#1a1a2e', effect: 'neon-glow', effectColor: '#00ff88' },
    scroll: { direction: 'left', speed: 2 }
  },
  {
    name: '公告栏',
    lines: [
      { text: '欢迎光临 营业时间 9:00-22:00', color: '#00ff88' }
    ],
    font: { size: 42, glow: true, glowIntensity: 12 },
    background: { color: '#0a0a0f', effect: 'none' },
    scroll: { direction: 'right', speed: 1 }
  },
  {
    name: '赛博朋克',
    lines: [
      { text: 'CYBERPUNK 2077', color: '#ff00ff' },
      { text: '霓虹之夜 NIGHT CITY', color: '#00ffff' }
    ],
    font: { size: 52, glow: true, glowIntensity: 20 },
    background: { effect: 'neon-glow', effectColor: '#ff00ff', effectIntensity: 80 },
    scroll: { direction: 'left', speed: 2 }
  },
  {
    name: '矩阵风格',
    lines: [
      { text: 'THE MATRIX 黑客帝国', color: '#00ff00' },
      { text: 'WAKE UP NEO', color: '#00ff00' }
    ],
    font: { size: 38, glow: true, glowIntensity: 10 },
    background: { effect: 'matrix', effectColor: '#00ff00', effectIntensity: 100 },
    scroll: { direction: 'down', speed: 1 }
  },
  {
    name: '星空浪漫',
    lines: [
      { text: '仰望星空 脚踏实地', color: '#ffffff' },
      { text: '✨ STARS ✨', color: '#ffd700' }
    ],
    font: { size: 44, glow: true, glowIntensity: 12 },
    background: { effect: 'starfield', effectColor: '#ffffff', effectIntensity: 100 },
    scroll: { direction: 'left', speed: 1 }
  },
  {
    name: '🧧 春节',
    lines: [
      { text: '恭喜发财 万事如意', color: '#ff0000' },
      { text: '龙年大吉 新春快乐', color: '#ffd700' }
    ],
    font: { size: 52, glow: true, glowIntensity: 18, family: '"Microsoft YaHei", sans-serif' },
    background: { color: '#1a0000', effect: 'particles', effectColor: '#ff0000', effectIntensity: 80 },
    scroll: { direction: 'left', speed: 2 }
  },
  {
    name: '🎄 圣诞节',
    lines: [
      { text: 'Merry Christmas', color: '#00ff00' },
      { text: '圣诞快乐 岁岁平安', color: '#ff0000' }
    ],
    font: { size: 48, glow: true, glowIntensity: 15 },
    background: { effect: 'starfield', effectColor: '#00ff00', effectIntensity: 80 },
    scroll: { direction: 'left', speed: 1 }
  },
  {
    name: '🎆 元旦跨年',
    lines: [
      { text: 'HAPPY NEW YEAR 2025', color: '#ffd700' },
      { text: '新年快乐 前程似锦', color: '#ffffff' }
    ],
    font: { size: 50, glow: true, glowIntensity: 20 },
    background: { effect: 'particles', effectColor: '#ffd700', effectIntensity: 90 },
    scroll: { direction: 'left', speed: 2 }
  },
  {
    name: '🏮 元宵节',
    lines: [
      { text: '元宵快乐 团圆美满', color: '#ff6600' },
      { text: '花灯万盏 月圆人圆', color: '#ffcc00' }
    ],
    font: { size: 46, glow: true, glowIntensity: 14, family: '"Microsoft YaHei", sans-serif' },
    background: { color: '#0a0500', effect: 'particles', effectColor: '#ff6600', effectIntensity: 70 },
    scroll: { direction: 'right', speed: 1 }
  },
  {
    name: '💕 情人节',
    lines: [
      { text: 'Happy Valentine\'s Day', color: '#ff1493' },
      { text: '爱你一万年 永远在一起', color: '#ff69b4' }
    ],
    font: { size: 44, glow: true, glowIntensity: 16 },
    background: { effect: 'particles', effectColor: '#ff1493', effectIntensity: 60 },
    scroll: { direction: 'left', speed: 1 }
  },
  {
    name: '🎓 毕业季',
    lines: [
      { text: '毕业快乐 前程似锦', color: '#4169e1' },
      { text: 'CONGRATULATIONS!', color: '#ffd700' }
    ],
    font: { size: 46, glow: true, glowIntensity: 12 },
    background: { effect: 'starfield', effectColor: '#4169e1', effectIntensity: 70 },
    scroll: { direction: 'left', speed: 2 }
  },
  {
    name: '🔥 限时特惠',
    lines: [
      { text: '限时特惠 全场5折起', color: '#ff4400' },
      { text: 'FLASH SALE 50% OFF', color: '#ffcc00' }
    ],
    font: { size: 50, glow: true, glowIntensity: 18 },
    background: { color: '#0a0000', effect: 'neon-glow', effectColor: '#ff4400', effectIntensity: 90 },
    scroll: { direction: 'left', speed: 3 }
  },
  {
    name: '🏷️ 新品上市',
    lines: [
      { text: '新品首发 限量抢购', color: '#00ff88' },
      { text: 'NEW ARRIVAL 购物狂欢', color: '#00ccff' }
    ],
    font: { size: 46, glow: true, glowIntensity: 14 },
    background: { effect: 'particles', effectColor: '#00ff88', effectIntensity: 60 },
    scroll: { direction: 'left', speed: 2 }
  },
  {
    name: '🎉 开业大吉',
    lines: [
      { text: '盛大开业 钜惠全城', color: '#ff0000' },
      { text: 'GRAND OPENING', color: '#ffd700' }
    ],
    font: { size: 52, glow: true, glowIntensity: 20, family: '"Microsoft YaHei", sans-serif' },
    background: { color: '#1a0000', effect: 'particles', effectColor: '#ff0000', effectIntensity: 80 },
    scroll: { direction: 'left', speed: 2 }
  },
  {
    name: '💰 双11狂欢',
    lines: [
      { text: '双11全球狂欢节', color: '#ff0088' },
      { text: '11.11 BIG SALE 全场钜惠', color: '#ffcc00' }
    ],
    font: { size: 48, glow: true, glowIntensity: 16 },
    background: { effect: 'neon-glow', effectColor: '#ff0088', effectIntensity: 80 },
    scroll: { direction: 'left', speed: 3 }
  }
];

const initialState = {
  lines: [
    { id: generateId(), text: '欢迎使用LED字幕滚动组件', color: '#00ff88' },
    { id: generateId(), text: '自定义文字 · 字体 · 颜色 · 特效', color: '#ff0088' }
  ],
  font: {
    family: 'Orbitron, sans-serif',
    size: 48,
    weight: 700,
    glow: true,
    glowIntensity: 12
  },
  scroll: {
    direction: 'left' as const,
    speed: 2,
    mode: 'continuous' as const
  },
  background: {
    color: '#0a0a0f',
    effect: 'particles' as const,
    effectIntensity: 50,
    effectColor: '#00ff88'
  },
  activeLineIndex: 0,
  isPlaying: true
};

export const useLEDStore = create<LEDStore>((set, get) => ({
  ...initialState,

  addLine: () => set((state) => ({
    lines: [...state.lines, { id: generateId(), text: '新字幕行', color: '#ffffff' }],
    activeLineIndex: state.lines.length
  })),

  removeLine: (index: number) => set((state) => {
    if (state.lines.length <= 1) return state;
    const newLines = state.lines.filter((_, i) => i !== index);
    return {
      lines: newLines,
      activeLineIndex: Math.min(state.activeLineIndex, newLines.length - 1)
    };
  }),

  updateLine: (index: number, updates: Partial<{ text: string; color: string }>) =>
    set((state) => ({
      lines: state.lines.map((line, i) =>
        i === index ? { ...line, ...updates } : line
      )
    })),

  setFont: (font) => set((state) => ({
    font: { ...state.font, ...font }
  })),

  setScroll: (scroll) => set((state) => ({
    scroll: { ...state.scroll, ...scroll }
  })),

  setBackground: (bg) => set((state) => ({
    background: { ...state.background, ...bg }
  })),

  setActiveLineIndex: (index) => set({ activeLineIndex: index }),

  togglePlaying: () => set((state) => ({ isPlaying: !state.isPlaying })),

  applyPreset: (preset: PresetConfig) => set(() => ({
    lines: preset.lines.map((l) => ({ ...l, id: generateId() })),
    font: { ...initialState.font, ...preset.font },
    background: { ...initialState.background, ...preset.background },
    scroll: { ...initialState.scroll, ...preset.scroll },
    activeLineIndex: 0
  })),

  reset: () => set(initialState)
}));

export { defaultPresets };
