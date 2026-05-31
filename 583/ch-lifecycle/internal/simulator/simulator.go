package simulator

import (
	"context"
	"fmt"
	"sort"
	"time"

	ch "ch-lifecycle/internal/clickhouse"
	"ch-lifecycle/internal/policy"
	"go.uber.org/zap"
)

type Simulator struct {
	client *ch.Client
	store  *policy.Store
	logger *zap.Logger
}

func NewSimulator(client *ch.Client, store *policy.Store, logger *zap.Logger) *Simulator {
	return &Simulator{
		client: client,
		store:  store,
		logger: logger,
	}
}

func (s *Simulator) Simulate(ctx context.Context, database, table string, config SimulationConfig) (*SimulationResult, error) {
	loc, err := time.LoadLocation(config.TZ)
	if err != nil {
		loc = time.UTC
		s.logger.Warn("failed to load timezone, using UTC", zap.Error(err))
	}

	startDate := time.Now().In(loc)
	startDate = time.Date(startDate.Year(), startDate.Month(), startDate.Day(), 0, 0, 0, 0, loc)
	endDate := startDate.AddDate(0, 0, config.DaysToSimulate)

	partitions, err := s.client.GetPartitions(ctx, database, table)
	if err != nil {
		return nil, fmt.Errorf("get partitions: %w", err)
	}

	disks, err := s.client.GetDisks(ctx)
	if err != nil {
		return nil, fmt.Errorf("get disks: %w", err)
	}

	policies, err := s.store.GetByTable(database, table)
	if err != nil {
		return nil, fmt.Errorf("get policies: %w", err)
	}

	var rules []policy.TTLRule
	for _, p := range policies {
		rules = append(rules, p.Rules...)
	}
	sort.Slice(rules, func(i, j int) bool {
		return rules[i].Priority < rules[j].Priority
	})

	projections := make([]PartitionProjection, 0, len(partitions))
	for _, part := range partitions {
		ageDays := calculateAge(part.MaxDate, loc)
		proj := PartitionProjection{
			Partition:     part.Partition,
			CurrentSize:   part.BytesOnDisk,
			ProjectedSize: part.BytesOnDisk,
			AgeDays:       ageDays,
			Dropped:       false,
			Timestamp:     startDate,
		}
		projections = append(projections, proj)
	}

	storageProjections := make([]StorageProjection, 0, len(disks))
	for _, disk := range disks {
		used := disk.TotalSpace - disk.FreeSpace
		sp := StorageProjection{
			DiskName:      disk.Name,
			CurrentUsed:   used,
			ProjectedUsed: []uint64{used},
			ProjectedFree: []uint64{disk.FreeSpace},
			Timestamps:    []time.Time{startDate},
		}
		storageProjections = append(storageProjections, sp)
	}

	dailyStats := make([]DailyStat, 0, config.DaysToSimulate)
	var totalDropped, totalArchived, totalMoved uint64

	currentDate := startDate
	for day := 0; day < config.DaysToSimulate; day++ {
		nextDate := currentDate.AddDate(0, 0, 1)
		stat := DailyStat{
			Date: currentDate,
		}

		projections, stat, totalDropped, totalArchived, totalMoved = s.SimulateDailyStep(
			projections,
			storageProjections,
			rules,
			currentDate,
			nextDate,
			config,
			stat,
			totalDropped,
			totalArchived,
			totalMoved,
			loc,
		)

		for i := range storageProjections {
			lastUsed := storageProjections[i].ProjectedUsed[len(storageProjections[i].ProjectedUsed)-1]
			lastFree := storageProjections[i].ProjectedFree[len(storageProjections[i].ProjectedFree)-1]
			storageProjections[i].ProjectedUsed = append(storageProjections[i].ProjectedUsed, lastUsed)
			storageProjections[i].ProjectedFree = append(storageProjections[i].ProjectedFree, lastFree)
			storageProjections[i].Timestamps = append(storageProjections[i].Timestamps, nextDate)
		}

		dailyStats = append(dailyStats, stat)
		currentDate = nextDate
	}

	for _, stat := range dailyStats {
		totalHot := stat.HotSize
		if totalHot > 0 {
			dailyStats[len(dailyStats)-1].HotSize = totalHot
			break
		}
	}

	result := &SimulationResult{
		Config:            config,
		StartDate:         startDate,
		EndDate:           endDate,
		Partitions:        projections,
		Storage:           storageProjections,
		TotalDroppedSize:  totalDropped,
		TotalArchivedSize: totalArchived,
		TotalMovedSize:    totalMoved,
		DailyStats:        dailyStats,
	}

	s.calculateFinalStats(result, loc)

	return result, nil
}

