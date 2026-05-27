package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"regexp"
	"sort"
	"strings"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

type Config struct {
	MongoURI           string
	Database           string
	Collection         string
	ThresholdMS        int
	MaxRecommendations int
}

type SlowQueryLog struct {
	Timestamp    time.Time
	DurationMS   int
	Namespace    string
	Database     string
	Operation    string
	Query        map[string]interface{}
	Projection   map[string]interface{}
	Sort         map[string]interface{}
	ExaminedDocs int64
	ReturnedDocs int64
	KeysExamined int64
}

type QueryPattern struct {
	Collection    string
	FilterFields  []string
	SortFields    []string
	Operation     string
	Count         int
	TotalDuration int64
	AvgDuration   float64
	MaxDuration   int64
	TotalExamined int64
	TotalReturned int64
	Queries       []*SlowQueryLog
}

type IndexRecommendation struct {
	Collection         string
	Keys               map[string]int
	Name               string
	Type               string
	BenefitScore       float64
	EstimatedSizeBytes int64
	CurrentScanDocs    int64
	EstimatedScanDocs  int64
	QueryPatterns      []*QueryPattern
	CreateCommand      string
	PartialFilter      map[string]interface{}
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

func DefaultConfig() *Config {
	return &Config{
		MongoURI:           "mongodb://localhost:27017",
		ThresholdMS:        100,
		MaxRecommendations: 10,
	}
}

type MongoClient struct {
	client *mongo.Client
	db     *mongo.Database
}

func NewMongoClient(cfg *Config) (*MongoClient, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	clientOpts := options.Client().ApplyURI(cfg.MongoURI)
	client, err := mongo.Connect(ctx, clientOpts)
	if err != nil {
		return nil, fmt.Errorf("connect failed: %w", err)
	}
	if err := client.Ping(ctx, nil); err != nil {
		return nil, fmt.Errorf("ping failed: %w", err)
	}
	var db *mongo.Database
	if cfg.Database != "" {
		db = client.Database(cfg.Database)
	}
	return &MongoClient{client: client, db: db}, nil
}

func (c *MongoClient) Close() error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	return c.client.Disconnect(ctx)
}

func (c *MongoClient) GetDatabase(name string) *mongo.Database {
	if name == "" {
		return c.db
	}
	return c.client.Database(name)
}

func parseLogLine(logLine string, thresholdMS int) (*SlowQueryLog, error) {
	if !strings.Contains(logLine, "Slow query") || !strings.Contains(logLine, "ms") {
		return nil, nil
	}
	durationRe := regexp.MustCompile(`(\d+)ms`)
	matches := durationRe.FindStringSubmatch(logLine)
	if len(matches) < 2 {
		return nil, fmt.Errorf("no duration")
	}
	duration, _ := time.ParseDuration(matches[1] + "ms")
	durationMS := int(duration.Milliseconds())
	if durationMS < thresholdMS {
		return nil, nil
	}
	nsRe := regexp.MustCompile(`ns (\S+)`)
	nsMatches := nsRe.FindStringSubmatch(logLine)
	namespace := ""
	if len(nsMatches) >= 2 {
		namespace = nsMatches[1]
	}
	parts := strings.SplitN(namespace, ".", 2)
	database := ""
	collection := namespace
	if len(parts) == 2 {
		database = parts[0]
		collection = parts[1]
	}
	opRe := regexp.MustCompile(`op (\w+)`)
	opMatches := opRe.FindStringSubmatch(logLine)
	operation := ""
	if len(opMatches) >= 2 {
		operation = opMatches[1]
	}
	query := parseQueryField(logLine, `query:({.*?})`)
	sort := parseQueryField(logLine, `sort:({.*?})`)
	projection := parseQueryField(logLine, `projection:({.*?})`)
	docsExaminedRe := regexp.MustCompile(`docsExamined:(\d+)`)
	docsExaminedMatches := docsExaminedRe.FindStringSubmatch(logLine)
	keysExaminedRe := regexp.MustCompile(`keysExamined:(\d+)`)
	keysExaminedMatches := keysExaminedRe.FindStringSubmatch(logLine)
	nreturnedRe := regexp.MustCompile(`nreturned:(\d+)`)
	nreturnedMatches := nreturnedRe.FindStringSubmatch(logLine)
	return &SlowQueryLog{
		Timestamp:    time.Now(),
		DurationMS:   durationMS,
		Namespace:    collection,
		Database:     database,
		Operation:    operation,
		Query:        query,
		Sort:         sort,
		Projection:   projection,
		ExaminedDocs: parseInt64(docsExaminedMatches),
		KeysExamined: parseInt64(keysExaminedMatches),
		ReturnedDocs: parseInt64(nreturnedMatches),
	}, nil
}

