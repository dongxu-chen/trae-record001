import React, { useState, useEffect } from 'react';
import { Tag, Gift, Copy, Check, ExternalLink, Filter, Search } from 'lucide-react';
import { couponApi } from '../services/api';
import { PLATFORM_CONFIG, type Coupon } from '../types';
import { formatPrice, formatDate, formatDiscount } from '../utils/format';

const mockCoupons: Coupon[] = [
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
  {
    id: 'coupon-004',
    platform: 'taobao',
    code: 'NEWYEAR100',
    discount: 100,
    discountType: 'fixed',
    minAmount: 500,
    maxDiscount: 100,
    validFrom: '2024-01-01T00:00:00Z',
    validTo: '2024-02-28T23:59:59Z',
  },
  {
    id: 'coupon-005',
    platform: 'jd',
    code: 'JD1000',
    discount: 1000,
    discountType: 'fixed',
    minAmount: 10000,
    maxDiscount: 1000,
    validFrom: '2024-01-15T00:00:00Z',
    validTo: '2024-01-31T23:59:59Z',
  },
  {
    id: 'coupon-006',
    platform: 'suning',
    code: 'SUNING50',
    discount: 50,
    discountType: 'fixed',
    minAmount: 500,
    maxDiscount: 50,
    validFrom: '2024-01-01T00:00:00Z',
    validTo: '2024-03-31T23:59:59Z',
  },
  {
    id: 'coupon-007',
    platform: 'pdd',
    code: 'PDD10',
    discount: 10,
    discountType: 'percentage',
    minAmount: 100,
    maxDiscount: 100,
    validFrom: '2024-01-01T00:00:00Z',
    validTo: '2024-06-30T23:59:59Z',
  },
  {
    id: 'coupon-008',
    platform: 'taobao',
    code: '3C500',
    discount: 500,
    discountType: 'fixed',
    minAmount: 5000,
    maxDiscount: 500,
    validFrom: '2024-01-20T00:00:00Z',
    validTo: '2024-02-05T23:59:59Z',
  },
];

const PLATFORM_FILTERS = [
  { value: 'all', label: '全部平台', logo: '🛍️' },
  { value: 'taobao', label: '淘宝', logo: '🐱' },
  { value: 'jd', label: '京东', logo: '🐕' },
  { value: 'pdd', label: '拼多多', logo: '🛒' },
  { value: 'suning', label: '苏宁', logo: '🏬' },
];

const TYPE_FILTERS = [
  { value: 'all', label: '全部类型' },
  { value: 'fixed', label: '满减券' },
  { value: 'percentage', label: '折扣券' },
];

const SORT_OPTIONS = [
  { value: 'discount_desc', label: '优惠最大' },
  { value: 'minAmount_asc', label: '门槛最低' },
  { value: 'validTo_asc', label: '即将到期' },
  { value: 'newest', label: '最新发布' },
];

