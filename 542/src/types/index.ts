export type ColorblindType =
  | 'protanopia'
  | 'protanomaly'
  | 'deuteranopia'
  | 'deuteranomaly'
  | 'tritanopia'
  | 'tritanomaly'
  | 'achromatopsia'
  | 'achromatomaly';

export interface ColorblindTypeInfo {
  id: ColorblindType;
  label: string;
  labelZh: string;
  category: 'red-green' | 'blue-yellow' | 'total';
  description: string;
  prevalence: string;
}

export const COLORBLIND_TYPES: ColorblindTypeInfo[] = [
  {
    id: 'protanopia',
    label: 'Protanopia',
    labelZh: '红色盲',
    category: 'red-green',
    description: '缺失L锥细胞，无法感知红色',
    prevalence: '男性约1.3%',
  },
  {
    id: 'protanomaly',
    label: 'Protanomaly',
    labelZh: '红色弱',
    category: 'red-green',
    description: 'L锥细胞灵敏度偏移，红色感知减弱',
    prevalence: '男性约1.3%',
  },
  {
    id: 'deuteranopia',
    label: 'Deuteranopia',
    labelZh: '绿色盲',
    category: 'red-green',
    description: '缺失M锥细胞，无法感知绿色',
    prevalence: '男性约1.2%',
  },
  {
    id: 'deuteranomaly',
    label: 'Deuteranomaly',
    labelZh: '绿色弱',
    category: 'red-green',
    description: 'M锥细胞灵敏度偏移，绿色感知减弱',
    prevalence: '男性约5.0%',
  },
  {
    id: 'tritanopia',
    label: 'Tritanopia',
    labelZh: '蓝色盲',
    category: 'blue-yellow',
    description: '缺失S锥细胞，无法感知蓝色',
    prevalence: '约0.003%',
  },
  {
    id: 'tritanomaly',
    label: 'Tritanomaly',
    labelZh: '蓝色弱',
    category: 'blue-yellow',
    description: 'S锥细胞灵敏度偏移，蓝色感知减弱',
    prevalence: '约0.0001%',
  },
  {
    id: 'achromatopsia',
    label: 'Achromatopsia',
    labelZh: '全色盲',
    category: 'total',
    description: '全锥细胞缺失，仅能感知明暗',
    prevalence: '约0.003%',
  },
  {
    id: 'achromatomaly',
    label: 'Achromatomaly',
    labelZh: '全色弱',
    category: 'total',
    description: '锥细胞灵敏度降低，色彩感知微弱',
    prevalence: '极其罕见',
  },
];

export interface RGB {
  r: number;
  g: number;
  b: number;
}

export interface HSL {
  h: number;
  s: number;
  l: number;
}

export type RegionType = 'text' | 'background' | 'graphic' | 'complex';

export interface ImageRegion {
  x: number;
  y: number;
  width: number;
  height: number;
  dominantColor: RGB;
  secondaryColors: RGB[];
  colorVariance: number;
  regionType: RegionType;
  isComplex: boolean;
  edgeDensity: number;
}

export type AlternativeType = 'pattern' | 'icon' | 'text' | 'outline' | 'border';

export interface AlternativeSolution {
  type: AlternativeType;
  label: string;
  description: string;
  icon: string;
  code?: string;
}

export interface ColorSuggestion {
  original: RGB;
  suggested: RGB;
  contrastRatio: number;
  aaPass: boolean;
  aaaPass: boolean;
}

export interface EnhancedSuggestion extends ColorSuggestion {
  alternatives: AlternativeSolution[];
  visualLabels: VisualLabel[];
  codeFixes: CodeFix[];
}

export interface VisualLabel {
  type: 'pattern' | 'icon' | 'text';
  value: string;
  display: string;
}

export type CodeFormat = 'css' | 'tailwind' | 'inline' | 'scss';

export interface CodeFix {
  format: CodeFormat;
  original: string;
  fixed: string;
  selector?: string;
  property?: string;
}

export interface ContrastIssue {
  id: string;
  foreground: RGB;
  background: RGB;
  contrastRatio: number;
  aaNormal: boolean;
  aaLarge: boolean;
  aaaNormal: boolean;
  aaaLarge: boolean;
  severity: 'critical' | 'major' | 'minor';
  position: { x: number; y: number };
  regionType: RegionType;
  suggestions: EnhancedSuggestion[];
  affectedColorblindTypes: ColorblindType[];
  cssSelector?: string;
}

export interface WcagReport {
  totalChecks: number;
  passed: number;
  failed: number;
  passRate: number;
  issues: ContrastIssue[];
  criticalCount: number;
  majorCount: number;
  minorCount: number;
  analyzedRegions: number;
  excludedComplexRegions: number;
}

export type WcagLevel = 'AA' | 'AAA';

export type TextSize = 'normal' | 'large';

export interface PageScanResult {
  id: string;
  url: string;
  title: string;
  status: 'pending' | 'scanning' | 'completed' | 'error';
  progress: number;
  screenshot?: string;
  report?: WcagReport;
  scannedAt?: Date;
  error?: string;
}

export interface BatchScanSession {
  id: string;
  name: string;
  urls: string[];
  results: PageScanResult[];
  status: 'idle' | 'scanning' | 'completed';
  createdAt: Date;
  completedAt?: Date;
  overallPassRate: number;
  totalIssues: number;
}

export interface TesterProfile {
  id: string;
  name: string;
  avatar?: string;
  colorblindTypes: ColorblindType[];
  severity: 'mild' | 'moderate' | 'severe';
  experience: 'beginner' | 'intermediate' | 'expert';
  availability: 'weekdays' | 'weekends' | 'flexible';
  bio: string;
  rating: number;
  completedTests: number;
  languages: string[];
}

export interface TestTask {
  id: string;
  title: string;
  description: string;
  url: string;
  targetColorblindTypes: ColorblindType[];
  status: 'open' | 'in_progress' | 'completed';
  compensation: string;
  estimatedTime: string;
  createdAt: Date;
  deadline: Date;
  applicants: TesterProfile[];
  acceptedTester?: TesterProfile;
  testResult?: TestResult;
}

export interface TestResult {
  overallRating: number;
  issuesFound: string[];
  positiveFeedback: string;
  suggestions: string;
  completedAt: Date;
  screenshots: string[];
}

export type ScanMode = 'single' | 'batch' | 'sitemap';