func parseQueryField(logLine, pattern string) map[string]interface{} {
	re := regexp.MustCompile(pattern)
	matches := re.FindStringSubmatch(logLine)
	if len(matches) >= 2 {
		result := make(map[string]interface{})
		err := json.Unmarshal([]byte(matches[1]), &result)
		if err == nil {
			return result
		}
	}
	return nil
}

func parseInt64(matches []string) int64 {
	if len(matches) >= 2 {
		var result int64
		fmt.Sscanf(matches[1], "%d", &result)
		return result
	}
	return 0
}

func (c *MongoClient) GetSlowQueries(ctx context.Context, dbName string, thresholdMS int) ([]*SlowQueryLog, error) {
	db := c.GetDatabase(dbName)
	var result bson.M
	err := db.RunCommand(ctx, bson.D{{Key: "getLog", Value: "global"}}).Decode(&result)
	if err != nil {
		return nil, fmt.Errorf("getLog failed: %w", err)
	}
	logs, ok := result["log"].(bson.A)
	if !ok {
		return nil, fmt.Errorf("unexpected log format")
	}
	var slowQueries []*SlowQueryLog
	for _, logEntry := range logs {
		if logStr, ok := logEntry.(string); ok {
			parsed, err := parseLogLine(logStr, thresholdMS)
			if err == nil && parsed != nil {
				if dbName == "" || parsed.Database == dbName {
					slowQueries = append(slowQueries, parsed)
				}
			}
		}
	}
	return slowQueries, nil
}

func (c *MongoClient) GetCollectionStats(ctx context.Context, dbName, collName string) (*CollectionStats, error) {
	db := c.GetDatabase(dbName)
	var stats bson.M
	err := db.RunCommand(ctx, bson.D{{Key: "collStats", Value: collName}}).Decode(&stats)
	if err != nil {
		return nil, fmt.Errorf("collStats failed: %w", err)
	}
	result := &CollectionStats{
		Name:       collName,
		Count:      getInt64(stats, "count"),
		SizeBytes:  getInt64(stats, "size"),
		AvgDocSize: getInt64(stats, "avgObjSize"),
	}
	if indexes, ok := stats["indexDetails"].(bson.M); ok {
		for name, idxDetails := range indexes {
			if idxMap, ok := idxDetails.(bson.M); ok {
				idxInfo := IndexInfo{Name: name}
				if key, ok := idxMap["key"].(bson.M); ok {
					idxInfo.Keys = make(map[string]int)
					for k, v := range key {
						idxInfo.Keys[k] = getInt(v)
					}
				}
				result.Indexes = append(result.Indexes, idxInfo)
			}
		}
	}
	if indexSizes, ok := stats["indexSizes"].(bson.M); ok {
		for i := range result.Indexes {
			if size, ok := indexSizes[result.Indexes[i].Name].(int32); ok {
				result.Indexes[i].SizeBytes = int64(size)
			} else if size, ok := indexSizes[result.Indexes[i].Name].(int64); ok {
				result.Indexes[i].SizeBytes = size
			}
		}
	}
	return result, nil
}

func getInt64(m bson.M, key string) int64 {
	if v, ok := m[key]; ok {
		switch val := v.(type) {
		case int32:
			return int64(val)
		case int64:
			return val
		case float64:
			return int64(val)
		}
	}
	return 0
}

func getInt(v interface{}) int {
	switch val := v.(type) {
	case int:
		return val
	case int32:
		return int(val)
	case int64:
		return int(val)
	case float64:
		return int(val)
	}
	return 0
}

type Analyzer struct {
	patterns map[string]*QueryPattern
}

func NewAnalyzer() *Analyzer {
	return &Analyzer{patterns: make(map[string]*QueryPattern)}
}

