package cost

import (
	"fmt"
	"sort"
	"time"

	"etcd-backup-manager/internal/backup"
	"etcd-backup-manager/pkg/models"
)

const (
	GB = 1024 * 1024 * 1024

	S3StandardPricePerGBMonth   = 0.023
	S3IAPricePerGBMonth         = 0.0125
	S3GlacierPricePerGBMonth    = 0.004
	LocalStoragePricePerGBMonth = 0.01
	NetworkPricePerGB           = 0.09
	ComputePricePerHour         = 0.05

	DefaultRTOFullPerGB    = 120
	DefaultRTOIncrPerGB    = 30
	DefaultRPOFullHour     = 24
	DefaultRPOIncrMinute   = 5
)

type Analyzer struct {
	backupMgr  *backup.Manager
	priceTable PriceTable
}

type PriceTable struct {
	StoragePerGBMonth map[string]float64
	NetworkPerGB      float64
	ComputePerHour    float64
}

func DefaultPriceTable() PriceTable {
	return PriceTable{
		StoragePerGBMonth: map[string]float64{
			"local":  LocalStoragePricePerGBMonth,
			"s3":     S3StandardPricePerGBMonth,
			"s3-ia":  S3IAPricePerGBMonth,
			"glacier": S3GlacierPricePerGBMonth,
		},
		NetworkPerGB:   NetworkPricePerGB,
		ComputePerHour: ComputePricePerHour,
	}
}

func NewAnalyzer(backupMgr *backup.Manager) *Analyzer {
	return &Analyzer{
		backupMgr:  backupMgr,
		priceTable: DefaultPriceTable(),
	}
}

func (a *Analyzer) AnalyzeCluster(clusterID string, period string) (*models.CostAnalysis, error) {
	backups := a.backupMgr.ListBackups(clusterID)

	now := time.Now()
	var cutoff time.Time
	switch period {
	case "7d":
		cutoff = now.AddDate(0, 0, -7)
	case "30d":
		cutoff = now.AddDate(0, 0, -30)
	case "90d":
		cutoff = now.AddDate(0, 0, -90)
	case "1y":
		cutoff = now.AddDate(-1, 0, 0)
	default:
		cutoff = now.AddDate(0, 0, -30)
	}

	analysis := &models.CostAnalysis{
		ClusterID: clusterID,
		Period:    period,
	}

	var fullBackups, incrBackups []*models.Backup
	var fullSize, incrSize int64

	for _, b := range backups {
		if b.CreatedAt.Before(cutoff) {
			continue
		}

		analysis.TotalBackups++
		analysis.TotalSizeBytes += b.Size

		if b.Type == "full" {
			analysis.FullCount++
			analysis.FullSizeBytes += b.Size
			fullBackups = append(fullBackups, b)
			fullSize += b.Size
		} else if b.Type == "incremental" {
			analysis.IncrementalCount++
			analysis.IncrementalSizeBytes += b.Size
			incrBackups = append(incrBackups, b)
			incrSize += b.Size
		}
	}

	storageType := "s3"
	storagePrice, ok := a.priceTable.StoragePerGBMonth[storageType]
	if !ok {
		storagePrice = S3StandardPricePerGBMonth
	}

	totalGB := float64(analysis.TotalSizeBytes) / float64(GB)
	analysis.StorageCost = totalGB * storagePrice

	replicaCount := 0
	for _, b := range backups {
		if b.Replicated && len(b.ReplicaSites) > 0 {
			replicaCount++
		}
	}
	replicaGB := float64(0)
	for _, b := range backups {
		if b.Replicated {
			replicaGB += float64(b.Size) / float64(GB)
		}
	}
	analysis.NetworkCost = replicaGB * a.priceTable.NetworkPerGB

	estimatedHours := float64(analysis.TotalBackups) * 0.1
	analysis.ComputeCost = estimatedHours * a.priceTable.ComputePerHour

	analysis.TotalCost = analysis.StorageCost + analysis.NetworkCost + analysis.ComputeCost

	if analysis.FullCount > 0 {
		fullGB := float64(analysis.FullSizeBytes) / float64(GB)
		analysis.EstimatedRTO = int64(fullGB * float64(DefaultRTOFullPerGB))
	}
	if analysis.IncrementalCount > 0 {
		analysis.EstimatedRTO += int64(float64(analysis.IncrementalCount) * 0.5)
	}

	if analysis.IncrementalCount > 0 {
		analysis.EstimatedRPO = int64(DefaultRPOIncrMinute)
	} else {
		analysis.EstimatedRPO = int64(DefaultRPOFullHour) * 60
	}

	allFullSize := float64(fullSize) / float64(GB)
	if analysis.IncrementalCount > 0 && allFullSize > 0 {
		incrRatio := float64(incrSize) / float64(fullSize)
		analysis.SavingsPercent = (1.0 - incrRatio/(1.0+incrRatio)) * 100
	}

	analysis.Recommendations = a.generateRecommendations(analysis, fullBackups, incrBackups)
	analysis.StorageTrend = a.generateTrend(backups, cutoff, storagePrice)

	return analysis, nil
}

