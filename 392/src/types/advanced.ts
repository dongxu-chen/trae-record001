import { Icon } from './index';

export interface IconStyle {
  id: string;
  name: string;
  description: string;
  keywords: string[];
  colorPalette: string[];
  complexity: 'simple' | 'medium' | 'complex';
  roundedness: 'sharp' | 'medium' | 'rounded';
  strokeWidth: 'thin' | 'medium' | 'thick';
}

export interface UserStyleProfile {
  preferredStyles: string[];
  preferredColors: string[];
  recentCategories: string[];
  usageCount: Record<string, number>;
  averageComplexity: number;
}

export interface StyleRecommendation {
  style: IconStyle;
  confidence: number;
  reason: string;
}

export interface OutdatedIcon {
  oldIconId: string;
  oldIconName: string;
  newIconId: string;
  newIconName: string;
  reason: string;
  improvement: string;
}

export interface BrandDetectionResult {
  icon: Icon;
  confidence: number;
  position: { x: number; y: number; width: number; height: number };
}

export interface BrandAnalysis {
  detectedIcons: BrandDetectionResult[];
  dominantColors: string[];
  style: IconStyle;
  recommendations: string[];
}
