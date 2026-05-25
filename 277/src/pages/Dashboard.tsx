import { useEffect, useState } from 'react'
import { Layers, FolderTree, Users, TrendingUp, Clock, Download } from 'lucide-react'
import { useIconStore, type Icon } from '@/store/iconStore'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const { icons, categories, fetchIcons, fetchCategories } = useIconStore()
  const [recentIcons, setRecentIcons] = useState<Icon[]>([])

  useEffect(() => {
    fetchIcons()
    fetchCategories()
  }, [fetchIcons, fetchCategories])

  useEffect(() => {
    const sorted = [...icons].sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    )
    setRecentIcons(sorted.slice(0, 6))
  }, [icons])

  const stats = [
    {
      label: '图标总数',
      value: icons.length,
      icon: Layers,
      color: 'bg-primary-500',
    },
    {
      label: '分类数量',
      value: categories.length,
      icon: FolderTree,
      color: 'bg-emerald-500',
    },
    {
      label: '团队成员',
      value: 3,
      icon: Users,
      color: 'bg-amber-500',
    },
    {
      label: '本周下载',
      value: 128,
      icon: TrendingUp,
      color: 'bg-rose-500',
    },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="font-display text-2xl font-bold text-gray-900">仪表板</h1>
        <p className="text-gray-500 mt-1">欢迎回来，这是您的图标库概览</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div key={stat.label} className="card p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">{stat.label}</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{stat.value}</p>
              </div>
              <div className={`w-12 h-12 ${stat.color} rounded-xl flex items-center justify-center`}>
                <stat.icon className="text-white" size={24} />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <Clock size={20} className="text-primary-500" />
              最近上传
            </h2>
            <Link to="/icons" className="text-sm text-primary-500 hover:text-primary-600">
              查看全部
            </Link>
          </div>

          {recentIcons.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <Layers size={48} className="mx-auto mb-4 opacity-50" />
              <p>暂无图标，开始上传吧</p>
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-4">
              {recentIcons.map((icon) => (
                <Link
                  key={icon.id}
                  to={`/icons/${icon.id}`}
                  className="aspect-square bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors group"
                >
                  <div
                    className="w-full h-full flex items-center justify-center"
                    dangerouslySetInnerHTML={{ __html: icon.svgContent }}
                  />
                  <p className="text-xs text-gray-600 mt-2 truncate text-center">{icon.name}</p>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="card p-6">
          <h2 className="font-semibold text-gray-900 flex items-center gap-2 mb-4">
            <Download size={20} className="text-emerald-500" />
            快捷操作
          </h2>
          <div className="space-y-3">
            <Link
              to="/upload"
              className="flex items-center gap-4 p-4 bg-primary-50 rounded-lg hover:bg-primary-100 transition-colors"
            >
              <div className="w-10 h-10 bg-primary-500 rounded-lg flex items-center justify-center">
                <Download className="text-white" size={20} />
              </div>
              <div>
                <p className="font-medium text-gray-900">上传新图标</p>
                <p className="text-sm text-gray-500">支持SVG格式批量上传</p>
              </div>
            </Link>

            <Link
              to="/categories"
              className="flex items-center gap-4 p-4 bg-emerald-50 rounded-lg hover:bg-emerald-100 transition-colors"
            >
              <div className="w-10 h-10 bg-emerald-500 rounded-lg flex items-center justify-center">
                <FolderTree className="text-white" size={20} />
              </div>
              <div>
                <p className="font-medium text-gray-900">管理分类</p>
                <p className="text-sm text-gray-500">创建和组织图标分类</p>
              </div>
            </Link>

            <Link
              to="/team"
              className="flex items-center gap-4 p-4 bg-amber-50 rounded-lg hover:bg-amber-100 transition-colors"
            >
              <div className="w-10 h-10 bg-amber-500 rounded-lg flex items-center justify-center">
                <Users className="text-white" size={20} />
              </div>
              <div>
                <p className="font-medium text-gray-900">团队成员</p>
                <p className="text-sm text-gray-500">邀请成员和管理权限</p>
              </div>
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