func (s *Simulator) ProjectPartitionGrowth(currentSize uint64, days int, growthRate float64) uint64 {
	if days <= 0 {
		return currentSize
	}
	growthMultiplier := 1.0 + growthRate/100.0
	projected := float64(currentSize)
	for i := 0; i < days; i++ {
		projected *= growthMultiplier
	}
	return uint64(projected)
}

func (s *Simulator) ApplyTtlRules(proj *PartitionProjection, rules []policy.TTLRule, currentDate time.Time) {
	if proj.Dropped {
		return
	}

	for _, rule := range rules {
		if proj.AgeDays >= rule.AgeDays {
			proj.Action = string(rule.Action)
			proj.TargetDisk = rule.TargetDisk
			proj.Timestamp = currentDate
			return
		}
	}
	proj.Action = ""
	proj.TargetDisk = ""
}

func (s *Simulator) SimulateDailyStep(
	projections []PartitionProjection,
	storageProjs []StorageProjection,
	rules []policy.TTLRule,
	currentDate, nextDate time.Time,
	config SimulationConfig,
	stat DailyStat,
	totalDropped, totalArchived, totalMoved uint64,
	loc *time.Location,
) ([]PartitionProjection, DailyStat, uint64, uint64, uint64) {
	hotDisk := getHotDisk(storageProjs)
	coldDisks := getColdDisks(storageProjs)

	var dailyDropped, dailyArchived, dailyMoved uint64
	var droppedParts int

	for i := range projections {
		if projections[i].Dropped {
			continue
		}

		projections[i].AgeDays++
		projections[i].ProjectedSize = s.ProjectPartitionGrowth(
			projections[i].CurrentSize,
			projections[i].AgeDays,
			config.DailyGrowthRate,
		)

		s.ApplyTtlRules(&projections[i], rules, currentDate)

		switch policy.ActionType(projections[i].Action) {
		case policy.ActionDrop:
			if !projections[i].Dropped {
				projections[i].Dropped = true
				projections[i].Timestamp = currentDate
				dailyDropped += projections[i].ProjectedSize
				totalDropped += projections[i].ProjectedSize
				droppedParts++

				removeFromStorage(storageProjs, hotDisk, projections[i].ProjectedSize)
			}
		case policy.ActionMoveToDisk:
			if projections[i].TargetDisk != "" {
				dailyMoved += projections[i].ProjectedSize
				totalMoved += projections[i].ProjectedSize
				moveBetweenStorage(storageProjs, hotDisk, projections[i].TargetDisk, projections[i].ProjectedSize)
			}
		case policy.ActionFreeze:
			dailyArchived += projections[i].ProjectedSize
			totalArchived += projections[i].ProjectedSize
		}
	}

	avgPartitionSize := calculateAvgPartitionSize(projections)
	newPartitions := calculateNewPartitions(config.DailyGrowthRate, avgPartitionSize, projections)
	if newPartitions > 0 {
		newSize := uint64(newPartitions) * avgPartitionSize
		addToStorage(storageProjs, hotDisk, newSize)
		stat.NewPartitions = newPartitions

		for i := 0; i < newPartitions; i++ {
			newPartName := generatePartitionName(nextDate, i, loc)
			newProj := PartitionProjection{
				Partition:     newPartName,
				CurrentSize:   avgPartitionSize,
				ProjectedSize: avgPartitionSize,
				AgeDays:       0,
				Dropped:       false,
				Timestamp:     nextDate,
			}
			projections = append(projections, newProj)
		}
	}

	stat.HotSize = getStorageUsed(storageProjs, hotDisk)
	stat.ColdSize = getTotalStorageUsed(storageProjs, coldDisks)
	stat.ArchivedSize = totalArchived
	stat.DroppedSize = totalDropped
	stat.DroppedPartitions = droppedParts

	return projections, stat, totalDropped, totalArchived, totalMoved
}

