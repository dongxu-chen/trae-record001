import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getAllNodeLoads,
  getNodeLoad,
  getSpeedInfo,
  setAdaptiveSpeed,
  getAllIndexHeat,
  getIndexHeat,
  getHotIndices,
  getAutoScalingStatus,
  triggerScaleOut,
} from '../api/monitor'

export function useAllNodeLoads() {
  return useQuery({
    queryKey: ['monitor', 'loads'],
    queryFn: getAllNodeLoads,
    refetchInterval: 15000,
  })
}

export function useNodeLoad(nodeName: string) {
  return useQuery({
    queryKey: ['monitor', 'load', nodeName],
    queryFn: () => getNodeLoad(nodeName),
    refetchInterval: 15000,
  })
}

export function useSpeedInfo() {
  return useQuery({
    queryKey: ['monitor', 'speed'],
    queryFn: getSpeedInfo,
    refetchInterval: 10000,
  })
}

export function useSetAdaptiveSpeed() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: setAdaptiveSpeed,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitor', 'speed'] })
    },
  })
}

export function useAllIndexHeat() {
  return useQuery({
    queryKey: ['monitor', 'heat'],
    queryFn: getAllIndexHeat,
    refetchInterval: 30000,
  })
}

export function useIndexHeat(indexName: string) {
  return useQuery({
    queryKey: ['monitor', 'heat', indexName],
    queryFn: () => getIndexHeat(indexName),
    refetchInterval: 30000,
  })
}

export function useHotIndices() {
  return useQuery({
    queryKey: ['monitor', 'hotIndices'],
    queryFn: getHotIndices,
    refetchInterval: 30000,
  })
}

export function useAutoScalingStatus() {
  return useQuery({
    queryKey: ['monitor', 'autoScaling'],
    queryFn: getAutoScalingStatus,
    refetchInterval: 30000,
  })
}

export function useTriggerScaleOut() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: triggerScaleOut,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitor', 'autoScaling'] })
    },
  })
}
