package types

import "time"

type NodeInfo struct {
	Path         string    `json:"path"`
	DataSize     int64     `json:"data_size"`
	ChildCount   int       `json:"child_count"`
	Depth        int       `json:"depth"`
	Children     []string  `json:"children"`
	Ephemeral    bool      `json:"ephemeral"`
	LastModified time.Time `json:"last_modified"`
}

type TTLRecord struct {
	Path      string    `json:"path"`
	TTL       int64     `json:"ttl"`
	CreatedAt time.Time `json:"created_at"`
	ExpiresAt time.Time `json:"expires_at"`
}

type CleanResult struct {
	Timestamp    time.Time `json:"timestamp"`
	Deleted      []string  `json:"deleted"`
	Errors       []string  `json:"errors"`
	Scanned      int       `json:"scanned"`
	DeletedCount int       `json:"deleted_count"`
}

type HeatRecord struct {
	Path       string    `json:"path"`
	ReadCount  int64     `json:"read_count"`
	WriteCount int64     `json:"write_count"`
	LastAccess time.Time `json:"last_access"`
	HeatLevel  string    `json:"heat_level"`
}

type HealthScore struct {
	Timestamp   time.Time         `json:"timestamp"`
	TotalScore  float64           `json:"total_score"`
	Grade       string            `json:"grade"`
	Dimensions  []HealthDimension `json:"dimensions"`
	Suggestions []string          `json:"suggestions"`
}

type HealthDimension struct {
	Name        string  `json:"name"`
	Score       float64 `json:"score"`
	Weight      float64 `json:"weight"`
	Description string  `json:"description"`
	Status      string  `json:"status"`
}
