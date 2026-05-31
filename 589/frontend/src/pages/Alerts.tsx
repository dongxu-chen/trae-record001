import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Bell,
  Plus,
  Trash2,
  ToggleLeft,
  ToggleRight,
  AlertCircle,
  Loader2,
  Mail,
  Smartphone,
  Clock,
  TrendingDown,
} from 'lucide-react';
import { alertApi } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { PLATFORM_CONFIG, type PriceAlert, type Product } from '../types';
import { formatPrice, formatDate, formatRelativeTime } from '../utils/format';

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
    id: 'prod-002',
    name: 'MacBook Pro 14英寸 M3 Pro 18GB 512GB',
    description: 'M3 Pro芯片，Liquid Retina XDR显示屏，18小时续航',
    category: 'computers',
    brand: 'Apple',
    model: 'MacBook Pro 14',
    imageUrl: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=MacBook%20Pro%2014%20inch%20laptop%20silver%20product%20photography%20white%20background&image_size=square',
    createdAt: '2024-01-10T10:00:00Z',
  },
];

const mockAlerts: PriceAlert[] = [
  {
    id: 'alert-001',
    userId: 'user-001',
    productId: 'prod-001',
    targetPrice: 7999,
    currentPrice: 8799,
    platform: 'pdd',
    notifyType: 'push',
    isActive: true,
    createdAt: new Date(Date.now() - 7 * 86400000).toISOString(),
  },
  {
    id: 'alert-002',
    userId: 'user-001',
    productId: 'prod-003',
    targetPrice: 1899,
    currentPrice: 2299,
    platform: 'taobao',
    notifyType: 'email',
    isActive: true,
    createdAt: new Date(Date.now() - 14 * 86400000).toISOString(),
  },
  {
    id: 'alert-003',
    userId: 'user-001',
    productId: 'prod-002',
    targetPrice: 12999,
    currentPrice: 14999,
    platform: 'jd',
    notifyType: 'push',
    isActive: false,
    createdAt: new Date(Date.now() - 30 * 86400000).toISOString(),
  },
];

