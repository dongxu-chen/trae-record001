package models

import (
	"time"

	"gorm.io/gorm"
)

type Domain struct {
	ID         uint           `gorm:"primarykey" json:"id"`
	DomainName string         `gorm:"uniqueIndex;not null" json:"domain_name"`
	Port       int            `gorm:"default:443" json:"port"`
	Remark     string         `json:"remark"`
	Tag        string         `json:"tag"`
	Enabled    bool           `gorm:"default:true" json:"enabled"`
	CreatedAt  time.Time      `json:"created_at"`
	UpdatedAt  time.Time      `json:"updated_at"`
	DeletedAt  gorm.DeletedAt `gorm:"index" json:"-"`
}

type CertRecord struct {
	ID                 uint           `gorm:"primarykey" json:"id"`
	DomainID           uint           `gorm:"index;not null" json:"domain_id"`
	Domain             string         `gorm:"index" json:"domain"`
	Port               int            `json:"port"`
	Subject            string         `json:"subject"`
	Issuer             string         `json:"issuer"`
	NotBefore          time.Time      `json:"not_before"`
	NotAfter           time.Time      `json:"not_after"`
	SignatureAlgo      string         `json:"signature_algo"`
	PublicKeyAlgo      string         `json:"public_key_algo"`
	PublicKeyBits      int            `json:"public_key_bits"`
	SerialNumber       string         `json:"serial_number"`
	Fingerprint        string         `json:"fingerprint"`
	SANs               string         `json:"sans"`
	DaysLeft           int            `json:"days_left"`
	Status             string         `json:"status"`
	Version            int            `json:"version"`
	ErrorMsg           string         `json:"error_msg"`
	LastCheckedAt      time.Time      `json:"last_checked_at"`
	CreatedAt          time.Time      `json:"created_at"`
	UpdatedAt          time.Time      `json:"updated_at"`
	DeletedAt          gorm.DeletedAt `gorm:"index" json:"-"`
	// 证书链相关
	CertChainComplete  bool           `json:"cert_chain_complete"`
	MissingCerts       string         `json:"missing_certs"`
	ChainLength        int            `json:"chain_length"`
	RootCA             string         `json:"root_ca"`
	// CT日志相关
	CTLogged           bool           `json:"ct_logged"`
	CTLogCount         int            `json:"ct_log_count"`
	CTLogs             string         `json:"ct_logs"`
}

type AlertLog struct {
	ID         uint           `gorm:"primarykey" json:"id"`
	DomainID   uint           `gorm:"index" json:"domain_id"`
	Domain     string         `gorm:"index" json:"domain"`
	AlertType  string         `json:"alert_type"`
	Level      string         `json:"level"`
	Content    string         `json:"content"`
	Sent       bool           `gorm:"default:false" json:"sent"`
	SentAt     *time.Time     `json:"sent_at"`
	ErrorMsg   string         `json:"error_msg"`
	CreatedAt  time.Time      `json:"created_at"`
	UpdatedAt  time.Time      `json:"updated_at"`
	DeletedAt  gorm.DeletedAt `gorm:"index" json:"-"`
}

type ReportData struct {
	TotalDomains      int       `json:"total_domains"`
	ValidCerts        int       `json:"valid_certs"`
	ExpiringSoon      int       `json:"expiring_soon"`
	Expired           int       `json:"expired"`
	FailedChecks      int       `json:"failed_checks"`
	LastScanTime      time.Time `json:"last_scan_time"`
}

type AlgorithmRule struct {
	ID          uint           `gorm:"primarykey" json:"id"`
	Version     string         `json:"version"`
	RuleType    string         `json:"rule_type"`
	Algorithm   string         `gorm:"uniqueIndex" json:"algorithm"`
	Status      string         `json:"status"`
	MinBits     int            `json:"min_bits"`
	Description string         `json:"description"`
	Reference   string         `json:"reference"`
	Source      string         `json:"source"`
	UpdatedAt   time.Time      `json:"updated_at"`
}

