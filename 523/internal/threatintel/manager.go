package threatintel

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/sirupsen/logrus"

	"github.com/security/container-escape-detector/pkg/types"
)

type Config struct {
	Enabled          bool     `yaml:"enabled"`
	UpdateURLs       []string `yaml:"update_urls"`
	UpdateInterval   int      `yaml:"update_interval_hours"`
	CacheDir         string   `yaml:"cache_dir"`
	AutoUpdate       bool     `yaml:"auto_update"`
	FeedNames        []string `yaml:"feed_names"`
	CustomSignatures []string `yaml:"custom_signatures"`
}

type Manager struct {
	config          *Config
	logger          *logrus.Logger
	stopChan        chan struct{}
	wg              sync.WaitGroup
	mu              sync.RWMutex
	signatures      map[string]ThreatSignature
	patternCache    map[string]*regexp.Regexp
	iocs            map[string]IOCEntry
	lastUpdate      time.Time
	running         bool
}

type ThreatSignature struct {
	ID            string        `json:"id"`
	Name          string        `json:"name"`
	Description   string        `json:"description"`
	Severity      string        `json:"severity"`
	Technique     string        `json:"technique"`
	Category      string        `json:"category"`
	Patterns      []string      `json:"patterns"`
	FilePatterns  []string      `json:"file_patterns"`
	SyscallNames  []string      `json:"syscall_names"`
	CAPNames      []string      `json:"cap_names"`
	MountPatterns []string      `json:"mount_patterns"`
	MitreAttack   []string      `json:"mitre_attack"`
	CVEs          []string      `json:"cves"`
	References    []string      `json:"references"`
	CreatedAt     time.Time     `json:"created_at"`
	UpdatedAt     time.Time     `json:"updated_at"`
	Hash          string        `json:"hash"`
}

type IOCEntry struct {
	Type      string    `json:"type"`
	Value     string    `json:"value"`
	Source    string    `json:"source"`
	FirstSeen time.Time `json:"first_seen"`
	LastSeen  time.Time `json:"last_seen"`
}

type ThreatFeed struct {
	Name         string            `json:"name"`
	Version      string            `json:"version"`
	GeneratedAt  time.Time         `json:"generated_at"`
	Signatures   []ThreatSignature `json:"signatures"`
	IOCs         []IOCEntry        `json:"iocs"`
}

type MatchResult struct {
	SignatureID   string
	SignatureName string
	Severity      types.RiskLevel
	MatchedOn     string
	MatchedValue  string
	Confidence    float64
}

func NewManager(logger *logrus.Logger, config *Config) *Manager {
	if config == nil {
		config = &Config{
			Enabled:        true,
			UpdateInterval: 24,
			CacheDir:       "/var/lib/escape-detector/threatintel",
			AutoUpdate:     true,
		}
	}

	return &Manager{
		config:       config,
		logger:       logger,
		stopChan:     make(chan struct{}),
		signatures:   make(map[string]ThreatSignature),
		patternCache: make(map[string]*regexp.Regexp),
		iocs:         make(map[string]IOCEntry),
	}
}

func (m *Manager) Start() error {
	if !m.config.Enabled {
		m.logger.Info("Threat intelligence manager disabled")
		return nil
	}

	m.mu.Lock()
	if m.running {
		m.mu.Unlock()
		return fmt.Errorf("threat intel manager already running")
	}
	m.running = true
	m.mu.Unlock()

	if err := os.MkdirAll(m.config.CacheDir, 0755); err != nil {
		m.logger.Warnf("Failed to create cache directory: %v", err)
	}

	m.loadBuiltinSignatures()
	m.loadFromCache()

	if m.config.AutoUpdate {
		m.wg.Add(1)
		go m.updateLoop()
	}

	m.logger.Infof("Threat intel manager started: %d signatures, %d IOCs",
		len(m.signatures), len(m.iocs))
	return nil
}

