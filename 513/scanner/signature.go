package scanner

import (
	"crypto/md5"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

type ServiceSignature struct {
	Port        int      `json:"port"`
	Service     string   `json:"service"`
	Protocol    string   `json:"protocol"`
	Probes      []Probe  `json:"probes"`
	VersionPatterns []VersionPattern `json:"version_patterns"`
	CommonVersions []string `json:"common_versions"`
	DefaultBanner string `json:"default_banner"`
	UpdatedAt    string `json:"updated_at"`
}

type Probe struct {
	Name     string `json:"name"`
	Payload  string `json:"payload"`
	Expected string `json:"expected"`
}

type VersionPattern struct {
	Pattern string `json:"pattern"`
	Regex   string `json:"regex"`
}

type SignatureDB struct {
	Version      string                      `json:"version"`
	LastUpdated  time.Time                 `json:"last_updated"`
	SourceURL    string                    `json:"source_url"`
	Signatures   map[int]ServiceSignature  `json:"signatures"`
	Checksum     string                    `json:"checksum"`
}

type SignatureManager struct {
	db            *SignatureDB
	cacheDir      string
	mu            sync.RWMutex
	autoUpdate    bool
	updateInterval time.Duration
}

var defaultSignatures = map[int]ServiceSignature{
	21: {
		Port:     21,
		Service:  "FTP",
		Protocol: "TCP",
		Probes: []Probe{
			{Name: "banner", Payload: "", Expected: "220"},
		},
		VersionPatterns: []VersionPattern{
			{Pattern: "220.*FTP", Regex: `220[\s-]([^\s]+)`},
			{Pattern: "ProFTPD", Regex: `ProFTPD\s+([\d.]+)`},
			{Pattern: "vsFTPd", Regex: `vsFTPd\s+([\d.]+)`},
		},
		CommonVersions: []string{"vsFTPd 3.0.3", "ProFTPD 1.3.5", "Pure-FTPd 1.0.49"},
		DefaultBanner: "220 FTP Server ready",
		UpdatedAt:     "2024-01-15",
	},
	22: {
		Port:     22,
		Service:  "SSH",
		Protocol: "TCP",
		Probes: []Probe{
			{Name: "banner", Payload: "", Expected: "SSH-"},
		},
		VersionPatterns: []VersionPattern{
			{Pattern: "SSH-", Regex: `SSH-([\d.]+)-(.+)`},
			{Pattern: "OpenSSH", Regex: `OpenSSH_([\d.p]+)`},
		},
		CommonVersions: []string{"OpenSSH_8.9p1", "OpenSSH_7.4p1", "OpenSSH_9.0p1"},
		DefaultBanner: "SSH-2.0-OpenSSH",
		UpdatedAt:     "2024-01-15",
	},
	80: {
		Port:     80,
		Service:  "HTTP",
		Protocol: "TCP",
		Probes: []Probe{
			{Name: "get", Payload: "GET / HTTP/1.0\r\n\r\n", Expected: "HTTP/"},
			{Name: "head", Payload: "HEAD / HTTP/1.0\r\n\r\n", Expected: "HTTP/"},
		},
		VersionPatterns: []VersionPattern{
			{Pattern: "Server:", Regex: `Server:\s*([^\r\n]+)`},
			{Pattern: "nginx", Regex: `nginx/([\d.]+)`},
			{Pattern: "Apache", Regex: `Apache/([\d.]+)`},
		},
		CommonVersions: []string{"nginx/1.24.0", "Apache/2.4.57", "Microsoft-IIS/10.0"},
		DefaultBanner: "HTTP/1.1 200 OK",
		UpdatedAt:     "2024-01-15",
	},
	6379: {
		Port:     6379,
		Service:  "Redis",
		Protocol: "TCP",
		Probes: []Probe{
			{Name: "ping", Payload: "PING\r\n", Expected: "+PONG"},
			{Name: "info", Payload: "INFO\r\n", Expected: "redis_version"},
		},
		VersionPatterns: []VersionPattern{
			{Pattern: "redis_version:", Regex: `redis_version:([\d.]+)`},
		},
		CommonVersions: []string{"Redis 7.2.0", "Redis 6.2.12", "Redis 5.0.14"},
		DefaultBanner: "+PONG",
		UpdatedAt:     "2024-01-15",
	},
	3306: {
		Port:     3306,
		Service:  "MySQL",
		Protocol: "TCP",
		Probes: []Probe{
			{Name: "handshake", Payload: "", Expected: "\x0a"},
		},
		VersionPatterns: []VersionPattern{
			{Pattern: "5\.", Regex: `^[\x00-\xff]*?([\d.]+)`},
		},
		CommonVersions: []string{"MySQL 8.0.36", "MySQL 5.7.42", "MySQL 8.2.0", "MariaDB 10.11.6"},
		DefaultBanner: "\x0a",
		UpdatedAt:     "2024-01-15",
	},
	27017: {
		Port:     27017,
		Service:  "MongoDB",
		Protocol: "TCP",
		Probes: []Probe{
			{Name: "ismaster", Payload: "\x3a\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xd4\x07\x00\x00\x00\x00\x00\x00admin.$cmd\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", Expected: "MongoDB"},
		},
		VersionPatterns: []VersionPattern{
			{Pattern: "version", Regex: `"version"\s*:\s*"([^"]+)`},
		},
		CommonVersions: []string{"MongoDB 7.0.5", "MongoDB 6.0.13", "MongoDB 5.0.24"},
		DefaultBanner: "MongoDB",
		UpdatedAt:     "2024-01-15",
	},
}

var signatureSources = []string{
	"https://raw.githubusercontent.com/nmap/nmap/master/nmap-service-probes",
	"https://raw.githubusercontent.com/nmap/nmap/master/nmap-services",
}

func NewSignatureManager() *SignatureManager {
	cacheDir := getDefaultCacheDir()
	return &SignatureManager{
		cacheDir:       cacheDir,
		autoUpdate:     true,
		updateInterval: 24 * time.Hour,
	}
}

func getDefaultCacheDir() string {
	home, err := os.UserHomeDir()
	if err != nil {
		home = "."
	}
	cacheDir := filepath.Join(home, ".portscanner", "signatures")
	os.MkdirAll(cacheDir, 0755)
	return cacheDir
}

func (sm *SignatureManager) Load() error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	dbPath := filepath.Join(sm.cacheDir, "signatures.json")
	
	if _, err := os.Stat(dbPath); os.IsNotExist(err) {
		return sm.initDefaultDB()
	}

	data, err := os.ReadFile(dbPath)
	if err != nil {
		return err
	}

	var db SignatureDB
	if err := json.Unmarshal(data, &db); err != nil {
		return sm.initDefaultDB()
	}

	sm.db = &db

	if sm.autoUpdate && time.Since(db.LastUpdated) > sm.updateInterval {
		go sm.Update()
	}

	return nil
}

