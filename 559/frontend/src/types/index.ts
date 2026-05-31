export interface LiveData {
  current_viewers: number;
  total_clicks: number;
  total_orders: number;
  conversion_rate: number;
  heat_score: number;
  viewer_trend: TrendData[];
  heat_trend: TrendData[];
  product_clicks: Record<string, number>;
  product_orders: Record<string, OrderData>;
  category_data: Record<string, CategoryData>;
  chat_analysis: ChatAnalysis;
  sentiment_analysis: SentimentSummary;
  hot_words: HotWord[];
  hot_word_categories: Record<string, HotWordCategory>;
  guided_scripts: GuidedScript[];
  recommended_products: OptimizedProduct[];
  competitor_data: Record<string, CompetitorRealtimeData>;
  user_persona: UserPersona;
  virtual_streamer: VirtualStreamerStatus;
  streamer_action: StreamerAction;
  hot_predictions: HotPrediction[];
  timestamp: string;
}

export interface TrendData {
  timestamp: string;
  count?: number;
  score?: number;
}

export interface OrderData {
  count: number;
  amount: number;
}

export interface CategoryData {
  clicks: number;
  orders: number;
}

export interface ChatAnalysis {
  question: number;
  praise: number;
  complaint: number;
  neutral: number;
}

export interface SentimentSummary {
  positive_ratio: number;
  negative_ratio: number;
  neutral_ratio: number;
  intent_buy_ratio: number;
  overall_score: number;
  trend: 'rising' | 'declining' | 'stable';
}

export interface HotWord {
  word: string;
  count: number;
  category: string;
}

export interface HotWordCategory {
  total_count: number;
  top_words: { word: string; count: number }[];
  heat_level: 'high' | 'medium' | 'low';
}

export interface GuidedScript {
  type: string;
  priority: 'urgent' | 'high' | 'medium';
  script: string;
  reason: string;
}

export interface OptimizedProduct {
  id: number;
  name: string;
  price: number;
  cost: number;
  category: string;
  stock: number;
  initial_stock: number;
  click_rate: number;
  profit_rate: number;
  stock_urgency: number;
  stock_status: 'danger' | 'warning' | 'normal';
  composite_score: number;
  persona_boosted: boolean;
  objectives: {
    click_rate: number;
    profit_rate: number;
    stock_urgency: number;
  };
}

export interface CompetitorRealtimeData {
  timestamp: string;
  competitor_id: number;
  competitor_name: string;
  product: string;
  product_id: number;
  current_price: number;
  price_trend: 'up' | 'down' | 'stable';
  viewer_count: number;
  sales_volume: number;
  update_latency_ms: number;
  our_price: number;
  price_diff: number;
  price_advantage: boolean;
  price_history: {
    timestamp: string;
    price: number;
    viewers: number;
  }[];
}

export interface UserPersona {
  total_users: number;
  age_distribution: Record<string, number>;
  gender_distribution: Record<string, number>;
  interest_distribution: Record<string, number>;
  consume_level_distribution: Record<string, number>;
  region_distribution: Record<string, number>;
  top_interests: string[];
  price_sensitivity: number;
  interest_multiplier: number;
  price_multiplier: number;
}

export interface VirtualStreamerStatus {
  name: string;
  avatar: string;
  state: string;
  state_label: string;
  current_product: string;
  current_script: string;
  total_speeches: number;
  script_history: {
    timestamp: string;
    state: string;
    product: string;
    script: string;
  }[];
  is_active: boolean;
}

export interface StreamerAction {
  state: string;
  product: string;
  script: string;
  auto_action: {
    type: string;
    product: string;
    stock: number;
  } | null;
}

export interface HotPrediction {
  id: number;
  name: string;
  price: number;
  category: string;
  stock: number;
  hot_score: number;
  prediction_level: 'explosive' | 'rising' | 'potential' | 'stable';
  metrics: {
    click_velocity: number;
    order_velocity: number;
    click_acceleration: number;
    order_acceleration: number;
    sentiment_momentum: number;
  };
  estimated_peak_minutes: number | null;
  stock_burn_rate: number;
  recommendation: string;
}
