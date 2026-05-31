package simulator

import "time"

type SimulationConfig struct {
	DaysToSimulate   int     `json:"days_to_simulate"`
	DailyGrowthRate  float64 `json:"daily_growth_rate"`
	CompressionRatio float64 `json:"compression_ratio"`
	TZ               string  `json:"tz"`
}

type PartitionProjection struct {
	Partition     string    `json:"partition"`
	CurrentSize   uint64    `json:"current_size"`
	ProjectedSize uint64    `json:"projected_size"`
	AgeDays       int       `json:"age_days"`
	Action        string    `json:"action"`
	TargetDisk    string    `json:"target_disk"`
	Dropped       bool      `json:"dropped"`
	Timestamp     time.Time `json:"timestamp"`
}

type StorageProjection struct {
	DiskName      string      `json:"disk_name"`
	CurrentUsed   uint64      `json:"current_used"`
	ProjectedUsed []uint64    `json:"projected_used"`
	ProjectedFree []uint64    `json:"projected_free"`
	Timestamps    []time.Time `json:"timestamps"`
}

type DailyStat struct {
	Date              time.Time `json:"date"`
	HotSize           uint64    `json:"hot_size"`
	ColdSize          uint64    `json:"cold_size"`
	ArchivedSize      uint64    `json:"archived_size"`
	DroppedSize       uint64    `json:"dropped_size"`
	NewPartitions     int       `json:"new_partitions"`
	DroppedPartitions int       `json:"dropped_partitions"`
}

type SimulationResult struct {
	Config           SimulationConfig     `json:"config"`
	StartDate        time.Time            `json:"start_date"`
	EndDate          time.Time            `json:"end_date"`
	Partitions       []PartitionProjection `json:"partitions"`
	Storage          []StorageProjection   `json:"storage"`
	TotalDroppedSize uint64               `json:"total_dropped_size"`
	TotalArchivedSize uint64              `json:"total_archived_size"`
	TotalMovedSize   uint64               `json:"total_moved_size"`
	DailyStats       []DailyStat          `json:"daily_stats"`
}

type SavingsMetric struct {
	DroppedSavingsBytes    uint64  `json:"dropped_savings_bytes"`
	ArchivedSavingsBytes   uint64  `json:"archived_savings_bytes"`
	ColdTierSavingsBytes   uint64  `json:"cold_tier_savings_bytes"`
	TotalSavingsBytes      uint64  `json:"total_savings_bytes"`
	DroppedSavingsPercent  float64 `json:"dropped_savings_percent"`
	ArchivedSavingsPercent float64 `json:"archived_savings_percent"`
	ColdTierSavingsPercent float64 `json:"cold_tier_savings_percent"`
	TotalSavingsPercent    float64 `json:"total_savings_percent"`
	ProjectedHotUsage      uint64  `json:"projected_hot_usage"`
	ProjectedTotalUsage    uint64  `json:"projected_total_usage"`
}

type ChartData struct {
	StorageTimeline  []StorageTimelinePoint  `json:"storage_timeline"`
	ActionBreakdown  []ActionBreakdownPoint  `json:"action_breakdown"`
	DailyGrowth      []DailyGrowthPoint      `json:"daily_growth"`
	TierDistribution []TierDistributionPoint `json:"tier_distribution"`
}

type StorageTimelinePoint struct {
	Date     time.Time `json:"date"`
	Hot      uint64    `json:"hot"`
	Cold     uint64    `json:"cold"`
	Archived uint64    `json:"archived"`
	Dropped  uint64    `json:"dropped"`
}

type ActionBreakdownPoint struct {
	Action string `json:"action"`
	Count  int    `json:"count"`
	Size   uint64 `json:"size"`
}

type DailyGrowthPoint struct {
	Date    time.Time `json:"date"`
	Added   uint64    `json:"added"`
	Removed uint64    `json:"removed"`
	Net     int64     `json:"net"`
}

type TierDistributionPoint struct {
	Tier  string `json:"tier"`
	Size  uint64 `json:"size"`
	Count int    `json:"count"`
}
