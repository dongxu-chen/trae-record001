import React, { useState, useEffect } from 'react';
import { TrendingDown, Clock, ArrowDown, Filter, SlidersHorizontal } from 'lucide-react';
import ProductCard from '../components/ProductCard';
import { productApi } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import type { HotProduct, Product } from '../types';
import { formatPrice, formatSavings } from '../utils/format';

const mockProducts: Product[] = [
  {
    id: 'prod-001',
    name: 'Apple iPhone 15 Pro Max 256GB 原色钛金属',
    description: 'A17 Pro芯片，钛金属设计，4800万像素主摄',
    category: 'phones',
    brand: 'Apple',
    model: 'iPhone 15 Pro Max',
    imageUrl: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Apple%20iPhone%2015%20Pro%20Max%20smartphone%20titanium%20design%20product%20photography%20white%20background&image_size=square',
    createdAt: '2024-01-15T10:00:00Z',
  },
  {
    id: 'prod-002',
    name: 'MacBook Pro 14英寸 M3 Pro 18GB 512GB',
    description: 'M3 Pro芯片，Liquid Retina XDR显示屏，18小时续航',
    category: 'computers',
    brand: 'Apple',
    model: 'MacBook Pro 14',
    imageUrl: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=MacBook%20Pro%2014%20inch%20laptop%20silver%20product%20photography%20white%20background&image_size=square',
    createdAt: '2024-01-10T10:00:00Z',
  },
  {
    id: 'prod-003',
    name: 'Sony WH-1000XM5 无线降噪耳机 黑色',
    description: '业界领先降噪，30小时续航，多点连接',
    category: 'electronics',
    brand: 'Sony',
    model: 'WH-1000XM5',
    imageUrl: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Sony%20WH-1000XM5%20wireless%20noise%20cancelling%20headphones%20black%20product%20photography&image_size=square',
    createdAt: '2024-01-08T10:00:00Z',
  },
  {
    id: 'prod-004',
    name: '戴森 V15 Detect Absolute 无线吸尘器',
    description: '激光探测灰尘，智能感应吸力，60分钟续航',
    category: 'home',
    brand: 'Dyson',
    model: 'V15 Detect',
    imageUrl: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Dyson%20V15%20cordless%20vacuum%20cleaner%20product%20photography%20white%20background&image_size=square',
    createdAt: '2024-01-05T10:00:00Z',
  },
  {
    id: 'prod-005',
    name: 'Nike Air Max 270 男子运动鞋 黑白',
    description: '经典气垫设计，舒适缓震，时尚百搭',
    category: 'sports',
    brand: 'Nike',
    model: 'Air Max 270',
    imageUrl: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Nike%20Air%20Max%20270%20sneakers%20black%20white%20product%20photography&image_size=square',
    createdAt: '2024-01-03T10:00:00Z',
  },
  {
    id: 'prod-006',
    name: 'SK-II 神仙水护肤精华露 230ml',
    description: '90%以上PITERA精华，改善肤质，提亮肤色',
    category: 'beauty',
    brand: 'SK-II',
    model: 'Facial Treatment Essence',
    imageUrl: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=SKII%20facial%20treatment%20essence%20bottle%20luxury%20skincare%20product%20photography&image_size=square',
    createdAt: '2024-01-01T10:00:00Z',
  },
  {
    id: 'prod-007',
    name: '华为 Mate 60 Pro 12GB+512GB 雅川青',
    description: '麒麟9000S芯片，卫星通话，超可靠玄武架构',
    category: 'phones',
    brand: '华为',
    model: 'Mate 60 Pro',
    imageUrl: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Huawei%20Mate%2060%20Pro%20smartphone%20green%20product%20photography&image_size=square',
    createdAt: '2024-01-01T10:00:00Z',
  },
  {
    id: 'prod-008',
    name: '小米14 Ultra 16GB+512GB 黑色',
    description: '徕卡Summilux镜头，骁龙8 Gen3，超大底主摄',
    category: 'phones',
    brand: '小米',
    model: '14 Ultra',
    imageUrl: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Xiaomi%2014%20Ultra%20smartphone%20black%20product%20photography&image_size=square',
    createdAt: '2024-01-01T10:00:00Z',
  },
];

const mockHotProducts: HotProduct[] = mockProducts.map((p, i) => ({
  product: p,
  bestPrice: [8999, 14999, 2299, 4990, 899, 1590, 6999, 5999][i],
  lowestEver: [7999, 13999, 1999, 4490, 699, 1290, 5999, 4999][i],
  potentialSavings: [1500, 2000, 500, 800, 300, 500, 1200, 1500][i],
}));

const TIME_RANGES = [
  { value: '24h', label: '24小时' },
  { value: '7d', label: '7天' },
  { value: '30d', label: '30天' },
];

const CATEGORIES = [
  { value: 'all', label: '全部' },
  { value: 'phones', label: '手机' },
  { value: 'computers', label: '电脑' },
  { value: 'electronics', label: '数码' },
  { value: 'home', label: '家电' },
  { value: 'beauty', label: '美妆' },
  { value: 'sports', label: '运动' },
];

