import { apiClient } from './client'
import type { Config } from '../types'

export const getConfig = async (): Promise<Config> => {
  const response = await apiClient.get<Config>('/config')
  return response.data
}

export const setSpeedLimit = async (maxBytesPerSec: string): Promise<{ status: string; message: string }> => {
  const response = await apiClient.post('/settings/speed-limit', {
    max_bytes_per_sec: maxBytesPerSec,
  })
  return response.data
}

export const setDiskWatermark = async (data: {
  low: string
  high: string
  flood: string
}): Promise<{ status: string; message: string }> => {
  const response = await apiClient.post('/settings/disk-watermark', data)
  return response.data
}
