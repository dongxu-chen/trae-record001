export interface TextStyle {
  color?: string;
  fontFamily?: string;
  fontSize?: number;
  fontWeight?: string | number;
}

export interface LineStyle {
  color?: string;
  width?: number;
  type?: 'solid' | 'dashed' | 'dotted';
}

export interface ItemStyle {
  color?: string;
  borderColor?: string;
  borderWidth?: number;
}

export interface AxisLine {
  show?: boolean;
  lineStyle?: LineStyle;
}

export interface AxisTick {
  show?: boolean;
  lineStyle?: LineStyle;
}

export interface AxisLabel {
  show?: boolean;
  color?: string;
  fontSize?: number;
  fontFamily?: string;
}

export interface SplitLine {
  show?: boolean;
  lineStyle?: LineStyle;
}

export interface AxisConfig {
  axisLine?: AxisLine;
  axisTick?: AxisTick;
  axisLabel?: AxisLabel;
  splitLine?: SplitLine;
}

export interface LineConfig {
  itemStyle?: ItemStyle;
  lineStyle?: LineStyle;
  symbolSize?: number;
  symbol?: string;
  smooth?: boolean;
}

export interface ChartTheme {
  color: string[];
  backgroundColor?: string;
  textStyle?: TextStyle;
  title?: {
    textStyle?: TextStyle;
    subtextStyle?: TextStyle;
  };
  line?: LineConfig;
  bar?: {
    itemStyle?: ItemStyle;
  };
  pie?: {
    itemStyle?: ItemStyle;
    label?: {
      color?: string;
      fontSize?: number;
    };
  };
  scatter?: {
    itemStyle?: ItemStyle;
  };
  grid?: {
    show?: boolean;
    borderColor?: string;
    borderWidth?: number;
  };
  categoryAxis?: AxisConfig;
  valueAxis?: AxisConfig;
  legend?: {
    show?: boolean;
    textStyle?: TextStyle;
  };
  tooltip?: {
    backgroundColor?: string;
    borderColor?: string;
    borderWidth?: number;
    textStyle?: TextStyle;
  };
}

export type ChartType = 'line' | 'bar' | 'pie' | 'scatter' | 'area';

export type ThemeCategory = 'dashboard' | 'report' | 'finance' | 'marketing' | 'tech';

export interface RecommendedTheme {
  id: string;
  name: string;
  description: string;
  category: ThemeCategory;
  categoryName: string;
  theme: Partial<ChartTheme>;
  previewColors: string[];
}

export interface SavedTheme {
  id: string;
  name: string;
  description: string;
  theme: ChartTheme;
  isFavorite: boolean;
  createdAt: number;
  updatedAt: number;
  isShared: boolean;
  author: string;
  previewColors?: string[];
}

export interface ThemeState {
  theme: ChartTheme;
  chartType: ChartType;
  isDarkMode: boolean;
  savedThemes: SavedTheme[];
  history: ChartTheme[];
  historyIndex: number;
  isDirty: boolean;
}