func (s *Simulator) CalculateSavings(result *SimulationResult) *SavingsMetric {
	if result == nil || len(result.DailyStats) == 0 {
		return &SavingsMetric{}
	}

	var baselineTotal uint64
	for _, proj := range result.Partitions {
		baselineTotal += proj.ProjectedSize
	}

	lastStat := result.DailyStats[len(result.DailyStats)-1]
	projectedHot := lastStat.HotSize
	projectedTotal := lastStat.HotSize + lastStat.ColdSize + lastStat.ArchivedSize

	droppedSavings := result.TotalDroppedSize
	archivedSavings := result.TotalArchivedSize
	coldSavings := result.TotalMovedSize
	totalSavings := droppedSavings + archivedSavings + coldSavings

	var droppedPercent, archivedPercent, coldPercent, totalPercent float64
	if baselineTotal > 0 {
		droppedPercent = float64(droppedSavings) / float64(baselineTotal) * 100
		archivedPercent = float64(archivedSavings) / float64(baselineTotal) * 100
		coldPercent = float64(coldSavings) / float64(baselineTotal) * 100
		totalPercent = float64(totalSavings) / float64(baselineTotal) * 100
	}

	return &SavingsMetric{
		DroppedSavingsBytes:    droppedSavings,
		ArchivedSavingsBytes:   archivedSavings,
		ColdTierSavingsBytes:   coldSavings,
		TotalSavingsBytes:      totalSavings,
		DroppedSavingsPercent:  droppedPercent,
		ArchivedSavingsPercent: archivedPercent,
		ColdTierSavingsPercent: coldPercent,
		TotalSavingsPercent:    totalPercent,
		ProjectedHotUsage:      projectedHot,
		ProjectedTotalUsage:    projectedTotal,
	}
}

func (s *Simulator) GenerateChartsData(result *SimulationResult) *ChartData {
	if result == nil {
		return &ChartData{}
	}

	timeline := make([]StorageTimelinePoint, 0, len(result.DailyStats))
	for _, stat := range result.DailyStats {
		timeline = append(timeline, StorageTimelinePoint{
			Date:     stat.Date,
			Hot:      stat.HotSize,
			Cold:     stat.ColdSize,
			Archived: stat.ArchivedSize,
			Dropped:  stat.DroppedSize,
		})
	}

	actionCounts := make(map[string]int)
	actionSizes := make(map[string]uint64)
	for _, proj := range result.Partitions {
		if proj.Action != "" {
			actionCounts[proj.Action]++
			actionSizes[proj.Action] += proj.ProjectedSize
		}
	}
	actionBreakdown := make([]ActionBreakdownPoint, 0, len(actionCounts))
	for action, count := range actionCounts {
		actionBreakdown = append(actionBreakdown, ActionBreakdownPoint{
			Action: action,
			Count:  count,
			Size:   actionSizes[action],
		})
	}
	sort.Slice(actionBreakdown, func(i, j int) bool {
		return actionBreakdown[i].Size > actionBreakdown[j].Size
	})

	dailyGrowth := make([]DailyGrowthPoint, 0, len(result.DailyStats))
	var prevTotal uint64
	for i, stat := range result.DailyStats {
		total := stat.HotSize + stat.ColdSize + stat.ArchivedSize
		var added, removed uint64
		if i == 0 {
			added = total
		} else if total > prevTotal {
			added = total - prevTotal
		} else {
			removed = prevTotal - total
		}
		net := int64(total) - int64(prevTotal)
		dailyGrowth = append(dailyGrowth, DailyGrowthPoint{
			Date:    stat.Date,
			Added:   added,
			Removed: removed,
			Net:     net,
		})
		prevTotal = total
	}

	tierCounts := make(map[string]int)
	tierSizes := make(map[string]uint64)
	for _, proj := range result.Partitions {
		if proj.Dropped {
			tierCounts["dropped"]++
			tierSizes["dropped"] += proj.ProjectedSize
		} else if proj.Action == string(policy.ActionFreeze) {
			tierCounts["archived"]++
			tierSizes["archived"] += proj.ProjectedSize
		} else if proj.TargetDisk != "" {
			tierCounts[proj.TargetDisk]++
			tierSizes[proj.TargetDisk] += proj.ProjectedSize
		} else {
			tierCounts["hot"]++
			tierSizes["hot"] += proj.ProjectedSize
		}
	}
	tierDistribution := make([]TierDistributionPoint, 0, len(tierCounts))
	for tier, count := range tierCounts {
		tierDistribution = append(tierDistribution, TierDistributionPoint{
			Tier:  tier,
			Size:  tierSizes[tier],
			Count: count,
		})
	}
	sort.Slice(tierDistribution, func(i, j int) bool {
		return tierDistribution[i].Size > tierDistribution[j].Size
	})

	return &ChartData{
		StorageTimeline:  timeline,
		ActionBreakdown:  actionBreakdown,
		DailyGrowth:      dailyGrowth,
		TierDistribution: tierDistribution,
	}
}

func (s *Simulator) calculateFinalStats(result *SimulationResult, loc *time.Location) {
	if len(result.DailyStats) == 0 {
		return
	}

	var finalHot, finalCold, finalArchived, finalDropped uint64
	for _, proj := range result.Partitions {
		size := proj.ProjectedSize
		if proj.Dropped {
			finalDropped += size
		} else if proj.Action == string(policy.ActionFreeze) {
			finalArchived += size
		} else if proj.TargetDisk != "" {
			finalCold += size
		} else {
			finalHot += size
		}
	}

	lastIdx := len(result.DailyStats) - 1
	result.DailyStats[lastIdx].HotSize = finalHot
	result.DailyStats[lastIdx].ColdSize = finalCold
	result.DailyStats[lastIdx].ArchivedSize = finalArchived
	result.DailyStats[lastIdx].DroppedSize = finalDropped
}

