package scanner

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

type PortSnapshot struct {
	Target     string       `json:"target"`
	ScanTime   time.Time    `json:"scan_time"`
	OpenPorts  []PortRecord `json:"open_ports"`
	TotalOpen  int          `json:"total_open"`
	Checksum   string       `json:"checksum"`
}

type PortRecord struct {
	Port    int    `json:"port"`
	Service string `json:"service"`
	Version string `json:"version"`
	State   string `json:"state"`
}

type PortChange struct {
	Port        int       `json:"port"`
	Service     string    `json:"service"`
	Version     string    `json:"version"`
	ChangeType  string    `json:"change_type"`
	Previous    *PortRecord `json:"previous,omitempty"`
	Current     *PortRecord `json:"current,omitempty"`
	DetectedAt  time.Time `json:"detected_at"`
	AlertLevel  string    `json:"alert_level"`
}

type HistoryManager struct {
	cacheDir string
	mu       chan struct{}
}

func NewHistoryManager() *HistoryManager {
	home, _ := os.UserHomeDir()
	if home == "" {
		home = "."
	}
	cacheDir := filepath.Join(home, ".portscanner", "history")
	os.MkdirAll(cacheDir, 0755)
	return &HistoryManager{
		cacheDir: cacheDir,
		mu:       make(chan struct{}, 1),
	}
}

func (hm *HistoryManager) SaveSnapshot(target string, ports []PortResult) error {
	hm.mu <- struct{}{}
	defer func() { <-hm.mu }()

	records := make([]PortRecord, 0, len(ports))
	for _, p := range ports {
		records = append(records, PortRecord{
			Port:    p.Port,
			Service: p.Service,
			Version: p.Version,
			State:   p.State,
		})
	}

	snapshot := &PortSnapshot{
		Target:    target,
		ScanTime:  time.Now(),
		OpenPorts: records,
		TotalOpen: len(records),
		Checksum:  calculateSnapshotChecksum(records),
	}

	dir := filepath.Join(hm.cacheDir, sanitizeTarget(target))
	os.MkdirAll(dir, 0755)

	filename := filepath.Join(dir, fmt.Sprintf("snapshot_%s.json", snapshot.ScanTime.Format("20060102_150405")))
	data, err := json.MarshalIndent(snapshot, "", "  ")
	if err != nil {
		return err
	}

	if err := os.WriteFile(filename, data, 0644); err != nil {
		return err
	}

	hm.cleanupOldSnapshots(dir, 90)

	return nil
}

func (hm *HistoryManager) GetLatestSnapshot(target string) (*PortSnapshot, error) {
	dir := filepath.Join(hm.cacheDir, sanitizeTarget(target))
	files, err := os.ReadDir(dir)
	if err != nil {
		return nil, fmt.Errorf("无历史记录")
	}

	if len(files) == 0 {
		return nil, fmt.Errorf("无历史记录")
	}

	sort.Slice(files, func(i, j int) bool {
		return files[i].Name() > files[j].Name()
	})

	latestFile := filepath.Join(dir, files[0].Name())
	return hm.loadSnapshot(latestFile)
}

func (hm *HistoryManager) GetSnapshotBefore(target string, before time.Time) (*PortSnapshot, error) {
	dir := filepath.Join(hm.cacheDir, sanitizeTarget(target))
	files, err := os.ReadDir(dir)
	if err != nil {
		return nil, fmt.Errorf("无历史记录")
	}

	sort.Slice(files, func(i, j int) bool {
		return files[i].Name() > files[j].Name()
	})

	for _, f := range files {
		snapshot, err := hm.loadSnapshot(filepath.Join(dir, f.Name()))
		if err != nil {
			continue
		}
		if snapshot.ScanTime.Before(before) {
			return snapshot, nil
		}
	}

	return nil, fmt.Errorf("未找到更早的快照")
}

func (hm *HistoryManager) CompareWithLatest(target string, currentPorts []PortResult) ([]PortChange, error) {
	latest, err := hm.GetLatestSnapshot(target)
	if err != nil {
		return nil, err
	}

	return hm.CompareSnapshots(latest, currentPorts), nil
}

