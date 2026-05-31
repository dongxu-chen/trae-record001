import { apiClient } from './client'
import type { NodeLoadHistory, SpeedInfo, IndexHeatInfo, AutoScalingStatus } from '../types'

export const getAllNodeLoads = async (): Promise<Record<string, NodeLoadHistory>> => {
  const response = await apiClient.get<{ loads: Record<string, NodeLoadHistory> }>('/monitor/load')
  return response.data.loads
}

export const getNodeLoad = async (nodeName: string): Promise<NodeLoadHistory> => {
  const response = await apiClient.get<NodeLoadHistory>(`/monitor/load/${nodeName}`)
  return response.data
}

export const getSpeedInfo = async (): Promise<SpeedInfo> => {
  const response = await apiClient.get<SpeedInfo>('/monitor/speed')
  return response.data
}

export const setAdaptiveSpeed = async (speed: string): Promise<{ status: string; current_speed: string }> => {
  const response = await apiClient.post('/monitor/speed', { speed })
  return response.data
}

export const getAllIndexHeat = async (): Promise<Record<string, IndexHeatInfo>> => {
  const response = await apiClient.get<{ heats: Record<string, IndexHeatInfo> }>('/monitor/heat')
  return response.data.heats
}

export const getIndexHeat = async (indexName: string): Promise<IndexHeatInfo> => {
  const response = await apiClient.get<IndexHeatInfo>(`/monitor/heat/${indexName}`)
  return response.data
}

export const getHotIndices = async (): Promise<string[]> => {
  const response = await apiClient.get<{ hot_indices: string[] }>('/monitor/heat/hot-indices')
  return response.data.hot_indices
}

export const getAutoScalingStatus = async (): Promise<AutoScalingStatus> => {
  const response = await apiClient.get<AutoScalingStatus>('/monitor/auto-scaling')
  return response.data
}

export const triggerScaleOut = async (): Promise<{ status: string; auto_scaler?: AutoScalingStatus }> => {
  const response = await apiClient.post('/monitor/auto-scaling/scale-out')
  return response.data
}
