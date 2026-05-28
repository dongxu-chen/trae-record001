import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  BarChart3, 
  Calendar, 
  Clock, 
  TrendingUp,
  ScanLine
} from 'lucide-react';
import { useHistory } from '../../hooks/useHistory';
import { calculateStatistics } from '../../utils/statistics';
import { Heatmap } from '../Statistics/Heatmap';

export function StatisticsPage() {
  const navigate = useNavigate();
  const { records } = useHistory();

  const stats = useMemo(() => calculateStatistics(records), [records]);

  const avgScansPerDay = stats.weeklyScans / 7;

  const typeLabels: Record<string, string> = {
    qrcode: '二维码',
    barcode: '条形码',
    manual: '手动输入',
  };

  const typeColors: Record<string, string> = {
    qrcode: 'bg-blue-500',
    barcode: 'bg-green-500',
    manual: 'bg-purple-500',
  };

  const maxHourlyCount = Math.max(...stats.hourlyStats.map((h) => h.count), 1);

  return (
    <div className="min-h-screen bg-[#0d1117]">
      <div className="sticky top-0 z-40 bg-[#0d1117]/95 backdrop-blur-xl border-b border-gray-800">
        <div className="px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            className="p-2 -ml-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-lg font-semibold text-white">扫码统计</h1>
        </div>
      </div>

      <div className="p-4 max-w-2xl mx-auto space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-[#161b22] rounded-xl border border-gray-700/50 p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <ScanLine className="w-4 h-4 text-blue-400" />
              </div>
              <span className="text-xs text-gray-500">总扫码次数</span>
            </div>
            <p className="text-2xl font-bold text-white">{stats.totalScans}</p>
          </div>

          <div className="bg-[#161b22] rounded-xl border border-gray-700/50 p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center">
                <Calendar className="w-4 h-4 text-green-400" />
              </div>
              <span className="text-xs text-gray-500">今日扫码</span>
            </div>
            <p className="text-2xl font-bold text-white">{stats.todayScans}</p>
          </div>

          <div className="bg-[#161b22] rounded-xl border border-gray-700/50 p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
                <TrendingUp className="w-4 h-4 text-purple-400" />
              </div>
              <span className="text-xs text-gray-500">本周扫码</span>
            </div>
            <p className="text-2xl font-bold text-white">{stats.weeklyScans}</p>
          </div>

          <div className="bg-[#161b22] rounded-xl border border-gray-700/50 p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-orange-500/20 flex items-center justify-center">
                <BarChart3 className="w-4 h-4 text-orange-400" />
              </div>
              <span className="text-xs text-gray-500">日均扫码</span>
            </div>
            <p className="text-2xl font-bold text-white">{avgScansPerDay.toFixed(1)}</p>
          </div>
        </div>

        <Heatmap data={stats.heatmapData} title="各时段扫码热力图" />

        <div className="bg-[#161b22] rounded-xl border border-gray-700/50 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-4 h-4 text-gray-400" />
            <h3 className="text-sm font-medium text-gray-400">24小时扫码分布</h3>
          </div>
          
          <div className="flex items-end gap-0.5 h-32">
            {stats.hourlyStats.map((stat) => (
              <div
                key={stat.hour}
                className="flex-1 flex flex-col items-center justify-end"
              >
                <div
                  className={`w-full rounded-t transition-all ${
                    stat.hour === stats.maxHourlyPeak.hour
                      ? 'bg-blue-500'
                      : 'bg-blue-500/40'
                  }`}
                  style={{ height: `${(stat.count / maxHourlyCount) * 100}%` }}
                  title={`${stat.label}: ${stat.count} 次`}
                />
              </div>
            ))}
          </div>
          
          <div className="flex justify-between mt-2">
            <span className="text-[10px] text-gray-500">00:00</span>
            <span className="text-[10px] text-gray-500">12:00</span>
            <span className="text-[10px] text-gray-500">24:00</span>
          </div>
          
          {stats.maxHourlyPeak.count > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-700/50">
              <p className="text-xs text-gray-500">
                扫码高峰: <span className="text-blue-400 font-medium">
                  {stats.hourlyStats[stats.maxHourlyPeak.hour]?.label}
                </span> ({stats.maxHourlyPeak.count} 次)
              </p>
            </div>
          )}
        </div>

        <div className="bg-[#161b22] rounded-xl border border-gray-700/50 p-4">
          <h3 className="text-sm font-medium text-gray-400 mb-4">扫码类型分布</h3>
          
          <div className="space-y-3">
            {Object.entries(stats.scanTypes).map(([type, count]) => (
              <div key={type} className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${typeColors[type] || 'bg-gray-500'}`} />
                <span className="text-sm text-gray-300 w-20">{typeLabels[type] || type}</span>
                <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${typeColors[type] || 'bg-gray-500'}`}
                    style={{ width: `${(count / stats.totalScans) * 100}%` }}
                  />
                </div>
                <span className="text-sm text-gray-400 w-12 text-right">
                  {count} ({((count / stats.totalScans) * 100).toFixed(0)}%)
                </span>
              </div>
            ))}
            
            {Object.keys(stats.scanTypes).length === 0 && (
              <p className="text-sm text-gray-500 text-center py-4">暂无统计数据</p>
            )}
          </div>
        </div>

        <div className="bg-[#161b22] rounded-xl border border-gray-700/50 p-4">
          <h3 className="text-sm font-medium text-gray-400 mb-4">近7天扫码趋势</h3>
          
          {stats.dailyStats.length > 0 ? (
            <div className="flex items-end gap-2 h-24">
              {stats.dailyStats.map((stat, index) => (
                <div
                  key={stat.date}
                  className="flex-1 flex flex-col items-center"
                >
                  <div
                    className="w-full bg-purple-500/60 rounded-t transition-all hover:bg-purple-400"
                    style={{ 
                      height: `${(stat.count / Math.max(...stats.dailyStats.map((d) => d.count), 1)) * 100}%`,
                      minHeight: stat.count > 0 ? '4px' : '0'
                    }}
                    title={`${stat.label}: ${stat.count} 次`}
                  />
                  <span className="text-[10px] text-gray-500 mt-1">{stat.label}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500 text-center py-4">暂无统计数据</p>
          )}
        </div>
      </div>
    </div>
  );
}
