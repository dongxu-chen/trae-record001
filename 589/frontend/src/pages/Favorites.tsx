import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Heart, Trash2, ShoppingCart, AlertCircle, Loader2 } from 'lucide-react';
import ProductCard from '../components/ProductCard';
import { favoriteApi } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import type { Favorite, Product, PlatformPrice } from '../types';
import { formatPrice, formatDate } from '../utils/format';

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
    id: 'prod-005',
    name: 'Nike Air Max 270 男子运动鞋 黑白',
    description: '经典气垫设计，舒适缓震，时尚百搭',
    category: 'sports',
    brand: 'Nike',
    model: 'Air Max 270',
    imageUrl: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Nike%20Air%20Max%20270%20sneakers%20black%20white%20product%20photography&image_size=square',
    createdAt: '2024-01-03T10:00:00Z',
  },
];

const mockPrices: Record<string, PlatformPrice[]> = {
  'prod-001': [
    { id: 'p1', productId: 'prod-001', platform: 'taobao', platformName: '淘宝', price: 8999, originalPrice: 9999, productUrl: '', inStock: true, rating: 4.8, sales: 5000, coupons: [], lastUpdated: '' },
    { id: 'p2', productId: 'prod-001', platform: 'jd', platformName: '京东', price: 9199, originalPrice: 9999, productUrl: '', inStock: true, rating: 4.9, sales: 8000, coupons: [], lastUpdated: '' },
  ],
  'prod-003': [
    { id: 'p3', productId: 'prod-003', platform: 'taobao', platformName: '淘宝', price: 2299, originalPrice: 2999, productUrl: '', inStock: true, rating: 4.8, sales: 15000, coupons: [], lastUpdated: '' },
  ],
  'prod-005': [
    { id: 'p4', productId: 'prod-005', platform: 'jd', platformName: '京东', price: 899, originalPrice: 1199, productUrl: '', inStock: true, rating: 4.7, sales: 25000, coupons: [], lastUpdated: '' },
  ],
};

const mockFavorites: Favorite[] = mockProducts.map((p, i) => ({
  id: `fav-${i + 1}`,
  product: p,
  createdAt: new Date(Date.now() - i * 86400000).toISOString(),
}));

export default function Favorites() {
  const [favorites, setFavorites] = useState<Favorite[]>(mockFavorites);
  const [prices] = useState<Record<string, PlatformPrice[]>>(mockPrices);
  const [loading, setLoading] = useState(false);
  const [removingId, setRemovingId] = useState<string | null>(null);

  const { setFavorites: setStoreFavorites, removeFavorite } = useAppStore();

  useEffect(() => {
    loadFavorites();
  }, []);

  const loadFavorites = async () => {
    try {
      setLoading(true);
      const data = await favoriteApi.getAll();
      if (data && data.length > 0) {
        setFavorites(data);
        setStoreFavorites(data);
      }
    } catch (e) {
      console.log('使用模拟收藏数据');
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (favoriteId: string) => {
    try {
      setRemovingId(favoriteId);
      await favoriteApi.remove(favoriteId);
      removeFavorite(favoriteId);
      setFavorites((prev) => prev.filter((f) => f.id !== favoriteId));
    } catch (e) {
      console.log('删除收藏失败');
    } finally {
      setRemovingId(null);
    }
  };

  const handleRemoveAll = async () => {
    if (!confirm('确定要清空所有收藏吗？')) return;

    try {
      setLoading(true);
      for (const fav of favorites) {
        await favoriteApi.remove(fav.id);
        removeFavorite(fav.id);
      }
      setFavorites([]);
    } catch (e) {
      console.log('清空收藏失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 size={48} className="text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">正在加载收藏...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-gradient-to-r from-pink-500 to-rose-500 text-white py-12 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center gap-3 mb-2">
            <Heart size={32} fill="currentColor" />
            <h1 className="text-3xl font-bold">❤️ 我的收藏</h1>
          </div>
          <p className="text-white/80 text-lg">
            您关注的商品都在这里，我们会持续监控价格变动
          </p>
          <div className="flex items-center gap-8 mt-6">
            <div className="text-center">
              <div className="text-3xl font-bold">{favorites.length}</div>
              <div className="text-sm text-white/70">收藏商品</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold">
                {favorites.filter((f) => {
                  const productPrices = prices[f.product.id] || [];
                  return productPrices.some((p) => p.inStock);
                }).length}
              </div>
              <div className="text-sm text-white/70">有货商品</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold">
                {favorites.filter((f) => {
                  const productPrices = prices[f.product.id] || [];
                  const currentPrice = Math.min(...productPrices.map((p) => p.price));
                  const originalPrice = Math.max(...productPrices.map((p) => p.originalPrice));
                  return currentPrice < originalPrice * 0.9;
                }).length}
              </div>
              <div className="text-sm text-white/70">已降价</div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {favorites.length > 0 && (
          <div className="flex items-center justify-between mb-6">
            <div className="text-gray-600">
              共 {favorites.length} 件收藏商品
            </div>
            <button
              onClick={handleRemoveAll}
              className="flex items-center gap-2 text-sm text-red-600 hover:text-red-700"
            >
              <Trash2 size={16} />
              清空收藏
            </button>
          </div>
        )}

        {favorites.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Heart size={80} className="text-gray-200 mb-4" />
            <h3 className="text-xl font-medium text-gray-700 mb-2">还没有收藏商品</h3>
            <p className="text-gray-500 mb-6">浏览商品，点击❤️即可收藏</p>
            <Link
              to="/"
              className="px-6 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition-colors"
            >
              去逛逛
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {favorites.map((favorite) => {
              const productPrices = prices[favorite.product.id] || [];
              const currentPrice = productPrices.length > 0
                ? Math.min(...productPrices.filter((p) => p.inStock).map((p) => p.price))
                : 0;
              const originalPrice = productPrices.length > 0
                ? Math.max(...productPrices.map((p) => p.originalPrice))
                : currentPrice;
              const hasPriceDrop = currentPrice < originalPrice * 0.9;
              const inStock = productPrices.some((p) => p.inStock);

              return (
                <div key={favorite.id} className="relative group">
                  {hasPriceDrop && (
                    <div className="absolute -top-2 -left-2 z-10 bg-red-500 text-white text-xs font-bold px-2 py-1 rounded-full">
                      已降价
                    </div>
                  )}
                  {!inStock && (
                    <div className="absolute inset-0 bg-black/50 rounded-2xl z-10 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                      <span className="text-white font-medium">暂时缺货</span>
                    </div>
                  )}
                  <div className="absolute top-3 right-3 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => handleRemove(favorite.id)}
                      disabled={removingId === favorite.id}
                      className="p-2 bg-white rounded-full shadow-md hover:bg-red-50 text-gray-600 hover:text-red-600 transition-colors"
                    >
                      {removingId === favorite.id ? (
                        <Loader2 size={18} className="animate-spin" />
                      ) : (
                        <Trash2 size={18} />
                      )}
                    </button>
                  </div>
                  <ProductCard
                    product={favorite.product}
                    prices={productPrices}
                  />
                  <div className="text-xs text-gray-400 mt-2 px-1">
                    收藏于 {formatDate(favorite.createdAt)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
