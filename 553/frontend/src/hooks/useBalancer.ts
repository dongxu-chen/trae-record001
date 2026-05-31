import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getMigrationPlan, executeMigrations, getMigrationTasks, moveShard, simulateMigration } from '../api/balancer'

export function useMigrationPlan() {
  return useQuery({
    queryKey: ['balancer', 'plan'],
    queryFn: getMigrationPlan,
    refetchInterval: 15000,
  })
}

export function useMigrationTasks() {
  return useQuery({
    queryKey: ['balancer', 'tasks'],
    queryFn: getMigrationTasks,
    refetchInterval: 3000,
  })
}

export function useExecuteMigrations() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: executeMigrations,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['balancer'] })
      queryClient.invalidateQueries({ queryKey: ['cluster'] })
    },
  })
}

export function useMoveShard() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: moveShard,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['balancer'] })
      queryClient.invalidateQueries({ queryKey: ['cluster'] })
    },
  })
}

export function useSimulateMigration() {
  return useQuery({
    queryKey: ['balancer', 'simulate'],
    queryFn: simulateMigration,
    enabled: false,
  })
}