func (hm *HistoryManager) CompareSnapshots(previous *PortSnapshot, currentPorts []PortResult) []PortChange {
	var changes []PortChange

	prevMap := make(map[int]PortRecord)
	for _, p := range previous.OpenPorts {
		prevMap[p.Port] = p
	}

	curMap := make(map[int]PortRecord)
	for _, p := range currentPorts {
		curMap[p.Port] = PortRecord{
			Port:    p.Port,
			Service: p.Service,
			Version: p.Version,
			State:   p.State,
		}
	}

	for port, cur := range curMap {
		if prev, exists := prevMap[port]; !exists {
			alertLevel := assessNewPortAlert(port, cur.Service)
			changes = append(changes, PortChange{
				Port:       port,
				Service:    cur.Service,
				Version:    cur.Version,
				ChangeType: "new_open",
				Current:    &cur,
				DetectedAt: time.Now(),
				AlertLevel: alertLevel,
			})
		} else {
			if prev.Service != cur.Service || prev.Version != cur.Version {
				changes = append(changes, PortChange{
					Port:       port,
					Service:    cur.Service,
					Version:    cur.Version,
					ChangeType: "changed",
					Previous:   &prev,
					Current:    &cur,
					DetectedAt: time.Now(),
					AlertLevel: "Medium",
				})
			}
		}
	}

	for port, prev := range prevMap {
		if _, exists := curMap[port]; !exists {
			changes = append(changes, PortChange{
				Port:       port,
				Service:    prev.Service,
				Version:    prev.Version,
				ChangeType: "closed",
				Previous:   &prev,
				DetectedAt: time.Now(),
				AlertLevel: "Info",
			})
		}
	}

	sort.Slice(changes, func(i, j int) bool {
		priority := map[string]int{"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
		if priority[changes[i].AlertLevel] != priority[changes[j].AlertLevel] {
			return priority[changes[i].AlertLevel] < priority[changes[j].AlertLevel]
		}
		return changes[i].Port < changes[j].Port
	})

	return changes
}

func assessNewPortAlert(port int, service string) string {
	criticalPorts := map[int]bool{
		23: true, 6379: true, 9200: true, 27017: true,
	}
	highRiskPorts := map[int]bool{
		21: true, 3306: true, 3389: true, 5432: true,
		11211: true, 5984: true, 7001: true, 8161: true,
	}
	mediumRiskPorts := map[int]bool{
		80: true, 8080: true, 443: true, 8443: true,
		9090: true, 8888: true,
	}

	if criticalPorts[port] {
		return "Critical"
	}
	if highRiskPorts[port] {
		return "High"
	}
	if mediumRiskPorts[port] {
		return "Medium"
	}

	risk := AssessRisk(port, service)
	switch risk.RiskLevel {
	case "Critical":
		return "Critical"
	case "High":
		return "High"
	case "Medium":
		return "Medium"
	default:
		return "Low"
	}
}

func (hm *HistoryManager) GetSnapshotHistory(target string, limit int) ([]*PortSnapshot, error) {
	dir := filepath.Join(hm.cacheDir, sanitizeTarget(target))
	files, err := os.ReadDir(dir)
	if err != nil {
		return nil, fmt.Errorf("无历史记录")
	}

	sort.Slice(files, func(i, j int) bool {
		return files[i].Name() > files[j].Name()
	})

	if limit > 0 && len(files) > limit {
		files = files[:limit]
	}

	var snapshots []*PortSnapshot
	for _, f := range files {
		snapshot, err := hm.loadSnapshot(filepath.Join(dir, f.Name()))
		if err != nil {
			continue
		}
		snapshots = append(snapshots, snapshot)
	}

	return snapshots, nil
}

func (hm *HistoryManager) PrintChangeReport(changes []PortChange) {
	if len(changes) == 0 {
		fmt.Println("\n✅ 与上次扫描结果一致，无端口变化")
		return
	}

	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("【端口变化告警】")
	fmt.Println(strings.Repeat("=", 80))

	newOpen := 0
	closed := 0
	changed := 0
	criticalAlerts := 0
	highAlerts := 0

	for _, change := range changes {
		switch change.ChangeType {
		case "new_open":
			newOpen++
		case "closed":
			closed++
		case "changed":
			changed++
		}
		if change.AlertLevel == "Critical" {
			criticalAlerts++
		} else if change.AlertLevel == "High" {
			highAlerts++
		}
	}

	if criticalAlerts > 0 {
		fmt.Printf("\n🚨 %d 个严重告警！\n", criticalAlerts)
	}
	if highAlerts > 0 {
		fmt.Printf("⚠️  %d 个高危告警\n", highAlerts)
	}

	fmt.Printf("\n变化统计: 新开放=%d, 已关闭=%d, 服务变更=%d\n", newOpen, closed, changed)

	for _, change := range changes {
		color := GetRiskColor(change.AlertLevel)
		reset := "\033[0m"

		switch change.ChangeType {
		case "new_open":
			fmt.Printf("\n%s[新增开放]%s 端口 %d (%s) - 告警等级: %s[%s]%s\n",
				color, reset, change.Port, change.Service, color, change.AlertLevel, reset)
			fmt.Printf("   版本: %s\n", change.Version)
			if change.AlertLevel == "Critical" || change.AlertLevel == "High" {
				fmt.Println("   ⚠️  建议立即检查该端口是否为授权开放！")
				risk := AssessRisk(change.Port, change.Service)
				for i, rec := range risk.Recommendations {
					fmt.Printf("   %d. %s\n", i+1, rec)
				}
			}
		case "closed":
			fmt.Printf("\n[已关闭] 端口 %d (%s)\n", change.Port, change.Service)
		case "changed":
			fmt.Printf("\n%s[服务变更]%s 端口 %d\n", color, reset, change.Port)
			if change.Previous != nil {
				fmt.Printf("   变更前: %s %s\n", change.Previous.Service, change.Previous.Version)
			}
			if change.Current != nil {
				fmt.Printf("   变更后: %s %s\n", change.Current.Service, change.Current.Version)
			}
		}
	}

	fmt.Println("\n" + strings.Repeat("=", 80))
}

func (hm *HistoryManager) loadSnapshot(filename string) (*PortSnapshot, error) {
	data, err := os.ReadFile(filename)
	if err != nil {
		return nil, err
	}

	var snapshot PortSnapshot
	if err := json.Unmarshal(data, &snapshot); err != nil {
		return nil, err
	}

	return &snapshot, nil
}

func (hm *HistoryManager) cleanupOldSnapshots(dir string, maxDays int) {
	files, err := os.ReadDir(dir)
	if err != nil {
		return
	}

	cutoff := time.Now().AddDate(0, 0, -maxDays)
	for _, f := range files {
		if f.IsDir() {
			continue
		}
		info, err := f.Info()
		if err != nil {
			continue
		}
		if info.ModTime().Before(cutoff) {
			os.Remove(filepath.Join(dir, f.Name()))
		}
	}
}

func (hm *HistoryManager) ExportHistory(target, filename string) error {
	snapshots, err := hm.GetSnapshotHistory(target, 0)
	if err != nil {
		return err
	}

	data, err := json.MarshalIndent(snapshots, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(filename, data, 0644)
}

func (hm *HistoryManager) GetChangeStats(target string) (map[string]int, error) {
	stats := map[string]int{
		"total_snapshots": 0,
		"total_new_open":  0,
		"total_closed":    0,
		"total_changed":   0,
	}

	snapshots, err := hm.GetSnapshotHistory(target, 0)
	if err != nil {
		return stats, nil
	}

	stats["total_snapshots"] = len(snapshots)

	for i := 0; i < len(snapshots)-1; i++ {
		older := snapshots[len(snapshots)-1-i]
		newer := snapshots[len(snapshots)-2-i]

		var currentPorts []PortResult
		for _, p := range newer.OpenPorts {
			currentPorts = append(currentPorts, PortResult{
				Port: p.Port, Service: p.Service, Version: p.Version, State: p.State,
			})
		}

		changes := hm.CompareSnapshots(older, currentPorts)
		for _, c := range changes {
			switch c.ChangeType {
			case "new_open":
				stats["total_new_open"]++
			case "closed":
				stats["total_closed"]++
			case "changed":
				stats["total_changed"]++
			}
		}
	}

	return stats, nil
}

func calculateSnapshotChecksum(records []PortRecord) string {
	var portStrs []string
	for _, r := range records {
		portStrs = append(portStrs, fmt.Sprintf("%d:%s:%s", r.Port, r.Service, r.Version))
	}
	sort.Strings(portStrs)
	combined := strings.Join(portStrs, "|")
	return fmt.Sprintf("%x", len(combined))
}

func sanitizeTarget(target string) string {
	sanitized := strings.ReplaceAll(target, ":", "_")
	sanitized = strings.ReplaceAll(sanitized, "/", "_")
	sanitized = strings.ReplaceAll(sanitized, "\\", "_")
	sanitized = strings.ReplaceAll(sanitized, ".", "_")
	return sanitized
}