export default function Coupons() {
  const [coupons, setCoupons] = useState<Coupon[]>(mockCoupons);
  const [platformFilter, setPlatformFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [sortBy, setSortBy] = useState('discount_desc');
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [stats, setStats] = useState({ total: 8, totalValue: 2150, used: 1234 });

  useEffect(() => {
    loadCoupons();
    loadStats();
  }, [platformFilter]);

  const loadCoupons = async () => {
    try {
      const platform = platformFilter === 'all' ? undefined : platformFilter;
      const data = await couponApi.getAll(platform);
      if (data && data.length > 0) {
        setCoupons(data);
      }
    } catch (e) {
      console.log('使用模拟优惠券数据');
    }
  };

  const loadStats = async () => {
    try {
      const data = await couponApi.getStats();
      if (data) {
        setStats(data);
      }
    } catch (e) {
      console.log('使用模拟统计数据');
    }
  };

  const filteredCoupons = coupons.filter((coupon) => {
    if (platformFilter !== 'all' && coupon.platform !== platformFilter) return false;
    if (typeFilter !== 'all' && coupon.discountType !== typeFilter) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        coupon.code.toLowerCase().includes(query) ||
        PLATFORM_CONFIG[coupon.platform]?.name.toLowerCase().includes(query)
      );
    }
    return true;
  });

  const sortedCoupons = [...filteredCoupons].sort((a, b) => {
    switch (sortBy) {
      case 'discount_desc':
        return b.discount - a.discount;
      case 'minAmount_asc':
        return a.minAmount - b.minAmount;
      case 'validTo_asc':
        return new Date(a.validTo).getTime() - new Date(b.validTo).getTime();
      case 'newest':
        return new Date(b.validFrom).getTime() - new Date(a.validFrom).getTime();
      default:
        return 0;
    }
  });

  const handleCopyCode = async (code: string, id: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (e) {
      console.log('复制失败');
    }
  };

  const getDiscountDisplay = (coupon: Coupon) => {
    if (coupon.discountType === 'percentage') {
      return `${coupon.discount}%`;
    }
    return formatPrice(coupon.discount);
  };

  const getDaysRemaining = (validTo: string) => {
    const now = new Date();
    const end = new Date(validTo);
    const diff = end.getTime() - now.getTime();
    const days = Math.ceil(diff / (1000 * 60 * 60 * 24));
    return days;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-gradient-to-r from-orange-500 to-red-500 text-white py-12 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center gap-3 mb-2">
            <Tag size={32} />
            <h1 className="text-3xl font-bold">🎫 优惠券中心</h1>
          </div>
          <p className="text-white/80 text-lg">
            聚合全网优惠券，自动匹配最优，让您享受最大优惠
          </p>
          <div className="flex items-center gap-8 mt-6">
            <div className="text-center">
              <div className="text-3xl font-bold">{stats.total}</div>
              <div className="text-sm text-white/70">可用优惠券</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold">{formatPrice(stats.totalValue)}</div>
              <div className="text-sm text-white/70">总优惠金额</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold">{stats.used}</div>
              <div className="text-sm text-white/70">已使用次数</div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="bg-white rounded-2xl p-6 mb-6 shadow-sm">
          <div className="flex flex-wrap items-center gap-4 mb-4">
            <div className="relative flex-1 max-w-md">
              <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索优惠券码或平台..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <Filter size={18} className="text-gray-500" />
              <span className="text-sm text-gray-600">平台：</span>
              <div className="flex gap-1">
                {PLATFORM_FILTERS.map((platform) => (
                  <button
                    key={platform.value}
                    onClick={() => setPlatformFilter(platform.value)}
                    className={`flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg transition-colors ${
                      platformFilter === platform.value
                        ? 'bg-orange-100 text-orange-700'
                        : 'text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    <span>{platform.logo}</span>
                    <span className="hidden sm:inline">{platform.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">类型：</span>
              <div className="flex gap-1">
                {TYPE_FILTERS.map((type) => (
                  <button
                    key={type.value}
                    onClick={() => setTypeFilter(type.value)}
                    className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                      typeFilter === type.value
                        ? 'bg-orange-100 text-orange-700'
                        : 'text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    {type.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">排序：</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
              >
                {SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {sortedCoupons.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Gift size={60} className="text-gray-300 mb-4" />
            <h3 className="text-xl font-medium text-gray-700 mb-2">暂无符合条件的优惠券</h3>
            <p className="text-gray-500">试试调整筛选条件</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {sortedCoupons.map((coupon) => {
              const daysRemaining = getDaysRemaining(coupon.validTo);
              const isExpiringSoon = daysRemaining <= 7;
              const platformConfig = PLATFORM_CONFIG[coupon.platform];

              return (
                <div
                  key={coupon.id}
                  className="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-lg transition-shadow border"
                >
                  <div
                    className="relative p-6 text-white"
                    style={{
                      background: `linear-gradient(135deg, ${platformConfig?.color || '#f97316'}, ${
                        platformConfig?.color || '#ef4444'
                      }dd)`,
                    }}
                  >
                    <div className="absolute top-3 right-3 flex items-center gap-1 bg-white/20 px-2 py-1 rounded-full text-xs">
                      <span>{platformConfig?.logo}</span>
                      <span>{platformConfig?.name}</span>
                    </div>

                    <div className="text-center mb-2">
                      <div className="text-5xl font-bold">{getDiscountDisplay(coupon)}</div>
                      <div className="text-white/80 text-sm mt-1">
                        {coupon.discountType === 'percentage' ? '折扣' : '立减'}
                      </div>
                    </div>

                    <div className="text-center text-white/90 text-sm">
                      满{formatPrice(coupon.minAmount)}可用
                      {coupon.maxDiscount && coupon.discountType === 'percentage' && (
                        <span className="ml-1">· 最高减{formatPrice(coupon.maxDiscount)}</span>
                      )}
                    </div>

                    {isExpiringSoon && (
                      <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 bg-red-600 text-white text-xs px-3 py-1 rounded-full">
                        仅剩 {daysRemaining} 天
                      </div>
                    )}
                  </div>

                  <div className="p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="text-sm text-gray-500">
                        有效期至 {formatDate(coupon.validTo)}
                      </div>
                      {daysRemaining > 0 && (
                        <div
                          className={`text-xs px-2 py-1 rounded-full ${
                            isExpiringSoon
                              ? 'bg-red-100 text-red-600'
                              : 'bg-green-100 text-green-600'
                          }`}
                        >
                          {daysRemaining}天后到期
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2 mb-3 p-2 bg-gray-50 rounded-lg">
                      <code className="flex-1 font-mono text-sm text-gray-700">{coupon.code}</code>
                      <button
                        onClick={() => handleCopyCode(coupon.code, coupon.id)}
                        className="flex items-center gap-1 px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
                      >
                        {copiedId === coupon.id ? (
                          <>
                            <Check size={14} />
                            已复制
                          </>
                        ) : (
                          <>
                            <Copy size={14} />
                            复制
                          </>
                        )}
                      </button>
                    </div>

                    <button
                      className="w-full flex items-center justify-center gap-2 py-2.5 bg-orange-500 text-white rounded-xl font-medium hover:bg-orange-600 transition-colors"
                    >
                      <Gift size={18} />
                      立即使用
                      <ExternalLink size={16} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="mt-8 bg-white rounded-2xl p-6">
          <h3 className="text-lg font-bold mb-4">💡 使用说明</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold flex-shrink-0">
                1
              </div>
              <div>
                <div className="font-medium mb-1">选择优惠券</div>
                <div className="text-sm text-gray-600">
                  浏览并选择适合您的优惠券，点击复制券码
                </div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold flex-shrink-0">
                2
              </div>
              <div>
                <div className="font-medium mb-1">前往购物</div>
                <div className="text-sm text-gray-600">
                  点击"立即使用"跳转到对应平台进行购物
                </div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold flex-shrink-0">
                3
              </div>
              <div>
                <div className="font-medium mb-1">结算使用</div>
                <div className="text-sm text-gray-600">
                  在结算页面粘贴优惠券码，即可享受优惠
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