func (a *Analyzer) AddQuery(query *SlowQueryLog) {
	filterFields := extractFields(query.Query)
	sortFields := extractFields(query.Sort)
	key := query.Namespace + ":" + query.Operation + ":" + strings.Join(filterFields, ",") + ":" + strings.Join(sortFields, ",")
	if pattern, exists := a.patterns[key]; !exists {
		a.patterns[key] = &QueryPattern{
			Collection:    query.Namespace,
			Operation:     query.Operation,
			FilterFields:  filterFields,
			SortFields:    sortFields,
			Count:         1,
			TotalDuration: int64(query.DurationMS),
			MaxDuration:   int64(query.DurationMS),
			TotalExamined: query.ExaminedDocs,
			TotalReturned: query.ReturnedDocs,
			Queries:       []*SlowQueryLog{query},
		}
	} else {
		pattern.Count++
		pattern.TotalDuration += int64(query.DurationMS)
		if int64(query.DurationMS) > pattern.MaxDuration {
			pattern.MaxDuration = int64(query.DurationMS)
		}
		pattern.TotalExamined += query.ExaminedDocs
		pattern.TotalReturned += query.ReturnedDocs
		pattern.Queries = append(pattern.Queries, query)
	}
}

func (a *Analyzer) GetPatterns() []*QueryPattern {
	patterns := make([]*QueryPattern, 0, len(a.patterns))
	for _, p := range a.patterns {
		if p.Count > 0 {
			p.AvgDuration = float64(p.TotalDuration) / float64(p.Count)
		}
		patterns = append(patterns, p)
	}
	sort.Slice(patterns, func(i, j int) bool {
		return patterns[i].TotalDuration > patterns[j].TotalDuration
	})
	return patterns
}

func extractFields(m map[string]interface{}) []string {
	var fields []string
	for field := range m {
		fields = append(fields, field)
	}
	sort.Strings(fields)
	return fields
}

type Recommender struct {
	maxRecommendations int
}

func NewRecommender(maxRecs int) *Recommender {
	return &Recommender{maxRecommendations: maxRecs}
}

func (r *Recommender) Recommend(patterns []*QueryPattern, existingIndexes []IndexInfo) []*IndexRecommendation {
	candidateMap := make(map[string]*IndexRecommendation)
	for _, pattern := range patterns {
		recs := r.generateForPattern(pattern)
		for _, rec := range recs {
			key := rec.Name
			if existing, ok := candidateMap[key]; !ok {
				candidateMap[key] = rec
			} else {
				existing.QueryPatterns = append(existing.QueryPatterns, pattern)
				existing.BenefitScore += r.calcBenefit(pattern)
				existing.CurrentScanDocs += pattern.TotalExamined
			}
		}
	}
	candidates := make([]*IndexRecommendation, 0, len(candidateMap))
	for _, rec := range candidateMap {
		rec.EstimatedScanDocs = r.estimateScan(rec)
		candidates = append(candidates, rec)
	}
	sort.Slice(candidates, func(i, j int) bool {
		return candidates[i].BenefitScore > candidates[j].BenefitScore
	})
	filtered := r.filterExisting(candidates, existingIndexes)
	if len(filtered) > r.maxRecommendations {
		filtered = filtered[:r.maxRecommendations]
	}
	return filtered
}

func (r *Recommender) generateForPattern(pattern *QueryPattern) []*IndexRecommendation {
	var recs []*IndexRecommendation
	if len(pattern.FilterFields) == 0 && len(pattern.SortFields) == 0 {
		return recs
	}
	keys := make(map[string]int)
	for _, f := range pattern.FilterFields {
		keys[f] = 1
	}
	for _, f := range pattern.SortFields {
		keys[f] = 1
	}
	name := genIndexName(keys)
	recs = append(recs, &IndexRecommendation{
		Collection:      pattern.Collection,
		Keys:            keys,
		Name:            name,
		Type:            "compound",
		BenefitScore:    r.calcBenefit(pattern),
		CurrentScanDocs: pattern.TotalExamined,
		QueryPatterns:   []*QueryPattern{pattern},
		CreateCommand:   genCreateCmd(pattern.Collection, keys, nil),
	})
	if len(pattern.Queries) > 0 {
		if pf := r.identifyPartial(pattern.Queries[0].Query); pf != nil {
			pname := name + "_partial"
			recs = append(recs, &IndexRecommendation{
				Collection:      pattern.Collection,
				Keys:            keys,
				Name:            pname,
				Type:            "partial",
				BenefitScore:    r.calcBenefit(pattern) * 1.5,
				CurrentScanDocs: pattern.TotalExamined,
				QueryPatterns:   []*QueryPattern{pattern},
				PartialFilter:   pf,
				CreateCommand:   genCreateCmd(pattern.Collection, keys, pf),
			})
		}
	}
	return recs
}

