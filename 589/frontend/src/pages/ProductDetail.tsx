import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Heart,
  Share2,
  Bell,
  ShoppingCart,
  ExternalLink,
  TrendingDown,
  TrendingUp,
  Minus,
  Star,
  Shield,
  Truck,
  RefreshCw,
  Tag,
  Gift,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import PriceChart from '../components/PriceChart';
import PriceComparisonTable from '../components/PriceComparisonTable';
import PriceAlertModal from '../components/PriceAlertModal';
import { productApi, couponApi, alertApi, favoriteApi } from '../services/api';
import { websocketService } from '../services/websocket';
import { useAppStore } from '../store/useAppStore';
import {
  PLATFORM_CONFIG,
  RECOMMENDATION_TEXT,
  type Product,
  type PlatformPrice,
  type PriceHistory,
  type PriceStats,
  type PurchaseRecommendation,
  type Coupon,
} from '../types';
import {
  formatPrice,
  formatDate,
  formatSales,
  formatSavings,
  getLowestPrice,
  getHighestPrice,
  calculatePotentialSavings,
} from '../utils/format';

const mockProduct: Product = {
  id: 'prod-001',
  name: 'Apple iPhone 15 Pro Max 256GB 原色钛金属',
  description: '全新A17 Pro芯片，首款3纳米工艺。钛金属设计，坚固轻盈。专业级摄像系统，支持ProRes视频录制。USB-C接口，支持USB 3.0速度。',
  category: 'phones',
  brand: 'Apple',
  model: 'iPhone 15 Pro Max',
  imageUrl: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Apple%20iPhone%2015%20Pro%20Max%20smartphone%20titanium%20design%20product%20photography%20white%20background&image_size=square',
  createdAt: '2024-01-15T10:00:00Z',
};

const mockPrices: PlatformPrice[] = [
  {
    id: 'price-001',
    productId: 'prod-001',
    platform: 'taobao',
    platformName: '淘宝',
    price: 8999,
    originalPrice: 9999,
    couponPrice: 8799,
    productUrl: 'https://www.taobao.com',
    inStock: true,
    rating: 4.8,
    sales: 15680,
    coupons: [
      {
        id: 'coupon-001',
        platform: 'taobao',
        code: 'TAOBAO200',
        discount: 200,
        discountType: 'fixed',
        minAmount: 8000,
        maxDiscount: 200,
        validFrom: '2024-01-01T00:00:00Z',
        validTo: '2024-12-31T23:59:59Z',
      },
    ],
    lastUpdated: new Date().toISOString(),
  },
  {
    id: 'price-002',
    productId: 'prod-001',
    platform: 'jd',
    platformName: '京东',
    price: 9199,
    originalPrice: 9999,
    couponPrice: 8999,
    productUrl: 'https://www.jd.com',
    inStock: true,
    rating: 4.9,
    sales: 23450,
    coupons: [
      {
        id: 'coupon-002',
        platform: 'jd',
        code: 'JDVIP',
        discount: 5,
        discountType: 'percentage',
        minAmount: 5000,
        maxDiscount: 500,
        validFrom: '2024-01-01T00:00:00Z',
        validTo: '2024-12-31T23:59:59Z',
      },
    ],
    lastUpdated: new Date().toISOString(),
  },
  {
    id: 'price-003',
    productId: 'prod-001',
    platform: 'pdd',
    platformName: '拼多多',
    price: 8799,
    originalPrice: 9999,
    couponPrice: 8599,
    productUrl: 'https://www.pinduoduo.com',
    inStock: true,
    rating: 4.6,
    sales: 35620,
    coupons: [
      {
        id: 'coupon-003',
        platform: 'pdd',
        code: 'PDD200',
        discount: 200,
        discountType: 'fixed',
        minAmount: 8000,
        maxDiscount: 200,
        validFrom: '2024-01-01T00:00:00Z',
        validTo: '2024-12-31T23:59:59Z',
      },
    ],
    lastUpdated: new Date().toISOString(),
  },
  {
    id: 'price-004',
    productId: 'prod-001',
    platform: 'suning',
    platformName: '苏宁',
    price: 9299,
    originalPrice: 9999,
    productUrl: 'https://www.suning.com',
    inStock: false,
    rating: 4.7,
    sales: 8920,
    coupons: [],
    lastUpdated: new Date().toISOString(),
  },
];

