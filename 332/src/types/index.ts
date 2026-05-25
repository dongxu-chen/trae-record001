export type QRCodeType = 'text' | 'url' | 'vcard' | 'wifi' | 'email';

export type DotStyle = 'square' | 'round' | 'dots';
export type EyeStyle = 'square' | 'rounded' | 'circle' | 'heart' | 'star';
export type ArtPattern = 'none' | 'gradient' | 'rainbow' | 'geometric' | 'abstract' | 'nature' | 'cyber' | 'vintage';
export type BackgroundStyle = 'solid' | 'gradient' | 'transparent';

export type ErrorCorrectionLevel = 'L' | 'M' | 'Q' | 'H';

export interface QRStyle {
  foregroundColor: string;
  backgroundColor: string;
  size: number;
  errorCorrectionLevel: ErrorCorrectionLevel;
  dotStyle: DotStyle;
  cornerRadius: number;
  logo?: string;
  logoSize?: number;
  logoBackgroundColor?: string;
  artPattern?: ArtPattern;
  eyeStyle?: EyeStyle;
  backgroundStyle?: BackgroundStyle;
  gradientStart?: string;
  gradientEnd?: string;
  gradientType?: 'linear' | 'radial' | 'diagonal';
}

export interface VCardData {
  firstName: string;
  lastName: string;
  organization: string;
  title: string;
  phone: string;
  email: string;
  website: string;
  address: string;
}

export interface WiFiData {
  ssid: string;
  password: string;
  encryption: 'WPA' | 'WEP' | 'nopass';
  hidden: boolean;
}

export interface EmailData {
  to: string;
  subject: string;
  body: string;
}

export interface DynamicCode {
  id: string;
  shortCode: string;
  originalUrl: string;
  name: string;
  type: QRCodeType;
  style: QRStyle;
  scanCount: number;
  createdAt: string;
  updatedAt: string;
  isActive: boolean;
}

export interface ScanLog {
  id: string;
  dynamicCodeId: string;
  timestamp: string;
  ip: string;
  userAgent: string;
  country?: string;
  region?: string;
  city?: string;
  deviceType: 'mobile' | 'desktop' | 'tablet';
  browser?: string;
  os?: string;
  referer?: string;
  language?: string;
  screenResolution?: string;
  isNewVisitor?: boolean;
  conversionGoal?: string;
  conversionValue?: number;
}

export interface CodeAnalysis {
  codeId: string;
  codeName: string;
  totalScans: number;
  uniqueVisitors: number;
  bounceRate: number;
  avgTimeOnPage: number;
  conversionRate: number;
  totalConversions: number;
  conversionValue: number;
  roi: number;
}

export interface UserProfile {
  country?: string;
  region?: string;
  city?: string;
  deviceType: string;
  browser: string;
  os: string;
  language: string;
  isMobile: boolean;
  ageGroup?: string;
  gender?: string;
  interests?: string[];
}

export interface LandingPageAnalysis {
  codeId: string;
  codeName: string;
  userProfiles: UserProfile[];
  conversionFunnel: Array<{
    stage: string;
    count: number;
    conversionRate: number;
  }>;
  performanceMetrics: {
    pageLoadTime: number;
    bounceRate: number;
    avgSessionDuration: number;
    pagesPerSession: number;
  };
  topReferers: Array<{ source: string; count: number }>;
  hourlyDistribution: Array<{ hour: number; count: number }>;
  dailyDistribution: Array<{ day: string; count: number }>;
}

export interface StatisticsOverview {
  totalScans: number;
  totalCodes: number;
  scansThisWeek: number;
  topPerformingCodes: Array<{
    id: string;
    name: string;
    scans: number;
    conversionRate: number;
  }>;
  scanTrend: Array<{
    date: string;
    count: number;
    conversions: number;
  }>;
  deviceDistribution: Array<{
    type: string;
    count: number;
    percentage: number;
  }>;
  geographicDistribution: Array<{
    country: string;
    count: number;
    percentage: number;
  }>;
  browserDistribution: Array<{
    browser: string;
    count: number;
    percentage: number;
  }>;
  conversionOverview: {
    totalConversions: number;
    totalConversionValue: number;
    avgConversionRate: number;
  };
}

export interface ManagementOverview {
  totalCodes: number;
  activeCodes: number;
  inactiveCodes: number;
  totalScansToday: number;
  totalScansThisMonth: number;
  avgScansPerCode: number;
  topCodes: Array<{
    id: string;
    name: string;
    scans: number;
    growthRate: number;
    status: 'active' | 'inactive';
  }>;
  recentScans: Array<{
    id: string;
    codeName: string;
    timestamp: string;
    country: string;
    deviceType: string;
  }>;
  alerts: Array<{
    id: string;
    type: 'warning' | 'error' | 'info' | 'success';
    message: string;
    codeId?: string;
    timestamp: string;
  }>;
}

export interface BatchCSVRow {
  type: QRCodeType;
  content: string;
  name?: string;
  [key: string]: string | undefined;
}

export interface SavedQRCode {
  id: string;
  name: string;
  type: QRCodeType;
  content: string;
  style: QRStyle;
  createdAt: string;
}

export interface QRFormData {
  type: QRCodeType;
  text: string;
  url: string;
  vcard: VCardData;
  wifi: WiFiData;
  email: EmailData;
}

export const artPatterns: Array<{ value: ArtPattern; label: string; description: string }> = [
  { value: 'none', label: '标准', description: '经典二维码样式' },
  { value: 'gradient', label: '渐变', description: '线性渐变色彩' },
  { value: 'rainbow', label: '彩虹', description: '七彩色码点' },
  { value: 'geometric', label: '几何', description: '几何图形装饰' },
  { value: 'abstract', label: '抽象', description: '抽象艺术风格' },
  { value: 'nature', label: '自然', description: '自然元素装饰' },
  { value: 'cyber', label: '赛博', description: '未来科技风格' },
  { value: 'vintage', label: '复古', description: '怀旧复古风格' },
];

export const eyeStyles: Array<{ value: EyeStyle; label: string }> = [
  { value: 'square', label: '方形' },
  { value: 'rounded', label: '圆角' },
  { value: 'circle', label: '圆形' },
  { value: 'heart', label: '爱心' },
  { value: 'star', label: '星形' },
];

export const defaultStyle: QRStyle = {
  foregroundColor: '#1e3a8a',
  backgroundColor: '#ffffff',
  size: 300,
  errorCorrectionLevel: 'H',
  dotStyle: 'square',
  cornerRadius: 0,
  logoSize: 0.2,
  logoBackgroundColor: '#ffffff',
  artPattern: 'none',
  eyeStyle: 'square',
  backgroundStyle: 'solid',
  gradientStart: '#1e3a8a',
  gradientEnd: '#06b6d4',
  gradientType: 'linear',
};

export const defaultVCard: VCardData = {
  firstName: '',
  lastName: '',
  organization: '',
  title: '',
  phone: '',
  email: '',
  website: '',
  address: '',
};

export const defaultWiFi: WiFiData = {
  ssid: '',
  password: '',
  encryption: 'WPA',
  hidden: false,
};

export const defaultEmail: EmailData = {
  to: '',
  subject: '',
  body: '',
};

export const defaultFormData: QRFormData = {
  type: 'url',
  text: '',
  url: 'https://',
  vcard: { ...defaultVCard },
  wifi: { ...defaultWiFi },
  email: { ...defaultEmail },
};
