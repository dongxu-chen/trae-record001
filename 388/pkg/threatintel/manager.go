package threatintel

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/sirupsen/logrus"

	"container-security-monitor/pkg/config"
)

type ThreatType string

const (
	ThreatTypeC2        ThreatType = "c2"
	ThreatTypeBotnet    ThreatType = "botnet"
	ThreatTypeMalware   ThreatType = "malware"
	ThreatTypePhishing  ThreatType = "phishing"
	ThreatTypeScanner   ThreatType = "scanner"
	ThreatTypeTor       ThreatType = "tor"
	ThreatTypeProxy     ThreatType = "proxy"
	ThreatTypeMalicious ThreatType = "malicious"
)

type ThreatEntry struct {
	Indicator   string     `json:"indicator"`
	Type        ThreatType `json:"type"`
	Source      string     `json:"source"`
	Severity    string     `json:"severity"`
	Confidence  float64    `json:"confidence"`
	Description string     `json:"description"`
	FirstSeen   time.Time  `json:"first_seen"`
	LastSeen    time.Time  `json:"last_seen"`
	Tags        []string   `json:"tags"`
	Malware     []string   `json:"malware,omitempty"`
	References  []string   `json:"references,omitempty"`
}

type ThreatMatch struct {
	Entry     *ThreatEntry `json:"entry"`
	IP        string       `json:"ip"`
	Port      uint16       `json:"port"`
	Domain    string       `json:"domain"`
	Timestamp time.Time    `json:"timestamp"`
	Context   string       `json:"context"`
}

type IntelSource struct {
	Name     string
	URL      string
	Type     string
	APIKey   string
	Interval time.Duration
}

type ThreatIntelManager struct {
	mu              sync.RWMutex
	ipThreats       map[string]*ThreatEntry
	domainThreats   map[string]*ThreatEntry
	hashThreats     map[string]*ThreatEntry
	sources         []*IntelSource
	cacheDir        string
	httpClient      *http.Client
	autoBlock       bool
	blockThreshold  float64
	updateTicker    *time.Ticker
	ctx             context.Context
	cancel          context.CancelFunc
	customBlocklist []*ThreatEntry
}

func NewThreatIntelManager(cfg config.ThreatIntelConfig) *ThreatIntelManager {
	if cfg.CacheDir == "" {
		cfg.CacheDir = "/var/run/csm/threatintel"
	}

	ctx, cancel := context.WithCancel(context.Background())

	tm := &ThreatIntelManager{
		ipThreats:       make(map[string]*ThreatEntry),
		domainThreats:   make(map[string]*ThreatEntry),
		hashThreats:     make(map[string]*ThreatEntry),
		cacheDir:        cfg.CacheDir,
		autoBlock:       cfg.AutoBlock,
		blockThreshold:  cfg.BlockThreshold,
		httpClient:      &http.Client{Timeout: 30 * time.Second},
		ctx:             ctx,
		cancel:          cancel,
	}

	for _, src := range cfg.Sources {
		tm.sources = append(tm.sources, &IntelSource{
			Name:     src.Name,
			URL:      src.URL,
			Type:     src.Type,
			APIKey:   src.APIKey,
			Interval: src.Interval,
		})
	}

	if err := os.MkdirAll(cfg.CacheDir, 0750); err != nil {
		logrus.Warnf("Failed to create threat intel cache dir: %v", err)
	}

	tm.loadFromCache()
	tm.addDefaultThreats()

	return tm
}

func (tm *ThreatIntelManager) addDefaultThreats() {
	torIPs := []string{
		"104.244.72.0/24", "104.244.73.0/24", "104.244.74.0/24",
		"104.244.75.0/24", "104.244.76.0/24", "104.244.77.0/24",
	}

	for _, ip := range torIPs {
		tm.ipThreats[ip] = &ThreatEntry{
			Indicator:   ip,
			Type:        ThreatTypeTor,
			Source:      "builtin",
			Severity:    "medium",
			Confidence:  0.8,
			Description: "Tor network exit node",
			Tags:        []string{"tor", "anonymity"},
			FirstSeen:   time.Now(),
			LastSeen:    time.Now(),
		}
	}

	suspiciousDomains := []string{
		"malware-domain.example.com",
		"phishing.example.com",
		"c2-server.example.com",
	}

	for _, domain := range suspiciousDomains {
		tm.domainThreats[domain] = &ThreatEntry{
			Indicator:   domain,
			Type:        ThreatTypeC2,
			Source:      "builtin",
			Severity:    "high",
			Confidence:  0.9,
			Description: "Known C2 server domain",
			Tags:        []string{"c2", "malware"},
			FirstSeen:   time.Now(),
			LastSeen:    time.Now(),
		}
	}
}