const generateMockHistory = (days: number, basePrice: number): PriceHistory[] => {
  const history: PriceHistory[] = [];
  const now = new Date();
  let price = basePrice;

  for (let i = days; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);

    const change = (Math.random() - 0.48) * 200;
    price = Math.max(basePrice * 0.8, Math.min(basePrice * 1.1, price + change));

    history.push({
      date: date.toISOString().split('T')[0],
      price: Math.round(price),
      platform: 'all',
    });
  }

  return history;
};

const mockStats: PriceStats = {
  lowest: 7999,
  highest: 9999,
  average: 8950,
  current: 8799,
  trend: -2.5,
  volatility: 8.3,
  isLowest: false,
};

const mockRecommendation: PurchaseRecommendation = {
  recommendation: 'wait_for_drop',
  confidence: 0.82,
  predictedPrice: 8499,
  bestMonth: '6月',
  currentPrice: 8799,
  savingsIfWait: 300,
};

export default function ProductDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [product, setProduct] = useState<Product | null>(mockProduct);
  const [prices, setPrices] = useState<PlatformPrice[]>(mockPrices);
  const [priceHistory, setPriceHistory] = useState<PriceHistory[]>(generateMockHistory(90, 8999));
  const [stats, setStats] = useState<PriceStats>(mockStats);
  const [recommendation, setRecommendation] = useState<PurchaseRecommendation>(mockRecommendation);
  const [matchedCoupons, setMatchedCoupons] = useState<Coupon[]>(mockPrices.flatMap((p) => p.coupons));
  const [historyDays, setHistoryDays] = useState(30);
  const [showAlertModal, setShowAlertModal] = useState(false);
  const [selectedImage, setSelectedImage] = useState(0);
  const [loading, setLoading] = useState(false);
  const [livePrice, setLivePrice] = useState<number | null>(null);

  const {
    favorites,
    addFavorite,
    removeFavorite,
    addNotification,
    setIsLoading,
  } = useAppStore();

  useEffect(() => {
    loadProductData();
    setupWebSocket();

    return () => {
      websocketService.disconnect();
    };
  }, [id]);

  const setupWebSocket = () => {
    websocketService.connect();

    if (id) {
      websocketService.onPriceUpdate(id, (data) => {
        setLivePrice(data.price);
        console.log('实时价格更新:', data);
      });
    }

    websocketService.onPriceAlert((alert) => {
      addNotification(alert);
    });
  };

  const loadProductData = async () => {
    if (!id) return;

    try {
      setLoading(true);
      const [prod, comparison, history, priceStats, rec] = await Promise.all([
        productApi.getById(id),
        productApi.getPrices(id),
        productApi.getHistory(id, historyDays),
        productApi.getStats(id, historyDays),
        productApi.getRecommendation(id),
      ]);

      setProduct(prod);
      setPrices(comparison.prices);
      setPriceHistory(history);
      setStats(priceStats);
      setRecommendation(rec);

      const couponMatch = await couponApi.match({
        productId: id,
        platform: 'all',
        price: getLowestPrice(comparison.prices),
      });
      setMatchedCoupons(couponMatch.matched);
    } catch (e) {
      console.log('使用模拟商品数据');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) {
      loadProductData();
    }
  }, [id, historyDays]);

  const isFavorite = product ? favorites.some((f) => f.product.id === product.id) : false;

  const handleFavorite = async () => {
    if (!product) return;

    try {
      if (isFavorite) {
        const fav = favorites.find((f) => f.product.id === product.id);
        if (fav) {
          await favoriteApi.remove(fav.id);
          removeFavorite(fav.id);
        }
      } else {
        const result = await favoriteApi.add(product.id);
        if (result.success) {
          addFavorite({
            id: `fav-${Date.now()}`,
            product,
            createdAt: new Date().toISOString(),
          });
        }
      }
    } catch (e) {
      console.log('收藏操作失败');
    }
  };

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: product?.name,
        url: window.location.href,
      });
    } else {
      navigator.clipboard.writeText(window.location.href);
      alert('链接已复制到剪贴板');
    }
  };

  const lowestPrice = getLowestPrice(prices);
  const highestPrice = getHighestPrice(prices);
  const potentialSavings = calculatePotentialSavings(prices);
  const bestDeal = prices.find((p) => (p.couponPrice ?? p.price) === lowestPrice);
  const inStockPrices = prices.filter((p) => p.inStock);

  const displayPrice = livePrice ?? lowestPrice;

  const productImages = [
    product?.imageUrl || '',
    product?.imageUrl?.replace('square', 'portrait_4_3') || '',
    product?.imageUrl?.replace('square', 'landscape_4_3') || '',
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 size={48} className="text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">正在加载商品信息...</p>
        </div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle size={48} className="text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold mb-2">商品不存在</h2>
          <button
            onClick={() => navigate('/')}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            返回首页
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-6">
        <nav className="text-sm text-gray-500 mb-6">
          <button onClick={() => navigate('/')} className="hover:text-blue-600">
            首页
          </button>
          <span className="mx-2">/</span>
          <span className="text-gray-900">{product.name}</span>
        </nav>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <div className="lg:col-span-5">
            <div className="bg-white rounded-2xl p-6 sticky top-24">
              <div className="aspect-square rounded-xl overflow-hidden bg-gray-100 mb-4">
                <img
                  src={productImages[selectedImage]}
                  alt={product.name}
                  className="w-full h-full object-cover"
                />
              </div>
              <div className="flex gap-3">
                {productImages.map((img, idx) => (
                  <button
                    key={idx}
                    onClick={() => setSelectedImage(idx)}
                    className={`w-20 h-20 rounded-lg overflow-hidden border-2 transition-all ${
                      selectedImage === idx ? 'border-blue-600' : 'border-transparent'
                    }`}
                  >
                    <img src={img} alt="" className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={handleFavorite}
                  className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl border transition-all ${
                    isFavorite
                      ? 'bg-red-50 border-red-300 text-red-600'
                      : 'border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  <Heart size={20} fill={isFavorite ? 'currentColor' : 'none'} />
                  {isFavorite ? '已收藏' : '收藏'}
                </button>
                <button
                  onClick={handleShare}
                  className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl border border-gray-300 hover:bg-gray-50 transition-all"
                >
                  <Share2 size={20} />
                  分享
                </button>
              </div>
            </div>
          </div>

          <div className="lg:col-span-7 space-y-6">
            <div className="bg-white rounded-2xl p-6">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    {product.brand && (
                      <span className="px-2 py-1 bg-blue-100 text-blue-700 text-sm rounded-full">
                        {product.brand}
                      </span>
                    )}
                    {stats.isLowest && (
                      <span className="px-2 py-1 bg-red-100 text-red-700 text-sm rounded-full animate-pulse">
                        🔥 历史最低价
                      </span>
                    )}
                    {livePrice && (
                      <span className="px-2 py-1 bg-green-100 text-green-700 text-sm rounded-full flex items-center gap-1">
                        <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                        实时更新
                      </span>
                    )}
                  </div>
                  <h1 className="text-2xl font-bold text-gray-900 mb-3">{product.name}</h1>
                  <p className="text-gray-600 mb-4">{product.description}</p>

                  {product.model && (
                    <div className="text-sm text-gray-500 mb-4">
                      型号：{product.model}
                    </div>
                  )}
                </div>
              </div>

              <div className="bg-gradient-to-r from-orange-50 to-red-50 rounded-xl p-6 mb-6">
                <div className="flex items-end gap-4 mb-4">
                  <div>
                    <div className="text-sm text-gray-600 mb-1">当前最低价</div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-4xl font-bold text-red-600">
                        {formatPrice(displayPrice)}
                      </span>
                      {displayPrice < stats.current && (
                        <span className="flex items-center gap-1 text-green-600 text-sm font-medium">
                          <TrendingDown size={16} />
                          下降 {((1 - displayPrice / stats.current) * 100).toFixed(1)}%
                        </span>
                      )}
                    </div>
                  </div>
                  {highestPrice > displayPrice && (
                    <div className="text-lg text-gray-400 line-through">
                      {formatPrice(highestPrice)}
                    </div>
                  )}
                  {potentialSavings > 0 && (
                    <div className="bg-green-500 text-white px-3 py-1 rounded-full text-sm font-medium">
                      {formatSavings(highestPrice, displayPrice)}
                    </div>
                  )}
                </div>

                {bestDeal && (
                  <div className="flex items-center gap-3 p-3 bg-white rounded-lg">
                    <span className="text-2xl">{PLATFORM_CONFIG[bestDeal.platform]?.logo}</span>
                    <div className="flex-1">
                      <div className="font-medium">{bestDeal.platformName}</div>
                      <div className="text-sm text-gray-500">
                        {bestDeal.coupons.length > 0
                          ? `已使用${bestDeal.coupons.length}张优惠券`
                          : '暂无可用优惠券'}
                      </div>
                    </div>
                    <a
                      href={bestDeal.productUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors"
                    >
                      去购买
                      <ExternalLink size={16} />
                    </a>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="text-center p-4 bg-gray-50 rounded-xl">
                  <div className="text-2xl font-bold text-gray-900">{formatPrice(stats.lowest)}</div>
                  <div className="text-sm text-gray-500">历史最低</div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-xl">
                  <div className="text-2xl font-bold text-gray-900">{formatPrice(stats.average)}</div>
                  <div className="text-sm text-gray-500">历史均价</div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-xl">
                  <div className={`text-2xl font-bold ${stats.trend < 0 ? 'text-green-600' : stats.trend > 0 ? 'text-red-600' : 'text-gray-900'}`}>
                    {stats.trend > 0 ? '+' : ''}{stats.trend.toFixed(1)}%
                  </div>
                  <div className="text-sm text-gray-500">近期趋势</div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-xl">
                  <div className="text-2xl font-bold text-gray-900">{inStockPrices.length}</div>
                  <div className="text-sm text-gray-500">平台在售</div>
                </div>
              </div>

              <div className={`p-4 rounded-xl border-2 ${
                recommendation.recommendation === 'buy_now'
                  ? 'bg-green-50 border-green-200'
                  : recommendation.recommendation === 'wait_for_drop'
                  ? 'bg-orange-50 border-orange-200'
                  : 'bg-blue-50 border-blue-200'
              }`}>
                <div className="flex items-start gap-3">
                  <div className="text-3xl">{RECOMMENDATION_TEXT[recommendation.recommendation]?.icon}</div>
                  <div className="flex-1">
                    <div className={`font-bold text-lg ${RECOMMENDATION_TEXT[recommendation.recommendation]?.color}`}>
                      {RECOMMENDATION_TEXT[recommendation.recommendation]?.text}
                    </div>
                    <div className="text-sm text-gray-600 mt-1">
                      置信度 {(recommendation.confidence * 100).toFixed(0)}%
                      {recommendation.predictedPrice && (
                        <span className="ml-2">
                          · 预测价格 {formatPrice(recommendation.predictedPrice)}
                        </span>
                      )}
                      {recommendation.bestMonth && (
                        <span className="ml-2">· 最佳购买月份 {recommendation.bestMonth}</span>
                      )}
                      {recommendation.savingsIfWait > 0 && (
                        <span className="ml-2">
                          · 预计可省 {formatPrice(recommendation.savingsIfWait)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold">价格走势</h2>
                <div className="flex gap-2">
                  {[7, 30, 90, 365].map((days) => (
                    <button
                      key={days}
                      onClick={() => setHistoryDays(days)}
                      className={`px-4 py-1.5 text-sm rounded-lg transition-colors ${
                        historyDays === days
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {days === 7 ? '7天' : days === 30 ? '30天' : days === 90 ? '90天' : '全年'}
                    </button>
                  ))}
                </div>
              </div>
              <PriceChart history={priceHistory} stats={stats} height={300} />
            </div>

            {matchedCoupons.length > 0 && (
              <div className="bg-white rounded-2xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Tag className="text-orange-500" size={24} />
                  <h2 className="text-xl font-bold">可用优惠券</h2>
                  <span className="text-sm text-gray-500">（已自动匹配）</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {matchedCoupons.map((coupon) => (
                    <div
                      key={coupon.id}
                      className="flex items-center gap-4 p-4 bg-gradient-to-r from-red-50 to-orange-50 rounded-xl border border-orange-200"
                    >
                      <div className="text-center">
                        <div className="text-2xl font-bold text-red-600">
                          {coupon.discountType === 'percentage' ? `${coupon.discount}%` : formatPrice(coupon.discount)}
                        </div>
                        <div className="text-xs text-gray-500">
                          {coupon.discountType === 'percentage' ? '折扣' : '立减'}
                        </div>
                      </div>
                      <div className="flex-1">
                        <div className="font-medium">满{formatPrice(coupon.minAmount)}可用</div>
                        <div className="text-sm text-gray-500">
                          {PLATFORM_CONFIG[coupon.platform]?.name} · 有效期至 {formatDate(coupon.validTo)}
                        </div>
                      </div>
                      <button className="px-4 py-2 bg-red-500 text-white rounded-lg text-sm font-medium hover:bg-red-600 transition-colors">
                        领取
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="bg-white rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold">多平台比价</h2>
                <button
                  onClick={() => loadProductData()}
                  className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
                >
                  <RefreshCw size={16} />
                  刷新价格
                </button>
              </div>
              <PriceComparisonTable prices={prices} onSetAlert={() => setShowAlertModal(true)} />
            </div>

            <div className="bg-white rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Bell className="text-blue-500" size={24} />
                <h2 className="text-xl font-bold">价格提醒</h2>
              </div>
              <div className="p-4 bg-blue-50 rounded-xl mb-4">
                <p className="text-sm text-blue-800">
                  设置目标价格，当商品降价到您期望的价格时，我们会第一时间通知您。
                </p>
              </div>
              <button
                onClick={() => setShowAlertModal(true)}
                className="w-full flex items-center justify-center gap-2 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition-colors"
              >
                <Bell size={20} />
                设置降价提醒
              </button>
            </div>

            <div className="bg-white rounded-2xl p-6">
              <h2 className="text-xl font-bold mb-4">服务保障</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="flex flex-col items-center gap-2 p-4 text-center">
                  <Shield className="text-green-500" size={32} />
                  <div className="text-sm font-medium">正品保障</div>
                  <div className="text-xs text-gray-500">平台官方渠道</div>
                </div>
                <div className="flex flex-col items-center gap-2 p-4 text-center">
                  <Truck className="text-blue-500" size={32} />
                  <div className="text-sm font-medium">极速配送</div>
                  <div className="text-xs text-gray-500">多仓发货</div>
                </div>
                <div className="flex flex-col items-center gap-2 p-4 text-center">
                  <RefreshCw className="text-orange-500" size={32} />
                  <div className="text-sm font-medium">7天无理由</div>
                  <div className="text-xs text-gray-500">退换无忧</div>
                </div>
                <div className="flex flex-col items-center gap-2 p-4 text-center">
                  <Gift className="text-purple-500" size={32} />
                  <div className="text-sm font-medium">优惠券</div>
                  <div className="text-xs text-gray-500">自动匹配最优</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {showAlertModal && product && (
        <PriceAlertModal
          product={product}
          prices={prices}
          onClose={() => setShowAlertModal(false)}
          onSave={async (data) => {
            try {
              await alertApi.create(data);
              setShowAlertModal(false);
            } catch (e) {
              console.log('创建提醒失败');
            }
          }}
        />
      )}
    </div>
  );
}
