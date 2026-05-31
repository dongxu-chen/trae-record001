import { Link, useLocation } from 'react-router-dom'
import {
  ServerIcon,
  CircleStackIcon,
  ArrowPathIcon,
  Cog6ToothIcon,
  ChartBarIcon,
  BeakerIcon,
} from '@heroicons/react/24/outline'
import clsx from 'clsx'

const navigation = [
  { name: '仪表盘', href: '/', icon: ChartBarIcon },
  { name: '节点管理', href: '/nodes', icon: ServerIcon },
  { name: '分片分布', href: '/shards', icon: CircleStackIcon },
  { name: '迁移任务', href: '/migrations', icon: ArrowPathIcon },
  { name: '迁移演练', href: '/simulation', icon: BeakerIcon },
  { name: '系统设置', href: '/settings', icon: Cog6ToothIcon },
]

export function Sidebar() {
  const location = useLocation()

  return (
    <div className="flex h-full flex-col bg-es-dark-900 w-64 border-r border-es-dark-700">
      <div className="flex h-16 items-center px-6 border-b border-es-dark-700">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-es-blue rounded-lg flex items-center justify-center">
            <CircleStackIcon className="w-5 h-5 text-white" />
          </div>
          <span className="text-lg font-bold text-white">ES Balancer</span>
        </div>
      </div>
      <nav className="flex-1 space-y-1 px-4 py-6">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href
          return (
            <Link
              key={item.name}
              to={item.href}
              className={clsx(
                'group flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-all duration-200',
                isActive
                  ? 'bg-es-blue text-white shadow-lg shadow-es-blue/30'
                  : 'text-es-dark-200 hover:bg-es-dark-800 hover:text-white'
              )}
            >
              <item.icon
                className={clsx(
                  'mr-3 h-5 w-5 flex-shrink-0',
                  isActive ? 'text-white' : 'text-es-dark-400 group-hover:text-white'
                )}
                aria-hidden="true"
              />
              {item.name}
            </Link>
          )
        })}
      </nav>
      <div className="p-4 border-t border-es-dark-700">
        <div className="text-xs text-es-dark-400">
          <p>版本 1.0.0</p>
          <p className="mt-1">Elasticsearch 分片均衡工具</p>
        </div>
      </div>
    </div>
  )
}