func calculateAge(dateStr string, loc *time.Location) int {
	if dateStr == "" || dateStr == "0000-00-00" {
		return 0
	}
	t, err := time.ParseInLocation("2006-01-02", dateStr, loc)
	if err != nil {
		return 0
	}
	tUTC := time.Date(t.Year(), t.Month(), t.Day(), 0, 0, 0, 0, time.UTC)
	nowUTC := time.Now().UTC()
	days := int(nowUTC.Sub(tUTC).Hours() / 24)
	if days < 0 {
		return 0
	}
	return days
}

func getHotDisk(storageProjs []StorageProjection) string {
	if len(storageProjs) == 0 {
		return "default"
	}
	return storageProjs[0].DiskName
}

func getColdDisks(storageProjs []StorageProjection) []string {
	if len(storageProjs) <= 1 {
		return nil
	}
	disks := make([]string, 0, len(storageProjs)-1)
	for i := 1; i < len(storageProjs); i++ {
		disks = append(disks, storageProjs[i].DiskName)
	}
	return disks
}

func getStorageUsed(storageProjs []StorageProjection, diskName string) uint64 {
	for _, sp := range storageProjs {
		if sp.DiskName == diskName && len(sp.ProjectedUsed) > 0 {
			return sp.ProjectedUsed[len(sp.ProjectedUsed)-1]
		}
	}
	return 0
}

func getTotalStorageUsed(storageProjs []StorageProjection, diskNames []string) uint64 {
	var total uint64
	for _, name := range diskNames {
		total += getStorageUsed(storageProjs, name)
	}
	return total
}

func addToStorage(storageProjs []StorageProjection, diskName string, size uint64) {
	for i := range storageProjs {
		if storageProjs[i].DiskName == diskName && len(storageProjs[i].ProjectedUsed) > 0 {
			lastIdx := len(storageProjs[i].ProjectedUsed) - 1
			storageProjs[i].ProjectedUsed[lastIdx] += size
			if storageProjs[i].ProjectedFree[lastIdx] >= size {
				storageProjs[i].ProjectedFree[lastIdx] -= size
			} else {
				storageProjs[i].ProjectedFree[lastIdx] = 0
			}
			return
		}
	}
}

func removeFromStorage(storageProjs []StorageProjection, diskName string, size uint64) {
	for i := range storageProjs {
		if storageProjs[i].DiskName == diskName && len(storageProjs[i].ProjectedUsed) > 0 {
			lastIdx := len(storageProjs[i].ProjectedUsed) - 1
			if storageProjs[i].ProjectedUsed[lastIdx] >= size {
				storageProjs[i].ProjectedUsed[lastIdx] -= size
			} else {
				storageProjs[i].ProjectedUsed[lastIdx] = 0
			}
			storageProjs[i].ProjectedFree[lastIdx] += size
			return
		}
	}
}

func moveBetweenStorage(storageProjs []StorageProjection, fromDisk, toDisk string, size uint64) {
	removeFromStorage(storageProjs, fromDisk, size)
	addToStorage(storageProjs, toDisk, size)
}

func calculateAvgPartitionSize(projections []PartitionProjection) uint64 {
	if len(projections) == 0 {
		return 1024 * 1024 * 100
	}
	var total uint64
	var count int
	for _, p := range projections {
		if !p.Dropped {
			total += p.CurrentSize
			count++
		}
	}
	if count == 0 {
		return 1024 * 1024 * 100
	}
	return total / uint64(count)
}

func calculateNewPartitions(growthRate float64, avgSize uint64, projections []PartitionProjection) int {
	if growthRate <= 0 {
		return 0
	}
	var totalCurrent uint64
	var count int
	for _, p := range projections {
		if !p.Dropped {
			totalCurrent += p.CurrentSize
			count++
		}
	}
	if count == 0 || avgSize == 0 {
		return 1
	}
	dailyGrowthBytes := float64(totalCurrent) * (growthRate / 100.0)
	newParts := int(dailyGrowthBytes / float64(avgSize))
	if newParts < 1 {
		return 1
	}
	return newParts
}

func generatePartitionName(date time.Time, index int, loc *time.Location) string {
	return fmt.Sprintf("%s_%d", date.In(loc).Format("20060102"), index)
}