func (r *Recommender) identifyPartial(query map[string]interface{}) map[string]interface{} {
	for field, value := range query {
		if m, ok := value.(map[string]interface{}); ok {
			for op := range m {
				if op == "$exists" || op == "$gte" || op == "$gt" || op == "$lte" || op == "$lt" {
					return map[string]interface{}{field: value}
				}
			}
		}
	}
	return nil
}

func (r *Recommender) calcBenefit(p *QueryPattern) float64 {
	score := float64(p.TotalDuration)
	if p.TotalExamined > 0 && p.TotalReturned > 0 {
		ratio := float64(p.TotalExamined) / float64(p.TotalReturned)
		score *= ratio
	}
	score *= float64(p.Count)
	return score
}

func (r *Recommender) estimateScan(rec *IndexRecommendation) int64 {
	if rec.CurrentScanDocs == 0 {
		return 0
	}
	if len(rec.Keys) >= 2 {
		return int64(float64(rec.CurrentScanDocs) * 0.1)
	}
	return int64(float64(rec.CurrentScanDocs) * 0.3)
}

func (r *Recommender) filterExisting(candidates []*IndexRecommendation, existing []IndexInfo) []*IndexRecommendation {
	var filtered []*IndexRecommendation
	for _, c := range candidates {
		exists := false
		for _, e := range existing {
			if indexesEqual(c.Keys, e.Keys) {
				exists = true
				break
			}
		}
		if !exists {
			filtered = append(filtered, c)
		}
	}
	return filtered
}

func indexesEqual(a, b map[string]int) bool {
	if len(a) != len(b) {
		return false
	}
	for k, v := range a {
		if b[k] != v {
			return false
		}
	}
	return true
}

func genIndexName(keys map[string]int) string {
	var parts []string
	for field, dir := range keys {
		if dir == 1 {
			parts = append(parts, field+"_1")
		} else {
			parts = append(parts, field+"_-1")
		}
	}
	sort.Strings(parts)
	return strings.Join(parts, "_")
}

func genCreateCmd(collection string, keys map[string]int, partialFilter map[string]interface{}) string {
	keysJSON, _ := json.Marshal(keys)
	if partialFilter != nil {
		filterJSON, _ := json.Marshal(partialFilter)
		return fmt.Sprintf(`db.%s.createIndex(%s, { partialFilterExpression: %s })`, collection, keysJSON, filterJSON)
	}
	return fmt.Sprintf(`db.%s.createIndex(%s)`, collection, keysJSON)
}

type Evaluator struct {
	client *MongoClient
}

func NewEvaluator(client *MongoClient) *Evaluator {
	return &Evaluator{client: client}
}

func (e *Evaluator) EstimateSize(ctx context.Context, dbName string, rec *IndexRecommendation, collStats *CollectionStats) int64 {
	if collStats == nil || collStats.Count == 0 {
		return 0
	}
	numFields := len(rec.Keys)
	avgKeySize := int64(64 * numFields)
	if collStats.AvgDocSize > 0 {
		avgKeySize = int64(float64(collStats.AvgDocSize) * 0.15 * float64(numFields))
	}
	total := avgKeySize * collStats.Count
	if rec.PartialFilter != nil {
		total = int64(float64(total) * 0.3)
	}
	return total
}

func (e *Evaluator) CalcImprovement(current, estimated int64) float64 {
	if current == 0 {
		return 0
	}
	return float64(current-estimated) / float64(current) * 100
}

func FormatBytes(bytes int64) string {
	const KB = 1024
	const MB = KB * 1024
	const GB = MB * 1024
	switch {
	case bytes >= GB:
		return fmt.Sprintf("%.2f GB", float64(bytes)/float64(GB))
	case bytes >= MB:
		return fmt.Sprintf("%.2f MB", float64(bytes)/float64(MB))
	case bytes >= KB:
		return fmt.Sprintf("%.2f KB", float64(bytes)/float64(KB))
	default:
		return fmt.Sprintf("%d bytes", bytes)
	}
}

