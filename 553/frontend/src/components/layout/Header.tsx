import { BellIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
import { useClusterHealth } from '../../hooks/useCluster'
import { getStatusColor } from '../../utils/format'

export function Header() {
  const { data: health } = useClusterHealth()

  return (
    <header className="h-16 bg-es-dark-800 border-b border-es-dark-700 px-6 flex items-center justify-between">
      <div className="flex items-center space-x-4">
        <h1 className="text-xl font-semibold text-white">Elasticsearch 分片均衡管理</h1>
        {health && (
          <div className="flex items-center space-x-2">
            <span className={`status-dot ${getStatusColor(health.status)} animate-pulse-slow`}></span>
            <span className="text-sm text-es-dark-200">
              {health.cluster_name}
            </span>
            <span className={`text-sm font-medium ${health.status === 'green' ? 'text-es-green' : health.status === 'yellow' ? 'text-es-yellow' : 'text-es-red'}`}>
              {health.status.toUpperCase()}
            </span>
          </div>
        )}
      </div>
      <div className="flex items-center space-x-3">
        <button className="p-2 rounded-lg text-es-dark-300 hover:bg-es-dark-700 hover:text-white transition-colors">
          <ArrowPathIcon className="w-5 h-5" />
        </button>
        <button className="p-2 rounded-lg text-es-dark-300 hover:bg-es-dark-700 hover:text-white transition-colors relative">
          <BellIcon className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-es-red rounded-full"></span>
        </button>
        <div className="h-8 w-8 bg-es-blue rounded-full flex items-center justify-center">
          <span className="text-sm font-medium text-white">A</span>
        </div>
      </div>
    </header>
  )
}
