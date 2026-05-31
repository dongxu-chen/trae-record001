import React, { useState, useEffect, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Search, Filter, SlidersHorizontal, Grid3X3, List, ChevronDown, Loader2 } from 'lucide-react';
import ProductCard from '../components/ProductCard';
import { productApi, favoriteApi } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import type { Product, PlatformPrice } from '../types';
import { formatPrice } from '../utils/format';

const SORT_OPTIONS = [
  { value: 'default', label: '综合排序' },
  { value: 'price_asc', label: '价格从低到高' },
  { value: 'price_desc', label: '价格从高到低' },
  { value: 'discount', label: '优惠幅度' },
  { value: 'sales', label: '销量优先' },
];

const PRICE_RANGES = [
  { min: 0, max: 100, label: '¥0 - ¥100' },
  { min: 100, max: 500, label: '¥100 - ¥500' },
  { min: 500, max: 1000, label: '¥500 - ¥1000' },
  { min: 1000, max: 5000, label: '¥1000 - ¥5000' },
  { min: 5000, max: Infinity, label: '¥5000以上' },
];

const PLATFORM_FILTERS = [
  { value: 'all', label: '全部平台', logo: '🛍️' },
  { value: 'taobao', label: '淘宝', logo: '🐱' },
  { value: 'jd', label: '京东', logo: '🐕' },
  { value: 'pdd', label: '拼多多', logo: '🛒' },
  { value: 'suning', label: '苏宁', logo: '🏬' },
];

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
    name: 'Apple iPhone 15 128GB 黑色',
    description: 'A16仿生芯片，灵动岛设计，4800万像素主摄',
    category: 'phones',
    brand: 'Apple',
    model: 'iPhone 15',
    imageUrl: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Apple%20iPhone%2015%20black%20smartphone%20product%20photography&image_size=square',
    createdAt: '2024-01-15T10:00:00Z',
  },
  {
    id: 'prod-003',
    name: 'Apple iPhone 15 Pro 256GB 蓝色钛金属',
    description: 'A17 Pro芯片，钛金属设计，专业级摄像系统',
    category: 'phones',
    brand: 'Apple',
    model: 'iPhone 15 Pro',
    imageUrl: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Apple%20iPhone%2015%20Pro%20blue%20titanium%20smartphone%20product%20photography&image_size=square',
    createdAt: '2024-01-15T10:00:00Z',
  },
  {
    id: 'prod-004',
    name: 'Apple iPhone 15 Plus 256GB 粉色',
    description: 'A16仿生芯片，6.7英寸超视网膜XDR显示屏',
    category: 'phones',
    brand: 'Apple',
    model: 'iPhone 15 Plus',
    imageUrl: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Apple%20iPhone%2015%20Plus%20pink%20smartphone%20product%20photography&image_size=square',
    createdAt: '2024-01-15T10:00:00Z',
  },
  {
    id: 'prod-005',
    name: 'Apple AirPods Pro 2 无线蓝牙耳机',
    description: 'H2芯片，主动降噪，自适应通透模式',
    category: 'electronics',
    brand: 'Apple',
    model: 'AirPods Pro 2',
    imageUrl: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Apple%20AirPods%20Pro%202%20wireless%20earbuds%20product%20photography&image_size=square',
    createdAt: '2024-01-15T10:00:00Z',
  },
  {
    id: 'prod-006',
    name: 'Apple Watch Series 9 GPS 45mm 午夜色',
    description: 'S9芯片，双击手势，健康监测',
    category: 'electronics',
    brand: 'Apple',
    model: 'Watch Series 9',
    imageUrl: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Apple%20Watch%20Series%209%20midnight%20product%20photography&image_size=square',
    createdAt: '2024-01-15T10:00:00Z',
  },
];