func (m *Manager) Stop() {
	m.mu.Lock()
	if !m.running {
		m.mu.Unlock()
		return
	}
	m.running = false
	m.mu.Unlock()

	close(m.stopChan)
	m.wg.Wait()

	m.saveToCache()
	m.logger.Info("Threat intel manager stopped")
}

func (m *Manager) loadBuiltinSignatures() {
	builtin := getBuiltinSignatures()

	for _, sig := range builtin {
		sig.Hash = computeSignatureHash(sig)
		m.signatures[sig.ID] = sig
	}

	m.logger.Infof("Loaded %d builtin threat signatures", len(builtin))
}

func (m *Manager) updateLoop() {
	defer m.wg.Done()

	interval := time.Duration(m.config.UpdateInterval) * time.Hour
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	m.UpdateFeeds()

	for {
		select {
		case <-m.stopChan:
			return
		case <-ticker.C:
			m.UpdateFeeds()
		}
	}
}

func (m *Manager) UpdateFeeds() error {
	m.logger.Info("Updating threat intelligence feeds")

	if len(m.config.UpdateURLs) == 0 {
		m.logger.Debug("No update URLs configured, using builtin signatures")
		return nil
	}

	var newSignatures []ThreatSignature
	var newIOCs []IOCEntry

	for _, url := range m.config.UpdateURLs {
		feed, err := m.downloadFeed(url)
		if err != nil {
			m.logger.Warnf("Failed to download feed %s: %v", url, err)
			continue
		}

		newSignatures = append(newSignatures, feed.Signatures...)
		newIOCs = append(newIOCs, feed.IOCs...)
	}

	m.mu.Lock()
	for _, sig := range newSignatures {
		sig.Hash = computeSignatureHash(sig)
		if existing, exists := m.signatures[sig.ID]; !exists || sig.UpdatedAt.After(existing.UpdatedAt) {
			m.signatures[sig.ID] = sig
		}
	}

	for _, ioc := range newIOCs {
		key := fmt.Sprintf("%s:%s", ioc.Type, ioc.Value)
		m.iocs[key] = ioc
	}
	m.lastUpdate = time.Now()
	m.mu.Unlock()

	m.saveToCache()
	m.logger.Infof("Updated threat feeds: %d signatures, %d IOCs", len(newSignatures), len(newIOCs))
	return nil
}

func (m *Manager) downloadFeed(url string) (*ThreatFeed, error) {
	client := &http.Client{Timeout: 30 * time.Second}

	resp, err := client.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var feed ThreatFeed
	if err := json.Unmarshal(body, &feed); err != nil {
		return nil, err
	}

	return &feed, nil
}

func (m *Manager) MatchEvent(event *types.BPFEvent) []MatchResult {
	if !m.config.Enabled {
		return nil
	}

	m.mu.RLock()
	defer m.mu.RUnlock()

	var results []MatchResult

	for _, sig := range m.signatures {
		if matched, value := m.matchSignature(sig, event); matched {
			results = append(results, MatchResult{
				SignatureID:   sig.ID,
				SignatureName: sig.Name,
				Severity:      parseSeverity(sig.Severity),
				MatchedOn:     "signature",
				MatchedValue:  value,
				Confidence:    0.9,
			})
		}
	}

	return results
}

func (m *Manager) matchSignature(sig ThreatSignature, event *types.BPFEvent) (bool, string) {
	for _, syscall := range sig.SyscallNames {
		if event.SyscallName == syscall {
			return true, fmt.Sprintf("syscall:%s", syscall)
		}
	}

	for _, capName := range sig.CAPNames {
		if event.CapName == capName {
			return true, fmt.Sprintf("capability:%s", capName)
		}
	}

	for _, pattern := range sig.MountPatterns {
		if strings.Contains(event.MountSource, pattern) || strings.Contains(event.MountTarget, pattern) {
			return true, fmt.Sprintf("mount:%s", pattern)
		}
	}

	for _, pattern := range sig.FilePatterns {
		re, err := m.getPattern(pattern)
		if err == nil && re.MatchString(event.FileName) {
			return true, fmt.Sprintf("file:%s", pattern)
		}
	}

	for _, pattern := range sig.Patterns {
		re, err := m.getPattern(pattern)
		if err == nil {
			eventStr := fmt.Sprintf("%s %s %s %s %s",
				event.Comm, event.SyscallName, event.FileName,
				event.MountSource, event.CapName)
			if re.MatchString(eventStr) {
				return true, fmt.Sprintf("pattern:%s", pattern)
			}
		}
	}

	return false, ""
}

