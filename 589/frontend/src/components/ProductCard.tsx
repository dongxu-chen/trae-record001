import React from 'react';
import { Link } from 'react-router-dom';
import { Heart, Star, ShoppingCart, TrendingDown } from 'lucide-react';
import type { Product, PlatformPrice, HotProduct } from '../types';
import { PLATFORM_CONFIG } from '../types';
import { formatPrice, formatSales } from '../utils/format';

interface ProductCardProps {
  product: Product;
  prices?: PlatformPrice[];
  bestPrice?: number;
  lowestEver?: number;
  potentialSavings?: number;
  onFavorite?: (productId: string) => void;
  isFavorite?: boolean;
}

export default function ProductCard({
  product,
  prices = [],
  bestPrice,
  lowestEver,
  potentialSavings,
  onFavorite,
  isFavorite = false,
}: ProductCardProps) {
  const inStockPrices = prices.filter((p) => p.inStock);
  const currentBest = bestPrice ?? (inStockPrices.length > 0
    ? Math.min(...inStockPrices.map((p) => p.couponPrice ?? p.price))
    : 0);
  const originalPrice = prices.length > 0
    ? Math.max(...prices.map((p) => p.originalPrice ?? p.price))
    : currentBest * 1.1;

  const platforms = [...new Set(prices.map((p) => p.platform))];
  const isLowestEver = lowestEver && currentBest <= lowestEver * 1.01;

  return (
    <div className="group bg-white rounded-2xl shadow-md hover:shadow-2xl transition-all duration-300 overflow-hidden border border-gray-100 hover:border-orange-200 hover:-translate-y-1">
      <div className="relative">
        <Link to={`/product/${product.id}`}>
          <div className="aspect-square overflow-hidden bg-gradient-to-br from-gray-50 to-gray-100">
            <img
              src={product.imageUrl || 'https://picsum.photos/400/400'}
              alt={product.name}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              loading="lazy"
            />
          </div>
        </Link>

        <div className="absolute top-3 left-3 flex flex-col gap-2">
          {isLowestEver && (
            <span className="bg-red-500 text-white text-xs font-bold px-2 py-1 rounded-full animate-pulse">
              🔥 历史最低
            </span>
          )}
          {potentialSavings && potentialSavings > 100 && (
            <span className="bg-green-500 text-white text-xs font-bold px-2 py-1 rounded-full">
              💰 可省{formatPrice(potentialSavings)}
            </span>
          )}
        </div>

        <button
          onClick={(e) => {
            e.preventDefault();
            onFavorite?.(product.id);
          }}
          className={`absolute top-3 right-3 p-2 rounded-full transition-all ${
            isFavorite
              ? 'bg-red-500 text-white'
              : 'bg-white/80 text-gray-600 hover:bg-red-500 hover:text-white'
          }`}
        >
          <Heart size={18} fill={isFavorite ? 'currentColor' : 'none'} />
        </button>
      </div>

      <div className="p-4">
        <Link to={`/product/${product.id}`}>
          <h3 className="font-medium text-gray-900 line-clamp-2 h-12 mb-2 group-hover:text-blue-600 transition-colors">
            {product.name}
          </h3>
        </Link>

        {product.brand && (
          <div className="text-xs text-gray-500 mb-2">
            {product.brand} {product.model && `| ${product.model}`}
          </div>
        )}

        <div className="flex items-center justify-between mb-3">
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-red-600">
              {formatPrice(currentBest)}
            </span>
            {originalPrice > currentBest && (
              <span className="text-sm text-gray-400 line-through">
                {formatPrice(originalPrice)}
              </span>
            )}
          </div>
          {lowestEver && (
            <div className="text-xs text-gray-500">
              史低: {formatPrice(lowestEver)}
            </div>
          )}
        </div>

        {inStockPrices.length > 0 && (
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-1">
              {platforms.slice(0, 4).map((platform) => {
                const config = PLATFORM_CONFIG[platform];
                return (
                  <span
                    key={platform}
                    className="text-lg"
                    title={config?.name}
                  >
                    {config?.logo}
                  </span>
                );
              })}
              {platforms.length > 4 && (
                <span className="text-xs text-gray-500">+{platforms.length - 4}</span>
              )}
            </div>
            <div className="text-xs text-gray-500">
              {inStockPrices.length}家平台在售
            </div>
          </div>
        )}

        {inStockPrices.length > 0 && (
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-3">
            <div className="flex items-center gap-1">
              <Star size={14} className="text-yellow-500 fill-yellow-500" />
              <span>{(Math.max(...inStockPrices.map((p) => p.rating ?? 0)) || 4.5).toFixed(1)}</span>
            </div>
            <span>·</span>
            <span>{formatSales(Math.max(...inStockPrices.map((p) => p.sales ?? 0)))}人购买</span>
          </div>
        )}

        <Link
          to={`/product/${product.id}`}
          className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-orange-500 to-orange-600 text-white py-2.5 rounded-xl font-medium hover:from-orange-600 hover:to-orange-700 transition-all hover:shadow-lg active:scale-95"
        >
          <ShoppingCart size={18} />
          去比价
        </Link>
      </div>
    </div>
  );
}

export function HotProductCard({ item }: { item: HotProduct }) {
  return (
    <ProductCard
      product={item.product}
      bestPrice={item.bestPrice}
      lowestEver={item.lowestEver}
      potentialSavings={item.potentialSavings}
    />
  );
}