func (a *Analyzer) generateRecommendations(analysis *models.CostAnalysis, fullBackups, incrBackups []*models.Backup) []models.CostRecommendation {
	var recs []models.CostRecommendation

	if analysis.FullCount > 0 && analysis.IncrementalCount == 0 {
		recs = append(recs, models.CostRecommendation{
			Type:       "backup_strategy",
			Current:    "仅全量备份",
			Suggested:  "启用WAL增量备份",
			SavingsPct: 60,
			Reason:     "增量备份可减少60-80%的存储空间，同时缩短RPO到分钟级",
			Priority:   "high",
		})
	}

	if analysis.FullCount > 7 {
		oldFullCount := analysis.FullCount - 7
		if oldFullCount > 0 {
			avgFullSize := float64(0)
			if analysis.FullCount > 0 {
				avgFullSize = float64(analysis.FullSizeBytes) / float64(analysis.FullCount) / float64(GB)
			}
			savings := avgFullSize * float64(oldFullCount) * S3IAPricePerGBMonth
			recs = append(recs, models.CostRecommendation{
				Type:       "storage_tier",
				Current:    fmt.Sprintf("%d个全量备份存储在标准层", analysis.FullCount),
				Suggested:  fmt.Sprintf("将%d个旧备份迁移到低频访问层", oldFullCount),
				SavingsPct: 45,
				Reason:     fmt.Sprintf("旧备份迁移到S3-IA可节省约$%.2f/月", savings),
				Priority:   "medium",
			})
		}
	}

	if analysis.FullCount > 30 {
		veryOldCount := analysis.FullCount - 30
		if veryOldCount > 0 {
			avgFullSize := float64(0)
			if analysis.FullCount > 0 {
				avgFullSize = float64(analysis.FullSizeBytes) / float64(analysis.FullCount) / float64(GB)
			}
			savings := avgFullSize * float64(veryOldCount) * S3StandardPricePerGBMonth
			recs = append(recs, models.CostRecommendation{
				Type:       "retention",
				Current:    fmt.Sprintf("保留%d个全量备份", analysis.FullCount),
				Suggested:  fmt.Sprintf("保留最近30个，归档%d个到Glacier", veryOldCount),
				SavingsPct: 82,
				Reason:     fmt.Sprintf("归档旧备份到Glacier可节省约$%.2f/月", savings),
				Priority:   "low",
			})
		}
	}

	if analysis.EstimatedRTO > 300 {
		recs = append(recs, models.CostRecommendation{
			Type:       "rto_optimization",
			Current:    fmt.Sprintf("RTO约%d秒", analysis.EstimatedRTO),
			Suggested:  "增加增量备份频率，减少全量恢复时间",
			SavingsPct: 0,
			Reason:     "更频繁的增量备份可将RTO从小时级降至分钟级，代价是略增存储成本",
			Priority:   "high",
		})
	}

	if len(fullBackups) > 0 {
		avgFullSize := int64(0)
		for _, b := range fullBackups {
			avgFullSize += b.Size
		}
		avgFullSize /= int64(len(fullBackups))

		if avgFullSize > 500*1024*1024 {
			recs = append(recs, models.CostRecommendation{
				Type:       "compression",
				Current:    "未启用压缩",
				Suggested:  "启用gzip压缩传输和存储",
				SavingsPct: 40,
				Reason:     "ETCD数据通常压缩率可达40-60%，显著降低存储和网络成本",
				Priority:   "medium",
			})
		}
	}

	if analysis.NetworkCost > analysis.StorageCost*0.5 {
		recs = append(recs, models.CostRecommendation{
			Type:       "replication",
			Current:    "跨区域复制带宽成本较高",
			Suggested:  "使用压缩+增量复制降低网络成本",
			SavingsPct: 50,
			Reason:     fmt.Sprintf("当前网络成本$%.2f/月，优化后可降至$%.2f/月", analysis.NetworkCost, analysis.NetworkCost*0.5),
			Priority:   "medium",
		})
	}

	return recs
}

func (a *Analyzer) generateTrend(backups []*models.Backup, cutoff time.Time, storagePrice float64) []models.StorageTrendPoint {
	dailyData := make(map[string]struct {
		fullSize int64
		incrSize int64
	})

	for _, b := range backups {
		if b.CreatedAt.Before(cutoff) {
			continue
		}

		dateKey := b.CreatedAt.Format("2006-01-02")
		data := dailyData[dateKey]
		if b.Type == "full" {
			data.fullSize += b.Size
		} else {
			data.incrSize += b.Size
		}
		dailyData[dateKey] = data
	}

	var trend []models.StorageTrendPoint
	var cumulativeSize int64

	dates := make([]string, 0, len(dailyData))
	for d := range dailyData {
		dates = append(dates, d)
	}
	sort.Strings(dates)

	for _, date := range dates {
		data := dailyData[date]
		cumulativeSize += data.fullSize + data.incrSize
		costGB := float64(cumulativeSize) / float64(GB) * storagePrice

		trend = append(trend, models.StorageTrendPoint{
			Date:      date,
			FullSize:  data.fullSize,
			IncrSize:  data.incrSize,
			TotalSize: cumulativeSize,
			Cost:      costGB,
		})
	}

	return trend
}

func (a *Analyzer) EstimateRestoreTime(backupID string) (int64, string, error) {
	backup, err := a.backupMgr.GetBackup(backupID)
	if err != nil {
		return 0, "", err
	}

	backupGB := float64(backup.Size) / float64(GB)

	var estimatedSeconds int64
	var strategy string

	if backup.Type == "full" {
		estimatedSeconds = int64(backupGB * float64(DefaultRTOFullPerGB))
		strategy = "全量恢复"
	} else {
		estimatedSeconds = int64(backupGB * float64(DefaultRTOIncrPerGB))
		chain := a.backupMgr.ListBackups(backup.ClusterID)
		fullCount := 0
		for _, b := range chain {
			if b.Type == "full" && b.Status == "completed" {
				fullCount++
			}
		}
		estimatedSeconds += int64(fullCount) * 10
		strategy = "增量链恢复(需先恢复基础全量备份)"
	}

	return estimatedSeconds, strategy, nil
}