func (tm *ThreatIntelManager) Start() {
	if len(tm.sources) == 0 {
		logrus.Info("No threat intel sources configured, skipping updates")
		return
	}

	tm.updateTicker = time.NewTicker(1 * time.Hour)

	go func() {
		tm.updateAllSources()
		for {
			select {
			case <-tm.ctx.Done():
				tm.updateTicker.Stop()
				return
			case <-tm.updateTicker.C:
				tm.updateAllSources()
			}
		}
	}()

	logrus.Infof("Threat intelligence manager started with %d sources", len(tm.sources))
}

func (tm *ThreatIntelManager) Stop() {
	tm.cancel()
	tm.saveToCache()
	logrus.Info("Threat intelligence manager stopped")
}

func (tm *ThreatIntelManager) updateAllSources() {
	logrus.Info("Updating threat intelligence from sources...")
	totalUpdated := 0

	for _, src := range tm.sources {
		count, err := tm.updateSource(src)
		if err != nil {
			logrus.Errorf("Failed to update source %s: %v", src.Name, err)
			continue
		}
		totalUpdated += count
		logrus.Infof("Updated %d entries from %s", count, src.Name)
	}

	tm.saveToCache()
	logrus.Infof("Threat intel update complete, total: %d IPs, %d domains",
		len(tm.ipThreats), len(tm.domainThreats))
}

func (tm *ThreatIntelManager) updateSource(src *IntelSource) (int, error) {
	req, err := http.NewRequestWithContext(tm.ctx, "GET", src.URL, nil)
	if err != nil {
		return 0, err
	}

	if src.APIKey != "" {
		req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", src.APIKey))
	}

	resp, err := tm.httpClient.Do(req)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return 0, fmt.Errorf("unexpected status: %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return 0, err
	}

	return tm.parseSourceData(src, body)
}

func (tm *ThreatIntelManager) parseSourceData(src *IntelSource, data []byte) (int, error) {
	count := 0
	lines := strings.Split(string(data), "\n")

	tm.mu.Lock()
	defer tm.mu.Unlock()

	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		parts := strings.Fields(line)
		if len(parts) < 1 {
			continue
		}

		indicator := parts[0]
		entry := &ThreatEntry{
			Indicator:  indicator,
			Source:     src.Name,
			Confidence: 0.7,
			FirstSeen:  time.Now(),
			LastSeen:   time.Now(),
			Tags:       []string{src.Type},
		}

		if len(parts) >= 2 {
			entry.Type = ThreatType(parts[1])
		} else {
			entry.Type = ThreatTypeMalicious
		}

		if len(parts) >= 3 {
			entry.Severity = parts[2]
		} else {
			entry.Severity = "medium"
		}

		if strings.Contains(indicator, "/") || strings.Count(indicator, ".") == 3 {
			if !tm.isPrivateIP(indicator) {
				tm.ipThreats[indicator] = entry
				count++
			}
		} else if strings.Contains(indicator, ".") {
			tm.domainThreats[indicator] = entry
			count++
		}
	}

	return count, nil
}

func (tm *ThreatIntelManager) CheckIP(ip string) *ThreatMatch {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	entry, exists := tm.ipThreats[ip]
	if !exists {
		for cidr, threat := range tm.ipThreats {
			if strings.Contains(cidr, "/") && tm.ipInCIDR(ip, cidr) {
				return &ThreatMatch{
					Entry:     threat,
					IP:        ip,
					Timestamp: time.Now(),
					Context:   "CIDR match",
				}
			}
		}
		return nil
	}

	return &ThreatMatch{
		Entry:     entry,
		IP:        ip,
		Timestamp: time.Now(),
		Context:   "Direct IP match",
	}
}

func (tm *ThreatIntelManager) CheckDomain(domain string) *ThreatMatch {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	entry, exists := tm.domainThreats[domain]
	if !exists {
		parts := strings.Split(domain, ".")
		for i := 0; i < len(parts)-1; i++ {
			parent := strings.Join(parts[i:], ".")
			if entry, ok := tm.domainThreats[parent]; ok {
				return &ThreatMatch{
					Entry:     entry,
					Domain:    domain,
					Timestamp: time.Now(),
					Context:   "Parent domain match",
				}
			}
		}
		return nil
	}

	return &ThreatMatch{
		Entry:     entry,
		Domain:    domain,
		Timestamp: time.Now(),
		Context:   "Direct domain match",
	}
}

