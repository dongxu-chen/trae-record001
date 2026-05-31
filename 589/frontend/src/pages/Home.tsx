import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Search, TrendingDown, Tag, Sparkles, ChevronRight, Zap, Gift, Clock, Bell } from 'lucide-react';
import ProductCard, { HotProductCard } from '../components/ProductCard';
import { productApi } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import type { HotProduct, Product } from '../types';
import { formatPrice } from '../utils/format';

const CATEGORIES = [
  { id: 'electronics', name: '数码电子', icon: '📱', color: 'from-blue-500 to-cyan-500' },
  { id: 'phones', name: '手机通讯', icon: '📞', color: 'from-purple-500 to-pink-500' },
  { id: 'computers', name: '电脑办公', icon: '💻', color: 'from-indigo-500 to-blue-500' },
  { id: 'home', name: '家用电器', icon: '🏠', color: 'from-green-500 to-emerald-500' },
  { id: 'clothing', name: '服饰鞋包', icon: '👕', color: 'from-pink-500 to-rose-500' },
  { id: 'beauty', name: '美妆护肤', icon: '💄', color: 'from-rose-500 to-red-500' },
  { id: 'food', name: '食品生鲜', icon: '🍎', color: 'from-orange-500 to-yellow-500' },
  { id: 'sports', name: '运动户外', icon: '⚽', color: 'from-teal-500 to-green-500' },
];

const PLATFORMS = [
  { name: '淘宝', logo: '🐱', color: 'bg-orange-500' },
  { name: '京东', logo: '🐕', color: 'bg-red-600' },
  { name: '拼多多', logo: '🛒', color: 'bg-red-500' },
  { name: '苏宁', logo: '🏬', color: 'bg-yellow-500' },
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
];

const mockHotProducts: HotProduct[] = mockProducts.slice(0, 4).map((p, i) => ({
  product: p,
  bestPrice: [8999, 14999, 2299, 4990, 899, 1590][i],
  lowestEver: [7999, 13999, 1999, 4490, 799, 1290][i],
  potentialSavings: [1000, 1000, 300, 500, 100, 300][i],
}));

