export interface User {
  _id: string;
  username: string;
  email: string;
  avatar?: string;
  role: 'user' | 'creator' | 'admin';
  bio?: string;
  createdAt: string;
}

export interface TemplateComponent {
  id: string;
  type: 'chart' | 'metric' | 'table' | 'text' | 'image';
  chartType?: 'line' | 'bar' | 'pie' | 'area' | 'gauge';
  title: string;
  position: { x: number; y: number };
  size: { w: number; h: number };
  config: Record<string, any>;
  dataSource: {
    type: 'static' | 'api' | 'database';
    data?: any[];
    apiUrl?: string;
    fields?: Array<{
      sourceField: string;
      targetField: string;
      label: string;
    }>;
  };
}

export interface LayoutConfig {
  gridCols: number;
  gridRows: number;
  gutter: number;
  backgroundColor: string;
}

export interface Template {
  _id: string;
  title: string;
  description: string;
  category: 'operation' | 'sales' | 'finance' | 'ops';
  thumbnail: string;
  previewImages: string[];
  fileUrl: string;
  author: User;
  price: number;
  rating: number;
  ratingCount: number;
  downloadCount: number;
  viewCount: number;
  tags: string[];
  complexity: 'simple' | 'medium' | 'complex';
  components: TemplateComponent[];
  layout: LayoutConfig;
  version: string;
  status: 'pending' | 'approved' | 'rejected';
  rejectReason?: string;
  reviewNote?: string;
  reviewedAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface CommentReply {
  _id: string;
  user: User;
  content: string;
  createdAt: string;
}

export interface Comment {
  _id: string;
  templateId: string;
  user: User;
  content: string;
  rating: number;
  createdAt: string;
  replies: CommentReply[];
}

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  pages: number;
}

export interface ApiResponse<T> {
  message: string;
  data?: T;
}

export interface TemplateListResponse {
  templates: Template[];
  pagination: Pagination;
}

export interface CommentListResponse {
  comments: Comment[];
  pagination: Pagination;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface LoginForm {
  email: string;
  password: string;
}

export interface RegisterForm {
  username: string;
  email: string;
  password: string;
}

export interface TemplateFilter {
  category?: string;
  complexity?: string;
  sort?: string;
  order?: string;
  search?: string;
  minRating?: number;
  page?: number;
  limit?: number;
}

export interface Statistics {
  templateCount: number;
  totalDownloads: number;
  totalViews: number;
  avgRating: number;
}
