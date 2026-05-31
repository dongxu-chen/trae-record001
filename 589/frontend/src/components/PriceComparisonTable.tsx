import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Star, ShoppingBag, Tag, Clock, CheckCircle, XCircle, Zap } from 'lucide-react';
import type { PlatformPrice, Coupon } from '../types';
import { PLATFORM_CONFIG } from '../types';
import { formatPrice, formatDiscount, formatRelativeTime, formatSales } from '../utils/format';

interface PriceComparisonTableProps {
  prices: PlatformPrice[];
  bestDeal: PlatformPrice;
}

export default function PriceComparisonTable({ prices, bestDeal }: PriceComparisonTableProps) {
  const [sortBy, setSortBy] = useState<'price' | 'rating' | 'sales'>('price');

  const sortedPrices = [...prices].sort((a, b) => {
    const priceA = a.couponPrice ?? a.price;
    const priceB = b.couponPrice ?? b.price;

    switch (sortBy) {
      case 'price':
        return priceA - priceB;
      case 'rating':
        return (b.rating ?? 0) - (a.rating ?? 0);
      case 'sales':
        return (b.sales ?? 0) - (a.sales ?? 0);
      default:
        return 0;
    }
  });

  const getCouponTag = (coupons: Coupon[], price: number) => {
    if (coupons.length === 0) return null;

    const applicable = coupons.filter((c) => price >= c.minAmount);
    if (applicable.length === 0) return null;

    const best = applicable.reduce((prev, curr) => {
      const prevDiscount = curr.discountType === 'percentage'
        ? price * (prev.discount / 100)
        : prev.discount;
      const currDiscount = curr.discountType === 'percentage'
        ? price * (curr.discount / 100)
        : curr.discount;
      return currDiscount > prevDiscount ? curr : prev;
    });

    return (
      <span className="inline-flex items-center gap-1 bg-red-100 text-red-700 px-2 py-0.5 rounded-full text-xs font-medium">
        <Tag size={12} />
        {formatDiscount(best.discount, best.discountType)}
      </span>
    );
  };

  return (
    <div className="bg-white rounded-2xl shadow-md overflow-hidden">
      <div className="p-6 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-gray-900">多平台比价</h3>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">排序:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-orange-400"
            >
              <option value="price">价格最低</option>
              <option value="rating">评分最高</option>
              <option value="sales">销量最高</option>
            </select>
          </div>
        </div>
      </div>

      <div className="hidden lg:grid grid-cols-12 gap-4 p-4 bg-gray-50 text-sm font-medium text-gray-600 border-b border-gray-100">
        <div className="col-span-2">平台</div>
        <div className="col-span-1">现价</div>
        <div className="col-span-1">原价</div>
        <div className="col-span-2">优惠券</div>
        <div className="col-span-1">到手价</div>
        <div className="col-span-1">评分</div>
        <div className="col-span-1">销量</div>
        <div className="col-span-1">库存</div>
        <div className="col-span-2">操作</div>
      </div>

      <div className="divide-y divide-gray-100">
        {sortedPrices.map((price, index) => {
          const config = PLATFORM_CONFIG[price.platform];
          const isBestDeal = price.id === bestDeal.id;
          const finalPrice = price.couponPrice ?? price.price;
          const hasCoupon = price.couponPrice && price.couponPrice < price.price;

          return (
            <div
              key={price.id}
              className={`p-4 grid grid-cols-1 lg:grid-cols-12 gap-4 items-center transition-all ${
                isBestDeal ? 'bg-gradient-to-r from-orange-50 to-transparent' : 'hover:bg-gray-50'
              }`}
            >
              <div className="col-span-2 flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center text-xl"
                  style={{ backgroundColor: `${config?.color}20` }}
                >
                  {config?.logo}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">{config?.name}</span>
                    {isBestDeal && (
                      <span className="inline-flex items-center gap-1 bg-orange-500 text-white text-xs font-bold px-2 py-0.5 rounded-full animate-pulse">
                        <Zap size={12} />
                        最优
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-gray-500 flex items-center gap-1">
                    <Clock size={12} />
                    {formatRelativeTime(price.lastUpdated)}
                  </div>
                </div>
              </div>

              <div className="col-span-1 lg:block hidden">
                <span className={`font-medium ${
                  hasCoupon ? 'text-gray-500 line-through' : 'text-gray-900'
                }`}>
                  {formatPrice(price.price)}
                </span>
              </div>

              <div className="col-span-1 lg:block hidden">
                <span className="text-gray-400 line-through text-sm">
                  {formatPrice(price.originalPrice)}
                </span>
              </div>

              <div className="col-span-2">
                <div className="flex flex-wrap gap-1">
                  {getCouponTag(price.coupons, price.price)}
                  {!price.inStock && (
                    <span className="inline-flex items-center gap-1 bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full text-xs">
                      <XCircle size={12} />
                      缺货
                    </span>
                  )}
                </div>
              </div>

              <div className="col-span-1">
                <div className={`text-xl font-bold ${
                  hasCoupon ? 'text-red-600' : 'text-orange-600'
                }`}>
                  {formatPrice(finalPrice)}
                </div>
                {hasCoupon && (
                  <div className="text-xs text-green-600 font-medium">
                    券后省{formatPrice(price.price - finalPrice)}
                  </div>
                )}
              </div>

              <div className="col-span-1 flex items-center gap-1">
                <Star size={14} className="text-yellow-500 fill-yellow-500" />
                <span className="text-sm text-gray-700">{price.rating?.toFixed(1) || '4.5'}</span>
              </div>

              <div className="col-span-1 text-sm text-gray-600">
                {formatSales(price.sales)}
              </div>

              <div className="col-span-1">
                {price.inStock ? (
                  <span className="inline-flex items-center gap-1 text-green-600 text-sm">
                    <CheckCircle size={14} />
                    有货
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-red-500 text-sm">
                    <XCircle size={14} />
                    缺货
                  </span>
                )}
              </div>

              <div className="col-span-2 lg:col-span-2 flex items-center gap-2">
                <a
                  href={price.productUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  disabled={!price.inStock}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-xl font-medium transition-all ${
                    isBestDeal
                      ? 'bg-gradient-to-r from-orange-500 to-orange-600 text-white hover:from-orange-600 hover:to-orange-700 shadow-lg hover:shadow-xl'
                      : price.inStock
                      ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  }`}
                >
                  <ShoppingBag size={16} />
                  去购买
                </a>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
