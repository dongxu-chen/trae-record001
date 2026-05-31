import React, { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart,
} from 'recharts';
import type { PriceHistory } from '../types';
import { formatPrice, formatDate, aggregatePriceHistory } from '../utils/format';

interface PriceChartProps {
  history: PriceHistory[];
  currentPrice: number;
  lowestEver: number;
}

const TIME_RANGES = [
  { key: '7', label: '7天', days: 7 },
  { key: '30', label: '30天', days: 30 },
  { key: '90', label: '90天', days: 90 },
  { key: '365', label: '1年', days: 365 },
];

export default function PriceChart({ history, currentPrice, lowestEver }: PriceChartProps) {
  const [selectedRange, setSelectedRange] = useState('30');
  const [chartType, setChartType] = useState<'line' | 'area'>('area');

  const filteredData = useMemo(() => {
    const days = parseInt(selectedRange);
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - days);

    const filtered = history.filter((h) => new Date(h.date) >= cutoffDate);
    return aggregatePriceHistory(filtered);
  }, [history, selectedRange]);

  const stats = useMemo(() => {
    if (filteredData.length === 0) return { min: 0, max: 0, avg: 0 };
    const prices = filteredData.map((d) => d.price);
    return {
      min: Math.min(...prices),
      max: Math.max(...prices),
      avg: prices.reduce((a, b) => a + b, 0) / prices.length,
    };
  }, [filteredData]);

  const trend = useMemo(() => {
    if (filteredData.length < 2) return 0;
    const first = filteredData[0].price;
    const last = filteredData[filteredData.length - 1].price;
    return ((last - first) / first) * 100;
  }, [filteredData]);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 rounded-lg shadow-lg border border-gray-200">
          <p className="text-sm text-gray-600">{formatDate(label)}</p>
          <p className="text-lg font-bold text-red-600">
            {formatPrice(payload[0].value)}
          </p>
          {payload[0].payload.isLowest && (
            <p className="text-xs text-green-600">📉 历史最低价</p>
          )}
        </div>
      );
    }
    return null;
  };

  const chartData = useMemo(() => {
    return filteredData.map((d) => ({
      ...d,
      isLowest: d.price <= lowestEver * 1.01,
    }));
  }, [filteredData, lowestEver]);

  if (filteredData.length === 0) {
    return (
      <div className="h-80 flex items-center justify-center text-gray-500 bg-gray-50 rounded-2xl">
        暂无价格历史数据
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl p-6 shadow-md">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-bold text-gray-900">价格走势</h3>
        <div className="flex items-center gap-4">
          <div className="flex bg-gray-100 rounded-lg p-1">
            {TIME_RANGES.map((range) => (
              <button
                key={range.key}
                onClick={() => setSelectedRange(range.key)}
                className={`px-3 py-1.5 text-sm rounded-md transition-all ${
                  selectedRange === range.key
                    ? 'bg-white text-blue-600 shadow font-medium'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {range.label}
              </button>
            ))}
          </div>
          <div className="flex bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setChartType('area')}
              className={`px-3 py-1.5 text-sm rounded-md transition-all ${
                chartType === 'area'
                  ? 'bg-white text-blue-600 shadow font-medium'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              面积图
            </button>
            <button
              onClick={() => setChartType('line')}
              className={`px-3 py-1.5 text-sm rounded-md transition-all ${
                chartType === 'line'
                  ? 'bg-white text-blue-600 shadow font-medium'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              折线图
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-xl">
          <p className="text-sm text-blue-600 mb-1">当前价格</p>
          <p className="text-2xl font-bold text-blue-700">{formatPrice(currentPrice)}</p>
        </div>
        <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-xl">
          <p className="text-sm text-green-600 mb-1">区间最低</p>
          <p className="text-2xl font-bold text-green-700">{formatPrice(stats.min)}</p>
        </div>
        <div className="bg-gradient-to-br from-red-50 to-red-100 p-4 rounded-xl">
          <p className="text-sm text-red-600 mb-1">区间最高</p>
          <p className="text-2xl font-bold text-red-700">{formatPrice(stats.max)}</p>
        </div>
        <div className={`bg-gradient-to-br ${
          trend < 0 ? 'from-emerald-50 to-emerald-100' : 'from-orange-50 to-orange-100'
        } p-4 rounded-xl`}>
          <p className={`text-sm ${trend < 0 ? 'text-emerald-600' : 'text-orange-600'} mb-1`}>
            {trend < 0 ? '价格趋势 ↓' : '价格趋势 ↑'}
          </p>
          <p className={`text-2xl font-bold ${trend < 0 ? 'text-emerald-700' : 'text-orange-700'}`}>
            {trend > 0 ? '+' : ''}{trend.toFixed(1)}%
          </p>
        </div>
      </div>

      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          {chartType === 'area' ? (
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f97316" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 12 }}
                tickFormatter={(v) => v.slice(5)}
                stroke="#9ca3af"
              />
              <YAxis
                domain={['auto', 'auto']}
                tick={{ fontSize: 12 }}
                tickFormatter={(v) => `¥${v}`}
                stroke="#9ca3af"
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine
                y={currentPrice}
                stroke="#ef4444"
                strokeDasharray="5 5"
                label={{ value: '当前', position: 'insideTopRight', fill: '#ef4444', fontSize: 12 }}
              />
              <ReferenceLine
                y={lowestEver}
                stroke="#10b981"
                strokeDasharray="5 5"
                label={{ value: '史低', position: 'insideBottomRight', fill: '#10b981', fontSize: 12 }}
              />
              <Area
                type="monotone"
                dataKey="price"
                stroke="#f97316"
                strokeWidth={2}
                fill="url(#colorPrice)"
                dot={{ r: 3, fill: '#f97316' }}
                activeDot={{ r: 6, fill: '#f97316', stroke: '#fff', strokeWidth: 2 }}
              />
            </AreaChart>
          ) : (
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 12 }}
                tickFormatter={(v) => v.slice(5)}
                stroke="#9ca3af"
              />
              <YAxis
                domain={['auto', 'auto']}
                tick={{ fontSize: 12 }}
                tickFormatter={(v) => `¥${v}`}
                stroke="#9ca3af"
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine
                y={currentPrice}
                stroke="#ef4444"
                strokeDasharray="5 5"
                label={{ value: '当前', position: 'insideTopRight', fill: '#ef4444', fontSize: 12 }}
              />
              <ReferenceLine
                y={lowestEver}
                stroke="#10b981"
                strokeDasharray="5 5"
                label={{ value: '史低', position: 'insideBottomRight', fill: '#10b981', fontSize: 12 }}
              />
              <Line
                type="monotone"
                dataKey="price"
                stroke="#f97316"
                strokeWidth={2}
                dot={{ r: 3, fill: '#f97316' }}
                activeDot={{ r: 6, fill: '#f97316', stroke: '#fff', strokeWidth: 2 }}
              />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