type SubdomainRecord struct {
	ID           uint           `gorm:"primarykey" json:"id"`
	ParentDomain string         `gorm:"index" json:"parent_domain"`
	Subdomain    string         `gorm:"uniqueIndex" json:"subdomain"`
	Source       string         `json:"source"`
	RecordType   string         `json:"record_type"`
	RecordValue  string         `json:"record_value"`
	AutoAdded    bool           `gorm:"default:false" json:"auto_added"`
	Monitored    bool           `gorm:"default:false" json:"monitored"`
	DiscoveredAt time.Time      `json:"discovered_at"`
	CreatedAt    time.Time      `json:"created_at"`
	UpdatedAt    time.Time      `json:"updated_at"`
}

type DNSRecord struct {
	ID         uint           `gorm:"primarykey" json:"id"`
	Domain     string         `gorm:"index" json:"domain"`
	RecordType string         `json:"record_type"`
	Value      string         `json:"value"`
	TTL        int            `json:"ttl"`
	Priority   int            `json:"priority"`
	Server     string         `json:"server"`
	ScannedAt  time.Time      `json:"scanned_at"`
	CreatedAt  time.Time      `json:"created_at"`
	UpdatedAt  time.Time      `json:"updated_at"`
}

type RuleUpdateLog struct {
	ID          uint      `gorm:"primarykey" json:"id"`
	Version     string    `json:"version"`
	TotalRules  int       `json:"total_rules"`
	AddedRules  int       `json:"added_rules"`
	UpdatedRules int      `json:"updated_rules"`
	RemovedRules int      `json:"removed_rules"`
	Source      string    `json:"source"`
	Status      string    `json:"status"`
	ErrorMsg    string    `json:"error_msg"`
	UpdatedAt   time.Time `json:"updated_at"`
}

type AlgoStrengthResult struct {
	Algorithm   string `json:"algorithm"`
	Bits        int    `json:"bits"`
	Status      string `json:"status"`
	Description string `json:"description"`
	Score       int    `json:"score"`
}

type CertChainInfo struct {
	Complete      bool     `json:"complete"`
	ChainLength   int      `json:"chain_length"`
	RootCA        string   `json:"root_ca"`
	Intermediates []string `json:"intermediates"`
	MissingCerts  []string `json:"missing_certs"`
	Errors        []string `json:"errors"`
}

type CTLogEntry struct {
	LogOperator string    `json:"log_operator"`
	LogName     string    `json:"log_name"`
	Timestamp   time.Time `json:"timestamp"`
	EntryHash   string    `json:"entry_hash"`
}

type CTLogResult struct {
	Logged    bool          `json:"logged"`
	LogCount  int           `json:"log_count"`
	Entries   []CTLogEntry  `json:"entries"`
	Errors    []string      `json:"errors"`
	Unlogged  bool          `json:"unlogged"`
}

type CertDiff struct {
	Field       string      `json:"field"`
	OldValue    interface{} `json:"old_value"`
	NewValue    interface{} `json:"new_value"`
	ChangeType  string      `json:"change_type"` // added, removed, modified
}

type CertCompareResult struct {
	Domain         string     `json:"domain"`
	OldCertID      uint       `json:"old_cert_id"`
	NewCertID      uint       `json:"new_cert_id"`
	OldFingerprint string     `json:"old_fingerprint"`
	NewFingerprint string     `json:"new_fingerprint"`
	Diffs          []CertDiff `json:"diffs"`
	DiffCount      int        `json:"diff_count"`
	ImportantDiffs []CertDiff `json:"important_diffs"`
	IsRenewal      bool       `json:"is_renewal"`
	IsIssuerChanged bool      `json:"is_issuer_changed"`
	IsAlgoChanged  bool       `json:"is_algo_changed"`
	ComparedAt     time.Time  `json:"compared_at"`
}
