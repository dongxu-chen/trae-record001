export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export function formatPercent(value: number): string {
  return value.toFixed(2) + '%'
}

export function getStatusColor(status: string): string {
  switch (status) {
    case 'green':
      return 'bg-es-green'
    case 'yellow':
      return 'bg-es-yellow'
    case 'red':
      return 'bg-es-red'
    default:
      return 'bg-gray-500'
  }
}

export function getStatusTextColor(status: string): string {
  switch (status) {
    case 'green':
      return 'text-es-green'
    case 'yellow':
      return 'text-es-yellow'
    case 'red':
      return 'text-es-red'
    default:
      return 'text-gray-500'
  }
}

export function getDiskUsageColor(percent: number): string {
  if (percent >= 90) return 'text-es-red'
  if (percent >= 80) return 'text-es-yellow'
  return 'text-es-green'
}

export function getNodeTypeColor(type: string): string {
  switch (type) {
    case 'hot':
      return 'bg-orange-500 text-white'
    case 'cold':
      return 'bg-blue-500 text-white'
    default:
      return 'bg-gray-500 text-white'
  }
}

export function formatNumber(value: number): string {
  return value.toLocaleString()
}
