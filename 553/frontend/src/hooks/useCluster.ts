import { useQuery } from '@tanstack/react-query'
import { getClusterHealth, getShardDistribution, getNodes, getShards } from '../api/cluster'

export function useClusterHealth() {
  return useQuery({
    queryKey: ['cluster', 'health'],
    queryFn: getClusterHealth,
    refetchInterval: 5000,
  })
}

export function useShardDistribution() {
  return useQuery({
    queryKey: ['cluster', 'distribution'],
    queryFn: getShardDistribution,
    refetchInterval: 10000,
  })
}

export function useNodes() {
  return useQuery({
    queryKey: ['cluster', 'nodes'],
    queryFn: getNodes,
    refetchInterval: 30000,
  })
}

export function useShards() {
  return useQuery({
    queryKey: ['cluster', 'shards'],
    queryFn: getShards,
    refetchInterval: 10000,
  })
}