func (sm *SignatureManager) initDefaultDB() error {
	db := &SignatureDB{
		Version:     "1.0.0",
		LastUpdated: time.Now(),
		SourceURL:   "built-in",
		Signatures: defaultSignatures,
	}

	checksum := calculateChecksum(db)
	db.Checksum = checksum

	sm.db = db
	return sm.save()
}

func calculateChecksum(db *SignatureDB) string {
	data, _ := json.Marshal(db.Signatures)
	return fmt.Sprintf("%x", md5.Sum(data))
}

func (sm *SignatureManager) save() error {
	dbPath := filepath.Join(sm.cacheDir, "signatures.json")
	data, err := json.MarshalIndent(sm.db, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(dbPath, data, 0644)
}

func (sm *SignatureManager) Update() error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	fmt.Println("🔄 正在更新服务特征库...")

	newSignatures := make(map[int]ServiceSignature)
	for port, sig := range sm.db.Signatures {
		newSignatures[port] = sig
	}

	for _, source := range signatureSources {
		if err := sm.updateFromSource(source, newSignatures); err != nil {
			fmt.Printf("⚠️  从 %s 更新失败: %v\n", source, err)
		}
	}

	sm.updateCommonVersions(newSignatures)

	sm.db.Signatures = newSignatures
	sm.db.LastUpdated = time.Now()
	sm.db.Version = fmt.Sprintf("1.0.%d", time.Now().Unix())
	sm.db.Checksum = calculateChecksum(sm.db)

	if err := sm.save(); err != nil {
		return err
	}

	fmt.Printf("✅ 特征库更新完成，当前版本: %s\n", sm.db.Version)
	fmt.Printf("📅 最后更新: %s\n", sm.db.LastUpdated.Format("2006-01-02 15:04:05"))
	fmt.Printf("📊 覆盖服务数量: %d\n", len(sm.db.Signatures))

	return nil
}