export default function Home() {
  const navigate = useNavigate();
  const [searchInput, setSearchInput] = useState('');
  const [hotProducts, setHotProducts] = useState<HotProduct[]>(mockHotProducts);
  const [trendingProducts, setTrendingProducts] = useState<Product[]>(mockProducts);
  const { setIsLoading, setSearchQuery } = useAppStore();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setIsLoading(true);
      const [hot, trending] = await Promise.all([
        productApi.getHot(8),
        productApi.search('', 1, 12),
      ]);
      if (hot && hot.length > 0) setHotProducts(hot);
      if (trending && trending.items.length > 0) setTrendingProducts(trending.items);
    } catch (e) {
      console.log('使用模拟数据');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) {
      setSearchQuery(searchInput);
      navigate(`/search?q=${encodeURIComponent(searchInput)}`);
    }
  };

  const handleCategoryClick = (category: string) => {
    navigate(`/search?category=${encodeURIComponent(category)}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      <section className="bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900 text-white py-16 px-4">
        <div className="max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-white/10 px-4 py-2 rounded-full mb-6">
            <Sparkles size={18} className="text-yellow-400" />
            <span className="text-sm font-medium">全网实时比价，帮您省钱</span>
          </div>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 leading-tight">
            聪明购物，
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 to-orange-400">
              每一分钱都花在刀刃上
            </span>
          </h1>
          <p className="text-lg md:text-xl text-blue-100 mb-8 max-w-2xl mx-auto">
            聚合淘宝、京东、拼多多、苏宁四大平台商品信息，智能比价，历史价格分析，帮您找到最优购买时机
          </p>

          <form onSubmit={handleSearch} className="max-w-3xl mx-auto mb-8">
            <div className="relative flex items-center">
              <div className="absolute left-4 text-gray-400">
                <Search size={24} />
              </div>
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="搜索商品，如 iPhone 15、MacBook Pro、戴森吸尘器..."
                className="w-full pl-14 pr-32 py-4 rounded-full text-gray-900 text-lg shadow-2xl focus:outline-none focus:ring-4 focus:ring-orange-400/50 transition-all"
              />
              <button
                type="submit"
                className="absolute right-2 bg-gradient-to-r from-orange-500 to-orange-600 text-white px-8 py-3 rounded-full font-semibold hover:from-orange-600 hover:to-orange-700 transition-all shadow-lg hover:shadow-xl active:scale-95"
              >
                搜索比价
              </button>
            </div>
          </form>

          <div className="flex flex-wrap justify-center gap-3">
            <span className="text-blue-200 text-sm">热门搜索：</span>
            {['iPhone 15', 'MacBook Pro', '戴森吸尘器', 'Nike运动鞋', 'SK-II神仙水'].map((keyword) => (
              <button
                key={keyword}
                onClick={() => {
                  setSearchQuery(keyword);
                  navigate(`/search?q=${encodeURIComponent(keyword)}`);
                }}
                className="px-4 py-1.5 bg-white/10 hover:bg-white/20 rounded-full text-sm transition-colors"
              >
                {keyword}
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="py-6 bg-white border-b">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid grid-cols-4 md:grid-cols-8 gap-4">
            {CATEGORIES.map((category) => (
              <button
                key={category.id}
                onClick={() => handleCategoryClick(category.id)}
                className="flex flex-col items-center gap-2 p-3 rounded-xl hover:bg-gray-50 transition-all group"
              >
                <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${category.color} flex items-center justify-center text-2xl shadow-md group-hover:scale-110 transition-transform`}>
                  {category.icon}
                </div>
                <span className="text-sm text-gray-700 font-medium">{category.name}</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="py-6 bg-gradient-to-r from-orange-50 to-yellow-50">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-orange-500 rounded-xl flex items-center justify-center text-white">
                <Zap size={24} />
              </div>
              <div>
                <div className="font-bold text-gray-900">实时比价</div>
                <div className="text-sm text-gray-600">4大平台同步更新</div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-500 rounded-xl flex items-center justify-center text-white">
                <TrendingDown size={24} />
              </div>
              <div>
                <div className="font-bold text-gray-900">历史价格</div>
                <div className="text-sm text-gray-600">365天价格走势</div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-green-500 rounded-xl flex items-center justify-center text-white">
                <Tag size={24} />
              </div>
              <div>
                <div className="font-bold text-gray-900">自动优惠券</div>
                <div className="text-sm text-gray-600">智能匹配最优券</div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-purple-500 rounded-xl flex items-center justify-center text-white">
                <Bell size={24} />
              </div>
              <div>
                <div className="font-bold text-gray-900">降价提醒</div>
                <div className="text-sm text-gray-600">目标价格自动通知</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-10">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-red-500 rounded-xl flex items-center justify-center text-white">
                <Gift size={20} />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-900">🔥 热门降价</h2>
                <p className="text-sm text-gray-500">近期降价幅度最大的商品</p>
              </div>
            </div>
            <Link
              to="/products/hot"
              className="flex items-center gap-1 text-orange-600 hover:text-orange-700 font-medium"
            >
              查看全部 <ChevronRight size={18} />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {hotProducts.map((item) => (
              <HotProductCard key={item.product.id} item={item} />
            ))}
          </div>
        </div>
      </section>

      <section className="py-10 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-500 rounded-xl flex items-center justify-center text-white">
                <Sparkles size={20} />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-900">✨ 为你推荐</h2>
                <p className="text-sm text-gray-500">精选热门商品</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-4">
            {trendingProducts.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        </div>
      </section>

      <section className="py-10">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">已支持平台</h2>
            <p className="text-gray-500">聚合四大主流电商平台，一站式比价</p>
          </div>
          <div className="flex justify-center gap-8">
            {PLATFORMS.map((platform) => (
              <div
                key={platform.name}
                className="flex flex-col items-center gap-2 p-6 rounded-2xl bg-white shadow-md hover:shadow-lg transition-shadow"
              >
                <div className={`w-16 h-16 ${platform.color} rounded-2xl flex items-center justify-center text-3xl`}>
                  {platform.logo}
                </div>
                <span className="font-semibold text-gray-700">{platform.name}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="bg-gray-900 text-gray-400 py-10 mt-10">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <TrendingDown className="text-orange-400" size={28} />
                <span className="text-xl font-bold text-white">比价达人</span>
              </div>
              <p className="text-sm">智能比价导购平台，帮您找到最优惠的购买渠道</p>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">热门分类</h4>
              <ul className="space-y-2 text-sm">
                <li><Link to="#" className="hover:text-white transition-colors">手机数码</Link></li>
                <li><Link to="#" className="hover:text-white transition-colors">电脑办公</Link></li>
                <li><Link to="#" className="hover:text-white transition-colors">家用电器</Link></li>
                <li><Link to="#" className="hover:text-white transition-colors">服饰鞋包</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">帮助中心</h4>
              <ul className="space-y-2 text-sm">
                <li><Link to="#" className="hover:text-white transition-colors">如何使用</Link></li>
                <li><Link to="#" className="hover:text-white transition-colors">常见问题</Link></li>
                <li><Link to="#" className="hover:text-white transition-colors">联系我们</Link></li>
                <li><Link to="#" className="hover:text-white transition-colors">隐私政策</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">关于我们</h4>
              <ul className="space-y-2 text-sm">
                <li><Link to="#" className="hover:text-white transition-colors">关于比价达人</Link></li>
                <li><Link to="#" className="hover:text-white transition-colors">商务合作</Link></li>
                <li><Link to="#" className="hover:text-white transition-colors">加入我们</Link></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-6 text-center text-sm">
            <p>© 2024 比价达人. 让每一次购物都物超所值.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
