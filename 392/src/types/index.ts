export interface Icon {
  id: string;
  name: string;
  library: 'fontawesome' | 'material' | 'custom';
  svgPath: string;
  tags: string[];
  category: string;
}

export interface UploadedIcon extends Icon {
  svg: string;
  createdAt: number;
}

export interface FavoriteItem {
  iconId: string;
  addedAt: number;
}

export interface RecentItem {
  iconId: string;
  usedAt: number;
}

export type IconLibrary = 'fontawesome' | 'material' | 'custom';

export type ViewMode = 'grid' | 'list';

export interface UserPreferences {
  theme: 'dark' | 'light';
  defaultLibrary: IconLibrary;
  viewMode: ViewMode;
}

export interface CopyFormat {
  format: 'svg' | 'jsx';
  color: string;
  size: number;
}
