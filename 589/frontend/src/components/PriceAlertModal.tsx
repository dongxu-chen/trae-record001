import React, { useState } from 'react';
import { X, Bell, Target, Mail, Smartphone, BellRing } from 'lucide-react';
import type { PlatformPrice } from '../types';
import { formatPrice } from '../utils/format';

interface PriceAlertModalProps {
  isOpen: boolean;
  onClose: () => void;
  productName: string;
  prices: PlatformPrice[];
  onSubmit: (data: { productId: string; platform: string; targetPrice: number; notifyType: string }) => void;
}

export default function PriceAlertModal({
  isOpen,
  onClose,
  productName,
  prices,
  onSubmit,
}: PriceAlertModalProps) {
  const [selectedPlatform, setSelectedPlatform] = useState(prices[0]?.platform || '');
  const [targetPrice, setTargetPrice] = useState(
    prices[0] ? (prices[0].price * 0.9).toFixed(2) : ''
  );
  const [notifyType, setNotifyType] = useState<'email' | 'push'>('push');

  if (!isOpen) return null;

  const currentPrice = prices.find((p) => p.platform === selectedPlatform)?.price ?? 0;
  const currentLowest = Math.min(...prices.filter((p) => p.inStock).map((p) => p.price));
  const discountPercent = currentPrice > 0
    ? (((currentPrice - parseFloat(targetPrice || '0')) / currentPrice) * 100).toFixed(1)
    : '0';

  const notifyOptions = [
    { key: 'push', label: '站内推送', icon: BellRing },
    { key: 'email', label: '邮件通知', icon: Mail },
  ];

  const presetDiscounts = [5, 10, 15, 20, 30];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-3xl w-full max-w-lg shadow-2xl overflow-hidden animate-[fadeIn_0.2s_ease-out]">
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 p-6 text-white">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold flex items-center gap-2">
              <Bell size={24} />
              设置降价提醒
            </h3>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/20 rounded-full transition-colors"
            >
              <X size={20} />
            </button>
          </div>
          <p className="text-blue-100 text-sm line-clamp-1">{productName}</p>
        </div>

        <div className="p-6 space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              选择平台
            </label>
            <div className="grid grid-cols-2 gap-3">
              {prices.map((price) => (
                <button
                  key={price.platform}
                  onClick={() => {
                    setSelectedPlatform(price.platform);
                    setTargetPrice((price.price * 0.9).toFixed(2));
                  }}
                  className={`p-4 rounded-xl border-2 transition-all ${
                    selectedPlatform === price.platform
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  } ${!price.inStock ? 'opacity-50 cursor-not-allowed' : ''}`}
                  disabled={!price.inStock}
                >
                  <div className="font-medium text-gray-900">{price.platformName}</div>
                  <div className="text-lg font-bold text-red-600">
                    {formatPrice(price.price)}
                  </div>
                  {!price.inStock && (
                    <div className="text-xs text-red-500">缺货</div>
                  )}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Target size={16} />
                  目标价格
                </span>
                <span className="text-sm text-gray-500">
                  当前最低: {formatPrice(currentLowest)}
                </span>
              </div>
            </label>

            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500">¥</span>
              <input
                type="number"
                value={targetPrice}
                onChange={(e) => setTargetPrice(e.target.value)}
                className="w-full pl-10 pr-4 py-3 text-xl font-bold border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-blue-400"
                placeholder="输入目标价格"
                step="0.01"
              />
            </div>

            <div className="mt-3">
              <div className="text-sm text-gray-500 mb-2">快捷设置降价幅度:</div>
              <div className="flex flex-wrap gap-2">
                {presetDiscounts.map((discount) => (
                  <button
                    key={discount}
                    onClick={() => {
                      const price = currentPrice * (1 - discount / 100);
                      setTargetPrice(price.toFixed(2));
                    }}
                    className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-full hover:bg-blue-100 hover:text-blue-700 transition-colors"
                  >
                    降{discount}%
                  </button>
                ))}
              </div>
            </div>

            {parseFloat(targetPrice) > 0 && currentPrice > 0 && (
              <div className={`mt-3 p-3 rounded-xl ${
                parseFloat(targetPrice) < currentPrice
                  ? 'bg-green-50 text-green-700'
                  : 'bg-orange-50 text-orange-700'
              }`}>
                {parseFloat(targetPrice) < currentPrice ? (
                  <span>
                    当价格下降到{formatPrice(parseFloat(targetPrice))}，
                    相当于降价 <strong>{discountPercent}%</strong> 时通知您
                  </span>
                ) : (
                  <span>目标价格需低于当前价格</span>
                )}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              通知方式
            </label>
            <div className="flex gap-3">
              {notifyOptions.map((option) => (
                <button
                  key={option.key}
                  onClick={() => setNotifyType(option.key as any)}
                  className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl border-2 transition-all ${
                    notifyType === option.key
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 text-gray-600 hover:border-gray-300'
                  }`}
                >
                  <option.icon size={18} />
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              onClick={onClose}
              className="flex-1 py-3 px-6 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 transition-colors"
            >
              取消
            </button>
            <button
              onClick={() => {
                if (parseFloat(targetPrice) < currentPrice) {
                  onSubmit({
                    productId: prices[0]?.productId || '',
                    platform: selectedPlatform,
                    targetPrice: parseFloat(targetPrice),
                    notifyType,
                  });
                  onClose();
                }
              }}
              disabled={parseFloat(targetPrice) >= currentPrice || !selectedPlatform}
              className={`flex-1 py-3 px-6 rounded-xl font-medium transition-all ${
                parseFloat(targetPrice) < currentPrice && selectedPlatform
                  ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white hover:from-blue-600 hover:to-blue-700 shadow-lg hover:shadow-xl'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              开启提醒
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
