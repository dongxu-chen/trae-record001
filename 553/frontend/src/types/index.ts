export interface ClusterHealth {
  cluster_name: string
  status: 'green' | 'yellow' | 'red'
  timed_out: boolean
  number_of_nodes: number
  number_of_data_nodes: number
  active_primary_shards: number
  active_shards: number
  relocating_shards: number
  initializing_shards: number
  unassigned_shards: number
  delayed_unassigned_shards: number
  number_of_pending_tasks: number
  number_of_in_flight_fetch: number
  task_max_waiting_in_queue_millis: number
  active_shards_percent_as_number: number
}

export interface NodeInfo {
  name: string
  host: string
  ip: string
  roles: string[]
  attributes: Record<string, string>
}

export interface DiskUsage {
  total_bytes: number
  used_bytes: number
  available_bytes: number
  used_percent: number
  dynamic_low?: number
  dynamic_high?: number
  dynamic_flood?: number
}

export interface NodeOSStats {
  timestamp: number
  cpu: CPUStats
  io: IOStats
  load_average: number[]
}

export interface CPUStats {
  percent: number
  load_average: number
}

export interface IOStats {
  total_read_bytes: number
  total_write_bytes: number
  read_bytes_per_sec: number
  write_bytes_per_sec: number
  io_wait_percent: number
}

export interface NodeLoadHistory {
  node_name: string
  history: NodeOSStats[]
  avg_load: number
  avg_io_wait: number
  avg_cpu: number
  is_high_load: boolean
  load_score: number
}

export interface SpeedInfo {
  current_speed: string
  min_speed: string
  max_speed: string
  adaptive_enabled: boolean
  last_adjust_time: string
}

export interface ShardInfo {
  index: string
  shard: string
  prirep: string
  state: string
  node: string
  'unassigned.reason'?: string
}

export interface NodeShardInfo {
  node_name: string
  shard_count: number
  indices: string[]
  shards: ShardInfo[]
  disk_usage: DiskUsage
  node_type: 'hot' | 'cold' | 'data'
}

export interface ShardDistribution {
  nodes: Record<string, NodeShardInfo>
  total_shards: number
  avg_shards: number
  max_shards: number
  min_shards: number
  imbalance: number
}

export interface MigrationPlan {
  index: string
  shard: string
  from_node: string
  to_node: string
  reason: string
  estimated_size: number
  created_at: string
  heat_score?: number
  is_hot_shard?: boolean
}

export interface IndexStats {
  index_name: string
  query_count: number
  index_count: number
  query_time_ms: number
  index_time_ms: number
  store_size_bytes: number
  docs_count: number
  timestamp: number
}

export interface IndexHeatInfo {
  index_name: string
  heat_score: number
  avg_queries_per_sec: number
  avg_indexes_per_sec: number
  is_hot: boolean
  history?: IndexStats[]
}

export interface ShardHeatInfo {
  index_name: string
  shard_num: string
  heat_score: number
  is_hot: boolean
  node_name: string
}

export interface SimulationMetrics {
  before_imbalance: number
  after_imbalance: number
  imbalance_improvement_percent: number

  before_max_disk_usage: number
  after_max_disk_usage: number
  disk_usage_improvement_percent: number

  before_hot_shards_on_high_load: number
  after_hot_shards_on_high_load: number
  hot_shard_improvement_percent: number

  nodes_over_high_watermark_before: number
  nodes_over_high_watermark_after: number

  overall_score: number
}

export interface MigrationSimulationResult {
  plans: MigrationPlan[]
  before_distribution: ShardDistribution
  after_distribution: ShardDistribution
  improvement_metrics: SimulationMetrics
  estimated_time_seconds: number
  estimated_total_bytes: number
  warnings: string[]
}

export interface AutoScalingStatus {
  enabled: boolean
  min_nodes: number
  max_nodes: number
  current_nodes: number
  flood_threshold: number
  max_disk_usage: number
  in_cooldown: boolean
  cooldown_remaining: number
  last_scale_time: string
  provider: string
  node_type: string
}

export interface MigrationStatus {
  task_id: string
  index: string
  shard: string
  from_node: string
  to_node: string
  status: string
  progress: number
  bytes_transferred: number
  total_bytes: number
  started_at: string
}

export interface BalanceResult {
  migrations_planned: number
  migrations: MigrationPlan[]
  message: string
}

export interface BalancerConfig {
  enabled: boolean
  schedule: string
  max_migrations_per_cycle: number
  migration_timeout: number
  disk_watermark: {
    low: number
    high: number
    flood: number
    dynamic_enabled: boolean
    base_capacity_gb: number
    max_extra_percent: number
  }
  speed_limit: {
    max_bytes_per_sec: string
    min_bytes_per_sec: string
    adaptive_enabled: boolean
    target_pending_tasks: number
    adjust_interval_sec: number
  }
  hot_cold: {
    enabled: boolean
    hot_node_attr: string
    hot_node_value: string
    cold_node_attr: string
    cold_node_value: string
  }
  load_awareness: {
    enabled: boolean
    history_size: number
    high_load_threshold: number
    io_wait_threshold: number
    cpu_load_threshold: number
    avoid_high_load_nodes: boolean
  }
  shard_heat: {
    enabled: boolean
    history_size: number
    query_weight: number
    index_weight: number
    heat_threshold: number
    priority_boost: number
    collect_interval_sec: number
  }
  auto_scaling: {
    enabled: boolean
    flood_threshold: number
    cooldown_minutes: number
    min_nodes: number
    max_nodes: number
    provider: string
    node_type: string
    disk_size_gb: number
    webhook_url: string
  }
}

export interface Config {
  elasticsearch: {
    url: string
    username: string
    password: string
    timeout: number
  }
  server: {
    port: number
    mode: string
  }
  balancer: BalancerConfig
  logging: {
    level: string
    format: string
  }
}