const mockPrices: Record<string, PlatformPrice[]> = {
  'prod-001': [
    { id: 'p1', productId: 'prod-001', platform: 'taobao', platformName: '淘宝', price: 8999, originalPrice: 9999, productUrl: '', inStock: true, rating: 4.8, sales: 5000, coupons: [], lastUpdated: '' },
    { id: 'p2', productId: 'prod-001', platform: 'jd', platformName: '京东', price: 9199, originalPrice: 9999, productUrl: '', inStock: true, rating: 4.9, sales: 8000, coupons: [], lastUpdated: '' },
    { id: 'p3', productId: 'prod-001', platform: 'pdd', platformName: '拼多多', price: 8799, originalPrice: 9999, productUrl: '', inStock: true, rating: 4.6, sales: 12000, coupons: [], lastUpdated: '' },
  ],
  'prod-002': [
    { id: 'p4', productId: 'prod-002', platform: 'taobao', platformName: '淘宝', price: 5499, originalPrice: 5999, productUrl: '', inStock: true, rating: 4.8, sales: 15000, coupons: [], lastUpdated: '' },
    { id: 'p5', productId: 'prod-002', platform: 'jd', platformName: '京东', price: 5599, originalPrice: 5999, productUrl: '', inStock: true, rating: 4.9, sales: 20000, coupons: [], lastUpdated: '' },
  ],
  'prod-003': [
    { id: 'p6', productId: 'prod-003', platform: 'pdd', platformName: '拼多多', price: 7499, originalPrice: 7999, productUrl: '', inStock: true, rating: 4.7, sales: 6000, coupons: [], lastUpdated: '' },
    { id: 'p7', productId: 'prod-003', platform: 'suning', platformName: '苏宁', price: 7799, originalPrice: 7999, productUrl: '', inStock: true, rating: 4.8, sales: 3000, coupons: [], lastUpdated: '' },
  ],
  'prod-004': [
    { id: 'p8', productId: 'prod-004', platform: 'taobao', platformName: '淘宝', price: 6499, originalPrice: 6999, productUrl: '', inStock: true, rating: 4.8, sales: 8000, coupons: [], lastUpdated: '' },
  ],
  'prod-005': [
    { id: 'p9', productId: 'prod-005', platform: 'jd', platformName: '京东', price: 1799, originalPrice: 1999, productUrl: '', inStock: true, rating: 4.9, sales: 25000, coupons: [], lastUpdated: '' },
    { id: 'p10', productId: 'prod-005', platform: 'taobao', platformName: '淘宝', price: 1699, originalPrice: 1999, productUrl: '', inStock: true, rating: 4.8, sales: 18000, coupons: [], lastUpdated: '' },
  ],
  'prod-006': [
    { id: 'p11', productId: 'prod-006', platform: 'jd', platformName: '京东', price: 3199, originalPrice: 3499, productUrl: '', inStock: true, rating: 4.9, sales: 10000, coupons: [], lastUpdated: '' },
  ],
};

