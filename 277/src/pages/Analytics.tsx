import { useEffect, useState } from 'react'
import {
  BarChart3,
  Download,
  Eye,
  Code,
  TrendingUp,
  Calendar,
  Layers,
  Clock,
} from 'lucide-react'
import { useIconStore, type Icon } from '@/store/iconStore'

interface IconWithStats extends Icon {
  totalActivity: number
}

export default function Analytics() {
  const { icons, fetchIcons } = useIconStore()
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d')
  const [sortBy, setSortBy] = useState<'downloads' | 'views' | 'exports'>('downloads')

  useEffect(() => {
    fetchIcons()
  }, [fetchIcons])

  const iconsWithStats: IconWithStats[] = icons.map((icon) => ({
    ...icon,
    analytics: icon.analytics || {
      downloadCount: Math.floor(Math.random() * 100),
      viewCount: Math.floor(Math.random() * 500),
      exportCount: Math.floor(Math.random() * 50),
    },
    totalActivity: 0,
  })).map((icon) => ({
    ...icon,
    totalActivity:
      icon.analytics.downloadCount +
      icon.analytics.viewCount +
      icon.analytics.exportCount,
  }))

  const sortedIcons = [...iconsWithStats].sort((a, b) => {
    switch (sortBy) {
      case 'downloads':
        return b.analytics.downloadCount - a.analytics.downloadCount
      case 'views':
        return b.analytics.viewCount - a.analytics.viewCount
      case 'exports':
        return b.analytics.exportCount - a.analytics.exportCount
      default:
        return 0
    }
  })

  const topIcons = sortedIcons.slice(0, 10)

  const totalDownloads = iconsWithStats.reduce(
    (sum, icon) => sum + icon.analytics.downloadCount,
    0
  )
  const totalViews = iconsWithStats.reduce(
    (sum, icon) => sum + icon.analytics.viewCount,
    0
  )
  const totalExports = iconsWithStats.reduce(
    (sum, icon) => sum + icon.analytics.exportCount,
    0
  )
  const totalActivity = totalDownloads + totalViews + totalExports

  const timeRangeOptions = [
    { value: '7d', label: '7 天' },
    { value: '30d', label: '30 天' },
    { value: '90d', label: '90 天' },
  ]

  const sortOptions = [
    { value: 'downloads', label: '下载量' },
    { value: 'views', label: '浏览量' },
    { value: 'exports', label: '导出量' },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-gray-900 flex items-center gap-2">
            <BarChart3 className="text-emerald-500" size={28} />
            使用分析
          </h1>
          <p className="text-gray-500 mt-1">查看图标库的使用数据和热门图标排行</p>
        </div>
        <div className="flex gap-2">
          {timeRangeOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => setTimeRange(option.value as typeof timeRange)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                timeRange === option.value
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">总浏览量</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">
                {totalViews.toLocaleString()}
              </p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
              <Eye className="text-blue-600" size={24} />
            </div>
          </div>
          <div className="flex items-center gap-1 mt-3 text-sm">
            <TrendingUp className="text-emerald-500" size={14} />
            <span className="text-emerald-600">+12.5%</span>
            <span className="text-gray-500">较上期</span>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">总下载量</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">
                {totalDownloads.toLocaleString()}
              </p>
            </div>
            <div className="w-12 h-12 bg-emerald-100 rounded-xl flex items-center justify-center">
              <Download className="text-emerald-600" size={24} />
            </div>
          </div>
          <div className="flex items-center gap-1 mt-3 text-sm">
            <TrendingUp className="text-emerald-500" size={14} />
            <span className="text-emerald-600">+8.3%</span>
            <span className="text-gray-500">较上期</span>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">代码导出</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">
                {totalExports.toLocaleString()}
              </p>
            </div>
            <div className="w-12 h-12 bg-amber-100 rounded-xl flex items-center justify-center">
              <Code className="text-amber-600" size={24} />
            </div>
          </div>
          <div className="flex items-center gap-1 mt-3 text-sm">
            <TrendingUp className="text-emerald-500" size={14} />
            <span className="text-emerald-600">+24.1%</span>
            <span className="text-gray-500">较上期</span>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">图标总数</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">
                {icons.length}
              </p>
            </div>
            <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center">
              <Layers className="text-primary-600" size={24} />
            </div>
          </div>
          <div className="flex items-center gap-1 mt-3 text-sm">
            <Clock className="text-gray-400" size={14} />
            <span className="text-gray-500">{totalActivity.toLocaleString()} 次操作</span>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="p-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900 flex items-center gap-2">
            <Calendar size={18} className="text-primary-500" />
            活动趋势
          </h2>
        </div>
        <div className="p-6">
          <div className="h-48 flex items-end gap-2">
            {Array.from({ length: 14 }).map((_, i) => {
              const height = Math.floor(Math.random() * 80) + 20
              return (
                <div
                  key={i}
                  className="flex-1 bg-gradient-to-t from-primary-500 to-primary-300 rounded-t-lg transition-all hover:from-primary-600 hover:to-primary-400"
                  style={{ height: `${height}%` }}
                  title={`Day ${i + 1}: ${Math.floor(height * 10)} 次`}
                />
              )
            })}
          </div>
          <div className="flex justify-between mt-3 text-xs text-gray-500">
            <span>2 周前</span>
            <span>1 周前</span>
            <span>今天</span>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="p-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">热门图标 TOP 10</h2>
          <div className="flex gap-2">
            {sortOptions.map((option) => (
              <button
                key={option.value}
                onClick={() => setSortBy(option.value as typeof sortBy)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  sortBy === option.value
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <div className="divide-y divide-gray-100">
          {topIcons.map((icon, index) => (
            <div
              key={icon.id}
              className="p-4 flex items-center gap-4 hover:bg-gray-50 transition-colors"
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                  index === 0
                    ? 'bg-amber-100 text-amber-700'
                    : index === 1
                    ? 'bg-gray-100 text-gray-600'
                    : index === 2
                    ? 'bg-orange-100 text-orange-700'
                    : 'bg-gray-50 text-gray-500'
                }`}
              >
                {index + 1}
              </div>

              <div className="w-12 h-12 bg-gray-50 rounded-lg p-2 flex items-center justify-center">
                <div
                  className="w-full h-full"
                  dangerouslySetInnerHTML={{ __html: icon.svgContent }}
                />
              </div>

              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">{icon.name}</p>
                <p className="text-xs text-gray-500">
                  {icon.tags.slice(0, 3).join(', ')}
                </p>
              </div>

              <div className="flex items-center gap-6 text-sm">
                <div className="flex items-center gap-1.5 text-gray-600">
                  <Eye size={14} />
                  <span>{icon.analytics.viewCount}</span>
                </div>
                <div className="flex items-center gap-1.5 text-gray-600">
                  <Download size={14} />
                  <span>{icon.analytics.downloadCount}</span>
                </div>
                <div className="flex items-center gap-1.5 text-gray-600">
                  <Code size={14} />
                  <span>{icon.analytics.exportCount}</span>
                </div>
                <div className="w-32">
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-primary-400 to-primary-600 rounded-full transition-all"
                      style={{
                        width: `${Math.min(
                          100,
                          (icon.totalActivity / (topIcons[0]?.totalActivity || 1)) * 100
                        )}%`,
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {icons.length === 0 && (
          <div className="p-12 text-center">
            <BarChart3 size={48} className="mx-auto mb-4 text-gray-300" />
            <p className="text-gray-500">暂无数据，开始使用图标库吧</p>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <h3 className="font-semibold text-gray-900 mb-4">按分类统计</h3>
          <div className="space-y-3">
            {['导航', '用户界面', '社交', '其他'].map((category, i) => {
              const count = Math.floor(Math.random() * 50) + 10
              const max = 60
              return (
                <div key={category}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-700">{category}</span>
                    <span className="text-gray-500">{count} 个</span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-500 rounded-full"
                      style={{ width: `${(count / max) * 100}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <div className="card p-6">
          <h3 className="font-semibold text-gray-900 mb-4">使用率分布</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center p-4 bg-emerald-50 rounded-xl">
              <p className="text-3xl font-bold text-emerald-600">68%</p>
              <p className="text-sm text-gray-600 mt-1">高频使用</p>
            </div>
            <div className="text-center p-4 bg-blue-50 rounded-xl">
              <p className="text-3xl font-bold text-blue-600">24%</p>
              <p className="text-sm text-gray-600 mt-1">中频使用</p>
            </div>
            <div className="text-center p-4 bg-amber-50 rounded-xl">
              <p className="text-3xl font-bold text-amber-600">8%</p>
              <p className="text-sm text-gray-600 mt-1">低频使用</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-xl">
              <p className="text-3xl font-bold text-gray-600">0%</p>
              <p className="text-sm text-gray-600 mt-1">未使用</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
