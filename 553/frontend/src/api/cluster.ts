import { apiClient } from './client'
import type { ClusterHealth, ShardDistribution, ShardInfo, NodeInfo } from '../types'

export const getClusterHealth = async (): Promise<ClusterHealth> => {
  const response = await apiClient.get<ClusterHealth>('/cluster/health')
  return response.data
}

export const getNodes = async (): Promise<Record<string, NodeInfo>> => {
  const response = await apiClient.get<Record<string, NodeInfo>>('/cluster/nodes')
  return response.data
}

export const getShards = async (): Promise<ShardInfo[]> => {
  const response = await apiClient.get<{ shards: ShardInfo[] }>('/cluster/shards')
  return response.data.shards
}

export const getShardDistribution = async (): Promise<ShardDistribution> => {
  const response = await apiClient.get<ShardDistribution>('/cluster/distribution')
  return response.data
}