func (sm *SignatureManager) updateFromSource(source string, sigs map[int]ServiceSignature) error {
	client := &http.Client{
		Timeout: 30 * time.Second,
	}

	resp, err := client.Get(source)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}

	lines := strings.Split(string(body), "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		parts := strings.Fields(line)
		if len(parts) >= 2 {
			portStr := parts[0]
			serviceName := parts[1]
			port := 0
			fmt.Sscanf(portStr, "%d", &port)
			if port > 0 {
				if _, exists := sigs[port]; !exists {
					sigs[port] = ServiceSignature{
						Port:     port,
						Service:  serviceName,
						Protocol: "TCP",
						UpdatedAt: time.Now().Format("2006-01-02"),
					}
				}
			}
		}
	}

	return nil
}

func (sm *SignatureManager) updateCommonVersions(sigs map[int]ServiceSignature) {
	versionUpdates := map[int][]string{
		22:   {"OpenSSH_9.3p1", "OpenSSH_9.2p1", "OpenSSH_8.9p1", "OpenSSH_7.9p1"},
		80:   {"nginx/1.25.3", "Apache/2.4.58", "Caddy/2.7.5"},
		6379: {"Redis 7.2.3", "Redis 7.0.15", "Redis 6.2.14"},
		3306: {"MySQL 8.2.0", "MySQL 8.0.36", "MariaDB 11.2.2"},
		27017: {"MongoDB 7.0.4", "MongoDB 6.0.13"},
	}

	for port, versions := range versionUpdates {
		if sig, exists := sigs[port]; exists {
			sig.CommonVersions = append(sig.CommonVersions, versions...)
			sig.UpdatedAt = time.Now().Format("2006-01-02")
			sigs[port] = sig
		}
	}
}

func (sm *SignatureManager) GetSignature(port int) (ServiceSignature, bool) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	if sm.db == nil {
		sm.Load()
	}

	sig, ok := sm.db.Signatures[port]
	return sig, ok
}

func (sm *SignatureManager) GetAllSignatures() map[int]ServiceSignature {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	if sm.db == nil {
		sm.Load()
	}

	return sm.db.Signatures
}

func (sm *SignatureManager) GetDBInfo() map[string]interface{} {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	if sm.db == nil {
		sm.Load()
	}

	return map[string]interface{}{
		"version":      sm.db.Version,
		"last_updated": sm.db.LastUpdated,
		"source":      sm.db.SourceURL,
		"count":       len(sm.db.Signatures),
		"checksum":    sm.db.Checksum,
	}
}

func (sm *SignatureManager) CheckUpdate() (bool, string) {
	if sm.db == nil {
		return true, "需要初始化"
	}

	if time.Since(sm.db.LastUpdated) > sm.updateInterval {
		return true, fmt.Sprintf("距离上次更新已超过 %v", sm.updateInterval)
	}

	return false, "特征库为最新版本"
}

func (sm *SignatureManager) AddCustomSignature(sig ServiceSignature) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	sig.UpdatedAt = time.Now().Format("2006-01-02")
	sm.db.Signatures[sig.Port] = sig
	return sm.save()
}

func (sm *SignatureManager) RemoveSignature(port int) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	delete(sm.db.Signatures, port)
	return sm.save()
}

func (sm *SignatureManager) ExportSignatures(filename string) error {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	data, err := json.MarshalIndent(sm.db, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(filename, data, 0644)
}

func (sm *SignatureManager) ImportSignatures(filename string) error {
	data, err := os.ReadFile(filename)
	if err != nil {
		return err
	}

	var db SignatureDB
	if err := json.Unmarshal(data, &db); err != nil {
		return err
	}

	sm.mu.Lock()
	defer sm.mu.Unlock()

	for port, sig := range db.Signatures {
		sm.db.Signatures[port] = sig
	}

	sm.db.LastUpdated = time.Now()
	sm.db.Checksum = calculateChecksum(sm.db)

	return sm.save()
}