func (m *Manager) getPattern(pattern string) (*regexp.Regexp, error) {
	if re, exists := m.patternCache[pattern]; exists {
		return re, nil
	}

	re, err := regexp.Compile(pattern)
	if err != nil {
		return nil, err
	}

	m.patternCache[pattern] = re
	return re, nil
}

func (m *Manager) GetSignatures() []ThreatSignature {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make([]ThreatSignature, 0, len(m.signatures))
	for _, sig := range m.signatures {
		result = append(result, sig)
	}
	return result
}

func (m *Manager) AddSignature(sig ThreatSignature) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	sig.Hash = computeSignatureHash(sig)
	sig.CreatedAt = time.Now()
	sig.UpdatedAt = time.Now()
	m.signatures[sig.ID] = sig

	m.saveToCache()
	m.logger.Infof("Added signature: %s (%s)", sig.ID, sig.Name)
	return nil
}

func (m *Manager) RemoveSignature(id string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, exists := m.signatures[id]; !exists {
		return fmt.Errorf("signature %s not found", id)
	}

	delete(m.signatures, id)
	m.saveToCache()
	m.logger.Infof("Removed signature: %s", id)
	return nil
}

func (m *Manager) saveToCache() {
	if m.config.CacheDir == "" {
		return
	}

	sigPath := filepath.Join(m.config.CacheDir, "signatures.json")
	iocPath := filepath.Join(m.config.CacheDir, "iocs.json")

	if data, err := json.MarshalIndent(m.signatures, "", "  "); err == nil {
		os.WriteFile(sigPath, data, 0644)
	}

	if data, err := json.MarshalIndent(m.iocs, "", "  "); err == nil {
		os.WriteFile(iocPath, data, 0644)
	}
}

func (m *Manager) loadFromCache() {
	if m.config.CacheDir == "" {
		return
	}

	sigPath := filepath.Join(m.config.CacheDir, "signatures.json")
	if data, err := os.ReadFile(sigPath); err == nil {
		var sigs map[string]ThreatSignature
		if err := json.Unmarshal(data, &sigs); err == nil {
			m.mu.Lock()
			for id, sig := range sigs {
				m.signatures[id] = sig
			}
			m.mu.Unlock()
		}
	}
}

func (m *Manager) GetLastUpdate() time.Time {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.lastUpdate
}

func (m *Manager) SignatureCount() int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return len(m.signatures)
}

func computeSignatureHash(sig ThreatSignature) string {
	data := fmt.Sprintf("%s|%s|%s|%v", sig.ID, sig.Name, sig.Description, sig.Patterns)
	hash := sha256.Sum256([]byte(data))
	return fmt.Sprintf("%x", hash[:16])
}

func parseSeverity(s string) types.RiskLevel {
	switch strings.ToUpper(s) {
	case "CRITICAL":
		return types.RiskCritical
	case "HIGH":
		return types.RiskHigh
	case "MEDIUM":
		return types.RiskMedium
	case "LOW":
		return types.RiskLow
	default:
		return types.RiskInfo
	}
}

