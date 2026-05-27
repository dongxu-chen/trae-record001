package models

import "time"

type SlowQueryLog struct {
	Timestamp    time.Time
	DurationMS   int
	Namespace    string
	Operation    string
	Query        map[string]interface{}
	Projection   map[string]interface{}
	Sort         map[string]interface{}
	ExaminedDocs int64
	ReturnedDocs int64
	KeysExamined int64
}

type QueryPattern struct {
	Collection       string
	FilterFields     []string
	SortFields       []string
	Operation        string
	Count            int
	TotalDuration    int64
	AvgDuration      float64
	MaxDuration      int64
	TotalExamined    int64
	TotalReturned    int64
	Queries          []*SlowQueryLog
}

type IndexRecommendation struct {
	Collection          string
	Keys                map[string]int
	Name                string
	Type                string
	BenefitScore        float64
	EstimatedSizeBytes  int64
	CurrentScanDocs     int64
	EstimatedScanDocs   int64
	QueryPatterns       []*QueryPattern
	CreateCommand       string
	PartialFilter       map[string]interface{}
}

type CollectionStats struct {
	Name       string
	Count      int64
	SizeBytes  int64
	AvgDocSize int64
	Indexes    []IndexInfo
}

type IndexInfo struct {
	Name      string
	Keys      map[string]int
	SizeBytes int64
}
type IndexInfo struct {
	Name      string
	Keys      map[string]int
	SizeBytes int64
}