func (tm *ThreatIntelManager) CheckIPAndPort(ip string, port uint16) *ThreatMatch {
	match := tm.CheckIP(ip)
	if match == nil {
		return nil
	}

	match.Port = port

	if tm.autoBlock && match.Entry.Confidence >= tm.blockThreshold {
		match.Context += " (auto-block enabled)"
	}

	return match
}

func (tm *ThreatIntelManager) ShouldBlock(match *ThreatMatch) bool {
	if !tm.autoBlock {
		return false
	}
	return match.Entry.Confidence >= tm.blockThreshold
}

func (tm *ThreatIntelManager) AddCustomBlock(entry *ThreatEntry) {
	tm.mu.Lock()
	defer tm.mu.Unlock()

	entry.Source = "custom"
	entry.FirstSeen = time.Now()
	entry.LastSeen = time.Now()

	if strings.Contains(entry.Indicator, ".") && !strings.Contains(entry.Indicator, "/") {
		tm.domainThreats[entry.Indicator] = entry
	} else {
		tm.ipThreats[entry.Indicator] = entry
	}

	tm.customBlocklist = append(tm.customBlocklist, entry)
	logrus.Infof("Added custom block: %s (%s)", entry.Indicator, entry.Type)
}

func (tm *ThreatIntelManager) RemoveCustomBlock(indicator string) {
	tm.mu.Lock()
	defer tm.mu.Unlock()

	delete(tm.ipThreats, indicator)
	delete(tm.domainThreats, indicator)
	logrus.Infof("Removed custom block: %s", indicator)
}

func (tm *ThreatIntelManager) GetStats() map[string]interface{} {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	return map[string]interface{}{
		"ip_threats":       len(tm.ipThreats),
		"domain_threats":   len(tm.domainThreats),
		"hash_threats":     len(tm.hashThreats),
		"custom_blocks":    len(tm.customBlocklist),
		"auto_block":       tm.autoBlock,
		"block_threshold":  tm.blockThreshold,
	}
}

func (tm *ThreatIntelManager) isPrivateIP(ip string) bool {
	return len(ip) > 3 && (ip[:3] == "10." || ip[:7] == "192.168" || ip[:3] == "172" || ip == "127.0.0.1")
}

func (tm *ThreatIntelManager) ipInCIDR(ip, cidr string) bool {
	parts := strings.Split(cidr, "/")
	if len(parts) != 2 {
		return false
	}

	networkIP := parts[0]
	return strings.HasPrefix(ip, strings.TrimSuffix(networkIP, "0"))
}

func (tm *ThreatIntelManager) saveToCache() {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	cacheFile := filepath.Join(tm.cacheDir, "threats.json")
	data := map[string]interface{}{
		"ips":     tm.ipThreats,
		"domains": tm.domainThreats,
		"custom":  tm.customBlocklist,
		"updated": time.Now(),
	}

	jsonData, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		logrus.Errorf("Failed to marshal threat cache: %v", err)
		return
	}

	if err := os.WriteFile(cacheFile, jsonData, 0640); err != nil {
		logrus.Errorf("Failed to save threat cache: %v", err)
	}
}

func (tm *ThreatIntelManager) loadFromCache() {
	cacheFile := filepath.Join(tm.cacheDir, "threats.json")
	data, err := os.ReadFile(cacheFile)
	if err != nil {
		logrus.Infof("No threat cache found at %s", cacheFile)
		return
	}

	var cache struct {
		IPs     map[string]*ThreatEntry `json:"ips"`
		Domains map[string]*ThreatEntry `json:"domains"`
		Custom  []*ThreatEntry          `json:"custom"`
	}

	if err := json.Unmarshal(data, &cache); err != nil {
		logrus.Errorf("Failed to parse threat cache: %v", err)
		return
	}

	tm.mu.Lock()
	defer tm.mu.Unlock()

	tm.ipThreats = cache.IPs
	tm.domainThreats = cache.Domains
	tm.customBlocklist = cache.Custom

	logrus.Infof("Loaded %d IPs, %d domains from cache", len(tm.ipThreats), len(tm.domainThreats))
}

func (tm *ThreatIntelManager) GetThreatByIP(ip string) *ThreatEntry {
	tm.mu.RLock()
	defer tm.mu.RUnlock()
	return tm.ipThreats[ip]
}

func (tm *ThreatIntelManager) GetThreatByDomain(domain string) *ThreatEntry {
	tm.mu.RLock()
	defer tm.mu.RUnlock()
	return tm.domainThreats[domain]
}