export default function SearchResults() {
  const location = useLocation();
  const navigate = useNavigate();
  const [products, setProducts] = useState<Product[]>(mockProducts);
  const [prices, setPrices] = useState<Record<string, PlatformPrice[]>>(mockPrices);
  const [total, setTotal] = useState(48);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [sortBy, setSortBy] = useState('default');
  const [priceRange, setPriceRange] = useState<{ min: number; max: number } | null>(null);
  const [platformFilter, setPlatformFilter] = useState('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [showFilters, setShowFilters] = useState(false);
  const [loading, setLoading] = useState(false);

  const { setIsLoading, favorites, setFavorites, addFavorite, removeFavorite } = useAppStore();

  const searchParams = new URLSearchParams(location.search);
  const query = searchParams.get('q') || '';
  const category = searchParams.get('category') || '';

  useEffect(() => {
    loadSearchResults();
  }, [location.search]);

  const loadSearchResults = async () => {
    try {
      setLoading(true);
      const result = await productApi.search(query, page, pageSize, category);
      if (result && result.items.length > 0) {
        setProducts(result.items);
        setTotal(result.total);
      }
    } catch (e) {
      console.log('使用模拟搜索数据');
    } finally {
      setLoading(false);
    }
  };

  const filteredAndSortedProducts = useMemo(() => {
    let result = [...products];

    if (priceRange) {
      result = result.filter((p) => {
        const productPrices = prices[p.id] || [];
        if (productPrices.length === 0) return false;
        const minPrice = Math.min(...productPrices.map((pr) => pr.price));
        return minPrice >= priceRange.min && minPrice <= priceRange.max;
      });
    }

    if (platformFilter !== 'all') {
      result = result.filter((p) => {
        const productPrices = prices[p.id] || [];
        return productPrices.some((pr) => pr.platform === platformFilter);
      });
    }

    switch (sortBy) {
      case 'price_asc':
        result.sort((a, b) => {
          const priceA = Math.min(...(prices[a.id] || []).map((p) => p.price));
          const priceB = Math.min(...(prices[b.id] || []).map((p) => p.price));
          return priceA - priceB;
        });
        break;
      case 'price_desc':
        result.sort((a, b) => {
          const priceA = Math.min(...(prices[a.id] || []).map((p) => p.price));
          const priceB = Math.min(...(prices[b.id] || []).map((p) => p.price));
          return priceB - priceA;
        });
        break;
      case 'discount':
        result.sort((a, b) => {
          const pricesA = prices[a.id] || [];
          const pricesB = prices[b.id] || [];
          const discountA = pricesA.length > 0 ? Math.max(...pricesA.map((p) => p.originalPrice - p.price)) : 0;
          const discountB = pricesB.length > 0 ? Math.max(...pricesB.map((p) => p.originalPrice - p.price)) : 0;
          return discountB - discountA;
        });
        break;
      case 'sales':
        result.sort((a, b) => {
          const salesA = Math.max(...(prices[a.id] || []).map((p) => p.sales || 0));
          const salesB = Math.max(...(prices[b.id] || []).map((p) => p.sales || 0));
          return salesB - salesA;
        });
        break;
    }

    return result;
  }, [products, prices, sortBy, priceRange, platformFilter]);

  const handleFavorite = async (productId: string) => {
    try {
      const existing = favorites.find((f) => f.product.id === productId);
      if (existing) {
        await favoriteApi.remove(existing.id);
        removeFavorite(existing.id);
      } else {
        const result = await favoriteApi.add(productId);
        const product = products.find((p) => p.id === productId);
        if (product && result.success) {
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

  const isFavorite = (productId: string) => {
    return favorites.some((f) => f.product.id === productId);
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b sticky top-16 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                {query ? `"${query}"` : category ? '分类商品' : '全部商品'}
                <span className="text-sm font-normal text-gray-500 ml-2">
                  共 {filteredAndSortedProducts.length} 件商品
                </span>
              </h1>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                  showFilters ? 'bg-blue-50 border-blue-500 text-blue-600' : 'border-gray-300 hover:bg-gray-50'
                }`}
              >
                <Filter size={18} />
                筛选
              </button>
              <div className="flex items-center bg-gray-100 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('grid')}
                  className={`p-2 rounded ${viewMode === 'grid' ? 'bg-white shadow' : 'text-gray-500'}`}
                >
                  <Grid3X3 size={18} />
                </button>
                <button
                  onClick={() => setViewMode('list')}
                  className={`p-2 rounded ${viewMode === 'list' ? 'bg-white shadow' : 'text-gray-500'}`}
                >
                  <List size={18} />
                </button>
              </div>
            </div>
          </div>

          {showFilters && (
            <div className="bg-gray-50 rounded-xl p-4 mb-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">平台筛选</label>
                <div className="flex flex-wrap gap-2">
                  {PLATFORM_FILTERS.map((platform) => (
                    <button
                      key={platform.value}
                      onClick={() => setPlatformFilter(platform.value)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm transition-colors ${
                        platformFilter === platform.value
                          ? 'bg-blue-600 text-white'
                          : 'bg-white border border-gray-300 hover:border-blue-400'
                      }`}
                    >
                      <span>{platform.logo}</span>
                      {platform.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">价格区间</label>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => setPriceRange(null)}
                    className={`px-4 py-2 rounded-full text-sm transition-colors ${
                      !priceRange ? 'bg-blue-600 text-white' : 'bg-white border border-gray-300 hover:border-blue-400'
                    }`}
                  >
                    全部
                  </button>
                  {PRICE_RANGES.map((range) => (
                    <button
                      key={range.label}
                      onClick={() => setPriceRange(range)}
                      className={`px-4 py-2 rounded-full text-sm transition-colors ${
                        priceRange?.min === range.min && priceRange?.max === range.max
                          ? 'bg-blue-600 text-white'
                          : 'bg-white border border-gray-300 hover:border-blue-400'
                      }`}
                    >
                      {range.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <SlidersHorizontal size={16} className="text-gray-500" />
              <span className="text-sm text-gray-600">排序：</span>
              {SORT_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setSortBy(option.value)}
                  className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                    sortBy === option.value
                      ? 'bg-blue-100 text-blue-700 font-medium'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 size={40} className="text-blue-600 animate-spin mb-4" />
            <p className="text-gray-500">正在搜索商品...</p>
          </div>
        ) : filteredAndSortedProducts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Search size={60} className="text-gray-300 mb-4" />
            <h3 className="text-xl font-medium text-gray-700 mb-2">没有找到相关商品</h3>
            <p className="text-gray-500 mb-4">试试其他关键词或筛选条件</p>
            <button
              onClick={() => navigate('/')}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              返回首页
            </button>
          </div>
        ) : (
          <>
            <div
              className={`grid gap-6 ${
                viewMode === 'grid'
                  ? 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5'
                  : 'grid-cols-1'
              }`}
            >
              {filteredAndSortedProducts.map((product) => (
                viewMode === 'grid' ? (
                  <ProductCard
                    key={product.id}
                    product={product}
                    prices={prices[product.id]}
                    onFavorite={handleFavorite}
                    isFavorite={isFavorite(product.id)}
                  />
                ) : (
                  <div
                    key={product.id}
                    className="flex gap-4 p-4 bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow border"
                  >
                    <div className="w-40 h-40 flex-shrink-0 rounded-lg overflow-hidden bg-gray-100">
                      <img
                        src={product.imageUrl}
                        alt={product.name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-medium text-gray-900 mb-2 hover:text-blue-600 cursor-pointer">
                        {product.name}
                      </h3>
                      <p className="text-sm text-gray-500 mb-3 line-clamp-2">{product.description}</p>
                      <div className="flex items-center gap-4 mb-3">
                        {prices[product.id]?.slice(0, 4).map((p) => (
                          <div key={p.id} className="flex items-center gap-1 text-sm">
                            <span>{p.platformName}</span>
                            <span className="text-red-600 font-semibold">{formatPrice(p.price)}</span>
                          </div>
                        ))}
                      </div>
                      <div className="flex items-center gap-3">
                        <button className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors">
                          去比价
                        </button>
                        <button
                          onClick={() => handleFavorite(product.id)}
                          className={`px-4 py-2 rounded-lg border transition-colors ${
                            isFavorite(product.id)
                              ? 'bg-red-50 border-red-300 text-red-600'
                              : 'border-gray-300 hover:bg-gray-50'
                          }`}
                        >
                          {isFavorite(product.id) ? '已收藏' : '收藏'}
                        </button>
                      </div>
                    </div>
                  </div>
                )
              ))}
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-8">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 rounded-lg border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  上一页
                </button>
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum = i + 1;
                  if (totalPages > 5) {
                    if (page <= 3) pageNum = i + 1;
                    else if (page >= totalPages - 2) pageNum = totalPages - 4 + i;
                    else pageNum = page - 2 + i;
                  }
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setPage(pageNum)}
                      className={`w-10 h-10 rounded-lg font-medium transition-colors ${
                        page === pageNum
                          ? 'bg-blue-600 text-white'
                          : 'border border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
                <button
                  onClick={() => setPage(Math.min(totalPages, page + 1))}
                  disabled={page === totalPages}
                  className="px-4 py-2 rounded-lg border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  下一页
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
