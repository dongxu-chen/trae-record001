import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Doughnut } from 'react-chartjs-2';
import { BarChart3, TrendingUp, Users, Globe, Download, Calendar } from 'lucide-react';
import { toast } from '@/components/ui/toast';
import { useAuthStore } from '@/store';
import type { StatisticsOverview } from '@/types';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const mockStats: StatisticsOverview = {
  totalScans: 15420,
  totalCodes: 28,
  scansThisWeek: 3240,
  topPerformingCodes: [
    { id: '1', name: '产品宣传页', scans: 5280 },
    { id: '2', name: '活动报名', scans: 3420 },
    { id: '3', name: '官网链接', scans: 2150 },
    { id: '4', name: '联系我们', scans: 1890 },
    { id: '5', name: '下载手册', scans: 1240 },
  ],
  scanTrend: Array.from({ length: 7 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (6 - i));
    return {
      date: date.toISOString().slice(5, 10),
      count: Math.floor(Math.random() * 500) + 200,
    };
  }),
  deviceDistribution: [
    { type: 'mobile', count: 10240, percentage: 66.4 },
    { type: 'desktop', count: 4120, percentage: 26.7 },
    { type: 'tablet', count: 1060, percentage: 6.9 },
  ],
};

export default function Statistics() {
  const { isAuthenticated } = useAuthStore();
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('7d');
  const [stats, setStats] = useState<StatisticsOverview>(mockStats);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setStats(mockStats);
  }, [timeRange]);

  const handleExport = () => {
    toast.success('统计报表已导出');
  };

  if (!isAuthenticated()) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <BarChart3 className="mx-auto h-16 w-16 text-slate-600 mb-4" />
          <h2 className="text-2xl font-bold text-slate-300 mb-2">请先登录</h2>
          <p className="text-slate-500">登录后即可查看扫描统计数据</p>
        </div>
      </div>
    );
  }

  const lineChartData = {
    labels: stats.scanTrend.map((d) => d.date),
    datasets: [
      {
        label: '扫描次数',
        data: stats.scanTrend.map((d) => d.count),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4,
        pointBackgroundColor: 'rgb(59, 130, 246)',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
      },
    ],
  };

  const doughnutData = {
    labels: stats.deviceDistribution.map((d) =>
      d.type === 'mobile' ? '移动设备' : d.type === 'desktop' ? '桌面设备' : '平板'
    ),
    datasets: [
      {
        data: stats.deviceDistribution.map((d) => d.percentage),
        backgroundColor: [
          'rgba(59, 130, 246, 0.8)',
          'rgba(6, 182, 212, 0.8)',
          'rgba(139, 92, 246, 0.8)',
        ],
        borderColor: [
          'rgb(59, 130, 246)',
          'rgb(6, 182, 212)',
          'rgb(139, 92, 246)',
        ],
        borderWidth: 2,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        display: false,
      },
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(148, 163, 184, 0.1)',
        },
        ticks: {
          color: '#94a3b8',
        },
      },
      y: {
        grid: {
          color: 'rgba(148, 163, 184, 0.1)',
        },
        ticks: {
          color: '#94a3b8',
        },
      },
    },
  };

  const doughnutOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: {
          color: '#94a3b8',
          padding: 20,
        },
      },
    },
  };

  const statCards = [
    {
      label: '总扫描次数',
      value: stats.totalScans.toLocaleString(),
      icon: TrendingUp,
      color: 'from-blue-500 to-blue-600',
    },
    {
      label: '二维码总数',
      value: stats.totalCodes,
      icon: BarChart3,
      color: 'from-cyan-500 to-cyan-600',
    },
    {
      label: '本周扫描',
      value: stats.scansThisWeek.toLocaleString(),
      icon: Calendar,
      color: 'from-purple-500 to-purple-600',
    },
    {
      label: '涉及国家',
      value: '12',
      icon: Globe,
      color: 'from-pink-500 to-pink-600',
    },
  ];

  return (
    <div className="min-h-screen bg-slate-950 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 via-cyan-400 to-blue-500 bg-clip-text text-transparent mb-2">
              统计中心
            </h1>
            <p className="text-slate-400">查看二维码扫描数据和趋势分析</p>
          </motion.div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 bg-slate-900/50 rounded-xl p-1 border border-slate-800/50">
              {(['7d', '30d', '90d'] as const).map((range) => (
                <button
                  key={range}
                  onClick={() => setTimeRange(range)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    timeRange === range
                      ? 'bg-blue-600 text-white'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {range === '7d' ? '7天' : range === '30d' ? '30天' : '90天'}
                </button>
              ))}
            </div>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleExport}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            >
              <Download size={16} />
              导出报表
            </motion.button>
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {statCards.map((card, index) => (
            <motion.div
              key={card.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="relative rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6 overflow-hidden"
            >
              <div
                className={`absolute inset-0 bg-gradient-to-br ${card.color} opacity-10`}
              />
              <div className="relative">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm text-slate-400">{card.label}</span>
                  <card.icon size={20} className="text-slate-500" />
                </div>
                <p className="text-3xl font-bold text-slate-100">{card.value}</p>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="grid lg:grid-cols-3 gap-6 mb-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="lg:col-span-2 rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6"
          >
            <h3 className="font-semibold text-slate-200 mb-6">扫描趋势</h3>
            <div className="h-72">
              <Line data={lineChartData} options={chartOptions} />
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6"
          >
            <h3 className="font-semibold text-slate-200 mb-6">设备分布</h3>
            <div className="h-72 flex items-center justify-center">
              <Doughnut data={doughnutData} options={doughnutOptions} />
            </div>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6"
        >
          <h3 className="font-semibold text-slate-200 mb-6">表现最佳的二维码</h3>
          <div className="space-y-3">
            {stats.topPerformingCodes.map((code, index) => (
              <div
                key={code.id}
                className="flex items-center gap-4 p-3 rounded-xl bg-slate-800/30 hover:bg-slate-800/50 transition-colors"
              >
                <span
                  className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm ${
                    index === 0
                      ? 'bg-yellow-500/20 text-yellow-400'
                      : index === 1
                      ? 'bg-slate-400/20 text-slate-400'
                      : index === 2
                      ? 'bg-amber-600/20 text-amber-500'
                      : 'bg-slate-700/50 text-slate-500'
                  }`}
                >
                  {index + 1}
                </span>
                <span className="flex-1 text-slate-300 font-medium">
                  {code.name}
                </span>
                <span className="text-slate-400 font-mono">
                  {code.scans.toLocaleString()} 次
                </span>
                <div className="w-32 h-2 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full"
                    style={{
                      width: `${(code.scans / stats.topPerformingCodes[0].scans) * 100}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
