import { apiClient } from './client'
import type { MigrationPlan, MigrationStatus, BalanceResult, MigrationSimulationResult } from '../types'

export const getMigrationPlan = async (): Promise<MigrationPlan[]> => {
  const response = await apiClient.get<{ plans: MigrationPlan[] }>('/balancer/plan')
  return response.data.plans
}

export const executeMigrations = async (): Promise<BalanceResult> => {
  const response = await apiClient.post<BalanceResult>('/balancer/execute')
  return response.data
}

export const moveShard = async (data: {
  index: string
  shard: string
  from_node: string
  to_node: string
}): Promise<{ status: string; message: string }> => {
  const response = await apiClient.post('/balancer/move', data)
  return response.data
}

export const getMigrationTasks = async (): Promise<MigrationStatus[]> => {
  const response = await apiClient.get<{ tasks: MigrationStatus[] }>('/balancer/tasks')
  return response.data.tasks
}

export const simulateMigration = async (): Promise<MigrationSimulationResult> => {
  const response = await apiClient.get<MigrationSimulationResult>('/balancer/simulate')
  return response.data
}