export default function Alerts() {
  const [alerts, setAlerts] = useState<PriceAlert[]>(mockAlerts);
  const [products] = useState<Product[]>(mockProducts);
  const [loading, setLoading] = useState(false);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [stats, setStats] = useState({
    total: 3,
    active: 2,
    triggered: 5,
    avgSavings: 850,
  });

  const { setAlerts: setStoreAlerts, addAlert, removeAlert, notifications } = useAppStore();

  useEffect(() => {
    loadAlerts();
    loadStats();
  }, []);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      const data = await alertApi.getAll(true);
      if (data && data.length > 0) {
        setAlerts(data);
        setStoreAlerts(data);
      }
    } catch (e) {
      console.log('使用模拟提醒数据');
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const data = await alertApi.getStats();
      if (data) {
        setStats(data);
      }
    } catch (e) {
      console.log('使用模拟统计数据');
    }
  };

  const getProduct = (productId: string) => {
    return products.find((p) => p.id === productId);
  };

  const handleToggle = async (alertId: string, isActive: boolean) => {
    try {
      setTogglingId(alertId);
      if (isActive) {
        await alertApi.deactivate(alertId);
      }
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, isActive: !isActive } : a))
      );
    } catch (e) {
      console.log('切换状态失败');
    } finally {
      setTogglingId(null);
    }
  };

  const handleDelete = async (alertId: string) => {
    if (!confirm('确定要删除这个提醒吗？')) return;

    try {
      await alertApi.delete(alertId);
      removeAlert(alertId);
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    } catch (e) {
      console.log('删除提醒失败');
    }
  };

  const getProgressPercent = (current: number, target: number) => {
    const maxPrice = current * 1.2;
    return Math.max(0, Math.min(100, ((maxPrice - current) / (maxPrice - target)) * 100));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 size={48} className="text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">正在加载提醒...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-12 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <Bell size={32} />
              <h1 className="text-3xl font-bold">🔔 降价提醒</h1>
            </div>
            <Link
              to="/"
              className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
            >
              <Plus size={18} />
              添加提醒
            </Link>
          </div>
          <p className="text-white/80 text-lg">
            设置目标价格，商品降价时第一时间通知您
          </p>
          <div className="flex items-center gap-8 mt-6">
            <div className="text-center">
              <div className="text-3xl font-bold">{stats.total}</div>
              <div className="text-sm text-white/70">总提醒数</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold">{stats.active}</div>
              <div className="text-sm text-white/70">监控中</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold">{stats.triggered}</div>
              <div className="text-sm text-white/70">已触发</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold">{formatPrice(stats.avgSavings)}</div>
              <div className="text-sm text-white/70">平均节省</div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {notifications.length > 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 mb-6">
            <div className="flex items-start gap-3">
              <AlertCircle className="text-yellow-600 flex-shrink-0 mt-0.5" size={20} />
              <div className="flex-1">
                <div className="font-medium text-yellow-800 mb-1">
                  您有 {notifications.length} 条新的降价通知
                </div>
                {notifications.slice(0, 3).map((n, i) => (
                  <div key={i} className="text-sm text-yellow-700">
                    {getProduct(n.productId)?.name} 已降至 {formatPrice(n.currentPrice)}，
                    低于您设置的目标价 {formatPrice(n.targetPrice)}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Bell size={80} className="text-gray-200 mb-4" />
            <h3 className="text-xl font-medium text-gray-700 mb-2">还没有设置降价提醒</h3>
            <p className="text-gray-500 mb-6">
              浏览商品，设置目标价格，降价时自动通知您
            </p>
            <Link
              to="/"
              className="px-6 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition-colors"
            >
              去逛逛
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {alerts.map((alert) => {
              const product = getProduct(alert.productId);
              const platformConfig = PLATFORM_CONFIG[alert.platform];
              const progressPercent = getProgressPercent(
                alert.currentPrice || 0,
                alert.targetPrice
              );
              const priceDiff = (alert.currentPrice || 0) - alert.targetPrice;

              if (!product) return null;

              return (
                <div
                  key={alert.id}
                  className={`bg-white rounded-2xl p-6 border transition-all ${
                    alert.isActive
                      ? 'border-blue-200 shadow-sm hover:shadow-md'
                      : 'border-gray-200 opacity-60'
                  }`}
                >
                  <div className="flex gap-6">
                    <Link
                      to={`/product/${product.id}`}
                      className="w-24 h-24 flex-shrink-0 rounded-lg overflow-hidden bg-gray-100"
                    >
                      <img
                        src={product.imageUrl}
                        alt={product.name}
                        className="w-full h-full object-cover"
                      />
                    </Link>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4 mb-2">
                        <Link
                          to={`/product/${product.id}`}
                          className="font-medium text-gray-900 hover:text-blue-600 line-clamp-1"
                        >
                          {product.name}
                        </Link>
                        <div className="flex items-center gap-2">
                          {togglingId === alert.id ? (
                            <Loader2 size={20} className="text-gray-400 animate-spin" />
                          ) : (
                            <button
                              onClick={() => handleToggle(alert.id, alert.isActive)}
                              className="text-gray-400 hover:text-blue-600 transition-colors"
                            >
                              {alert.isActive ? (
                                <ToggleRight size={24} className="text-blue-600" />
                              ) : (
                                <ToggleLeft size={24} />
                              )}
                            </button>
                          )}
                          <button
                            onClick={() => handleDelete(alert.id)}
                            className="text-gray-400 hover:text-red-600 transition-colors"
                          >
                            <Trash2 size={18} />
                          </button>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 mb-4">
                        <span
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs"
                          style={{ backgroundColor: `${platformConfig?.color}20`, color: platformConfig?.color }}
                        >
                          <span>{platformConfig?.logo}</span>
                          {platformConfig?.name}
                        </span>
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 rounded-full text-xs text-gray-600">
                          {alert.notifyType === 'email' ? (
                            <>
                              <Mail size={12} />
                              邮件通知
                            </>
                          ) : (
                            <>
                              <Smartphone size={12} />
                              站内推送
                            </>
                          )}
                        </span>
                        <span className="inline-flex items-center gap-1 text-xs text-gray-500">
                          <Clock size={12} />
                          {formatRelativeTime(alert.createdAt)}创建
                        </span>
                      </div>

                      <div className="flex items-center gap-8">
                        <div>
                          <div className="text-xs text-gray-500 mb-1">当前价格</div>
                          <div className="text-xl font-bold text-gray-900">
                            {formatPrice(alert.currentPrice)}
                          </div>
                        </div>

                        <div className="flex-1">
                          <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                            <span>降价进度</span>
                            <span className="flex items-center gap-1">
                              <TrendingDown size={12} className="text-green-600" />
                              还差 {formatPrice(priceDiff)}
                            </span>
                          </div>
                          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-blue-500 to-green-500 rounded-full transition-all duration-500"
                              style={{ width: `${progressPercent}%` }}
                            />
                          </div>
                        </div>

                        <div className="text-right">
                          <div className="text-xs text-gray-500 mb-1">目标价格</div>
                          <div className="text-xl font-bold text-green-600">
                            {formatPrice(alert.targetPrice)}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="mt-8 bg-white rounded-2xl p-6">
          <h3 className="text-lg font-bold mb-4">💡 降价提醒使用技巧</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold flex-shrink-0">
                1
              </div>
              <div>
                <div className="font-medium mb-1">合理设置目标价</div>
                <div className="text-sm text-gray-600">
                  建议参考历史最低价设置，不要设置过低的目标价
                </div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold flex-shrink-0">
                2
              </div>
              <div>
                <div className="font-medium mb-1">选择合适的平台</div>
                <div className="text-sm text-gray-600">
                  不同平台价格策略不同，可针对特定平台设置提醒
                </div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold flex-shrink-0">
                3
              </div>
              <div>
                <div className="font-medium mb-1">开启推送通知</div>
                <div className="text-sm text-gray-600">
                  确保开启浏览器通知权限，不错过任何降价信息
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