func main() {
	mongoURI := flag.String("uri", "mongodb://localhost:27017", "MongoDB URI")
	dbName := flag.String("db", "", "Database name")
	collName := flag.String("collection", "", "Collection name")
	threshold := flag.Int("threshold", 100, "Slow query threshold ms")
	maxRecs := flag.Int("max-recs", 10, "Max recommendations")
	outputFile := flag.String("output", "", "Output file")
	flag.Parse()

	cfg := DefaultConfig()
	cfg.MongoURI = *mongoURI
	cfg.Database = *dbName
	cfg.Collection = *collName
	cfg.ThresholdMS = *threshold
	cfg.MaxRecommendations = *maxRecs

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	log.Println("Connecting to MongoDB...")
	client, err := NewMongoClient(cfg)
	if err != nil {
		log.Fatalf("Connection failed: %v", err)
	}
	defer client.Close()
	log.Println("Connected")

	log.Println("Collecting slow queries...")
	slowQueries, err := client.GetSlowQueries(ctx, cfg.Database, cfg.ThresholdMS)
	if err != nil {
		log.Printf("Warning: %v", err)
	}
	log.Printf("Found %d slow queries", len(slowQueries))

	analyzer := NewAnalyzer()
	for _, q := range slowQueries {
		analyzer.AddQuery(q)
	}

	patterns := analyzer.GetPatterns()
	log.Printf("Identified %d query patterns", len(patterns))

	for i, p := range patterns {
		log.Printf("Pattern %d: %s %s count=%d avg=%.2fms",
			i+1, p.Collection, p.FilterFields, p.Count, p.AvgDuration)
	}

	log.Println("\nGenerating recommendations...")

	var existingIndexes []IndexInfo
	if cfg.Collection != "" {
		stats, err := client.GetCollectionStats(ctx, cfg.Database, cfg.Collection)
		if err != nil {
			log.Printf("Warning: %v", err)
		} else {
			existingIndexes = stats.Indexes
		}
	}

	rec := NewRecommender(cfg.MaxRecommendations)
	recommendations := rec.Recommend(patterns, existingIndexes)

	eval := NewEvaluator(client)

	var output strings.Builder
	output.WriteString("=== MongoDB Index Recommendations ===\n\n")

	for i, r := range recommendations {
		var collStats *CollectionStats
		if cfg.Database != "" {
			collStats, _ = client.GetCollectionStats(ctx, cfg.Database, r.Collection)
		}

		r.EstimatedSizeBytes = eval.EstimateSize(ctx, cfg.Database, r, collStats)
		improvement := eval.CalcImprovement(r.CurrentScanDocs, r.EstimatedScanDocs)

		output.WriteString(fmt.Sprintf("\n--- Recommendation %d ---\n", i+1))
		output.WriteString(fmt.Sprintf("Collection: %s\n", r.Collection))
		output.WriteString(fmt.Sprintf("Type: %s\n", r.Type))
		output.WriteString(fmt.Sprintf("Index Keys: %v\n", r.Keys))
		output.WriteString(fmt.Sprintf("Index Name: %s\n", r.Name))
		output.WriteString(fmt.Sprintf("Benefit Score: %.2f\n", r.BenefitScore))
		output.WriteString(fmt.Sprintf("Estimated Size: %s\n", FormatBytes(r.EstimatedSizeBytes)))
		output.WriteString(fmt.Sprintf("Current Scan Docs: %d\n", r.CurrentScanDocs))
		output.WriteString(fmt.Sprintf("Estimated Scan Docs: %d\n", r.EstimatedScanDocs))
		output.WriteString(fmt.Sprintf("Estimated Improvement: %.2f%%\n", improvement))
		output.WriteString(fmt.Sprintf("Create Command:\n  %s\n", r.CreateCommand))
		output.WriteString(fmt.Sprintf("Affected Query Patterns: %d\n", len(r.QueryPatterns)))
	}

	if *outputFile != "" {
		err := os.WriteFile(*outputFile, []byte(output.String()), 0644)
		if err != nil {
			log.Fatalf("Write failed: %v", err)
		}
		log.Printf("Written to %s", *outputFile)
	}

	fmt.Println(output.String())
	log.Println("\nDone!")
}