func getBuiltinSignatures() []ThreatSignature {
	return []ThreatSignature{
		{
			ID:            "TI-ESCAPE-001",
			Name:          "Docker Socket Mount Escape",
			Description:   "Detection of docker.sock mount for container escape",
			Severity:      "CRITICAL",
			Technique:     "T1611",
			Category:      "escape",
			MountPatterns: []string{"docker.sock", "/var/run/docker"},
			MitreAttack:   []string{"T1611", "T1200"},
			CVEs:          []string{},
			CreatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
			UpdatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
		},
		{
			ID:            "TI-ESCAPE-002",
			Name:          "CGroup v1 Release Agent Attack",
			Description:   "Known cgroup v1 release_agent exploitation technique",
			Severity:      "CRITICAL",
			Technique:     "T1068",
			Category:      "escape",
			FilePatterns:  []string{"release_agent", "notify_on_release"},
			SyscallNames:  []string{"mount"},
			MitreAttack:   []string{"T1068", "T1546"},
			CVEs:          []string{},
			CreatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
			UpdatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
		},
		{
			ID:            "TI-ESCAPE-003",
			Name:          "Host /proc Filesystem Mount",
			Description:   "Suspicious mount of host /proc filesystem",
			Severity:      "HIGH",
			Technique:     "T1005",
			Category:      "escape",
			MountPatterns: []string{"/proc"},
			MitreAttack:   []string{"T1005"},
			CreatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
			UpdatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
		},
		{
			ID:            "TI-ESCAPE-004",
			Name:          "CAP_SYS_ADMIN Capability Abuse",
			Description:   "Known technique using CAP_SYS_ADMIN for escape",
			Severity:      "HIGH",
			Technique:     "T1068",
			Category:      "privilege-escalation",
			CAPNames:      []string{"CAP_SYS_ADMIN", "CAP_SYS_MODULE"},
			MitreAttack:   []string{"T1068"},
			CreatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
			UpdatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
		},
		{
			ID:            "TI-ESCAPE-005",
			Name:          "Ptrace Process Injection",
			Description:   "Known ptrace injection technique for escape",
			Severity:      "HIGH",
			Technique:     "T1055",
			Category:      "privilege-escalation",
			SyscallNames:  []string{"ptrace"},
			CAPNames:      []string{"CAP_SYS_PTRACE"},
			MitreAttack:   []string{"T1055"},
			CreatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
			UpdatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
		},
		{
			ID:            "TI-ESCAPE-006",
			Name:          "Kubernetes Service Account Exposure",
			Description:   "Exposed K8s service account token for lateral movement",
			Severity:      "HIGH",
			Technique:     "T1552",
			Category:      "credential-access",
			FilePatterns:  []string{"serviceaccount/token"},
			MitreAttack:   []string{"T1552"},
			CreatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
			UpdatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
		},
		{
			ID:            "TI-ESCAPE-007",
			Name:          "MKNOD Device Creation",
			Description:   "Device node creation for disk access escape",
			Severity:      "CRITICAL",
			Technique:     "T1200",
			Category:      "escape",
			SyscallNames:  []string{"mknod"},
			CAPNames:      []string{"CAP_MKNOD"},
			MitreAttack:   []string{"T1200"},
			CreatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
			UpdatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
		},
		{
			ID:            "TI-ESCAPE-008",
			Name:          "Namespace Manipulation",
			Description:   "setns/unshare namespace escape technique",
			Severity:      "HIGH",
			Technique:     "T1020",
			Category:      "escape",
			SyscallNames:  []string{"setns", "unshare", "clone"},
			MitreAttack:   []string{"T1020"},
			CreatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
			UpdatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
		},
		{
			ID:            "TI-ESCAPE-009",
			Name:          "Kernel Module Loading",
			Description:   "Kernel module load for privilege escalation",
			Severity:      "CRITICAL",
			Technique:     "T1547",
			Category:      "privilege-escalation",
			SyscallNames:  []string{"init_module", "delete_module", "finit_module"},
			MitreAttack:   []string{"T1547"},
			CreatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
			UpdatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
		},
		{
			ID:            "TI-ESCAPE-010",
			Name:          "Host Root Filesystem Mount",
			Description:   "Full host root filesystem mounted in container",
			Severity:      "CRITICAL",
			Technique:     "T1005",
			Category:      "escape",
			MountPatterns: []string{"/", "/root", "/host", "/rootfs"},
			MitreAttack:   []string{"T1005"},
			CreatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
			UpdatedAt:     time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
		},
	}
}