export default function HotDrops() {
  const [hotProducts, setHotProducts] = useState<HotProduct[]>(mockHotProducts);
  const [timeRange, setTimeRange] = useState('7d');
  const [category, setCategory] = useState('all');
  const [minDiscount, setMinDiscount] = useState(0);
  const [loading, setLoading] = useState(false);

  const { setIsLoading } = useAppStore();

  useEffect(() => {
    loadHotProducts();
  }, [timeRange, category]);

  const loadHotProducts = async () => {
    try {
      setLoading(true);
      const data = await productApi.getHot(20);
      if (data && data.length > 0) {
        setHotProducts(data);
      }
    } catch (e) {
      console.log('使用模拟数据');
    } finally {
      setLoading(false);
    }
  };

  const filteredProducts = hotProducts.filter((item) => {
    const discountPercent = ((item.potentialSavings / (item.bestPrice + item.potentialSavings)) * 100);
    if (discountPercent < minDiscount) return false;
    if (category !== 'all' && item.product.category !== category) return false;
    return true;
  });

  const sortedProducts = [...filteredProducts].sort((a, b) => {
    const discountA = (a.potentialSavings / (a.bestPrice + a.potentialSavings)) * 100;
    const discountB = (b.potentialSavings / (b.bestPrice + b.potentialSavings)) * 100;
    return discountB - discountA;
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-gradient-to-r from-red-600 to-orange-500 text-white py-12 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center gap-3 mb-2">
            <TrendingDown size={32} />
            <h1 className="text-3xl font-bold">🔥 热门降价</h1>
          </div>
          <p className="text-white/80 text-lg">
            实时监控全网商品价格，为您精选近期降价幅度最大的商品
          </p>
          <div className="flex items-center gap-6 mt-6">
            <div className="text-center">
              <div className="text-3xl font-bold">{sortedProducts.length}</div>
              <div className="text-sm text-white/70">降价商品</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold">
                {sortedProducts.length > 0
                  ? `¥${Math.max(...sortedProducts.map((p) => p.potentialSavings))}`
                  : '¥0'}
              </div>
              <div className="text-sm text-white/70">最大降幅</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold">4</div>
              <div className="text-sm text-white/70">覆盖平台</div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="bg-white rounded-2xl p-6 mb-6 shadow-sm">
          <div className="flex flex-wrap items-center gap-6">
            <div className="flex items-center gap-2">
              <Clock size={18} className="text-gray-500" />
              <span className="text-sm text-gray-600">时间范围：</span>
              <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
                {TIME_RANGES.map((range) => (
                  <button
                    key={range.value}
                    onClick={() => setTimeRange(range.value)}
                    className={`px-4 py-1.5 text-sm rounded-md transition-colors ${
                      timeRange === range.value
                        ? 'bg-white text-red-600 font-medium shadow-sm'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    {range.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Filter size={18} className="text-gray-500" />
              <span className="text-sm text-gray-600">分类：</span>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <ArrowDown size={18} className="text-gray-500" />
              <span className="text-sm text-gray-600">最低降幅：</span>
              <select
                value={minDiscount}
                onChange={(e) => setMinDiscount(Number(e.target.value))}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                <option value={0}>全部</option>
                <option value={5}>5%以上</option>
                <option value={10}>10%以上</option>
                <option value={15}>15%以上</option>
                <option value={20}>20%以上</option>
                <option value={30}>30%以上</option>
              </select>
            </div>
          </div>
        </div>

        {sortedProducts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <TrendingDown size={60} className="text-gray-300 mb-4" />
            <h3 className="text-xl font-medium text-gray-700 mb-2">暂无符合条件的降价商品</h3>
            <p className="text-gray-500">试试调整筛选条件</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {sortedProducts.map((item, index) => {
              const discountPercent = (
                (item.potentialSavings / (item.bestPrice + item.potentialSavings)) *
                100
              ).toFixed(1);
              return (
                <div key={item.product.id} className="relative">
                  {index < 3 && (
                    <div
                      className={`absolute -top-2 -left-2 z-10 w-10 h-10 rounded-full flex items-center justify-center text-white font-bold shadow-lg ${
                        index === 0
                          ? 'bg-gradient-to-br from-yellow-400 to-orange-500'
                          : index === 1
                          ? 'bg-gradient-to-br from-gray-300 to-gray-500'
                          : 'bg-gradient-to-br from-amber-600 to-amber-800'
                      }`}
                    >
                      {index + 1}
                    </div>
                  )}
                  <div className="absolute top-3 right-3 z-10">
                    <span className="bg-red-500 text-white text-xs font-bold px-2 py-1 rounded-full">
                      -{discountPercent}%
                    </span>
                  </div>
                  <ProductCard
                    product={item.product}
                    bestPrice={item.bestPrice}
                    lowestEver={item.lowestEver}
                    potentialSavings={item.potentialSavings}
                  />
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
