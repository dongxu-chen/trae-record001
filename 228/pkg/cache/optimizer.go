package cache

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"docker-build-accelerator/pkg/parser"
)

type CachePrediction struct {
	CommandIndex   int
	Command        *parser.DockerCommand
	CacheHit       bool
	Confidence     float64
	Reason         string
	LayerHash      string
	FileChanges    []string
	FileHashes     map[string]string
	PreviousLayers []string
	CombinedHash   string
}

type CacheOptimizer struct {
	BuildContext     string
	CacheDBPath      string
	CacheDB          *CacheDatabase
	ParsedDockerfile *parser.ParsedDockerfile
	mu               sync.RWMutex
}

type CacheRecord struct {
	LayerHash     string            `json:"layer_hash"`
	Command       string            `json:"command"`
	CommandType   string            `json:"command_type"`
	Size          int64             `json:"size"`
	DurationMs    int64             `json:"duration_ms"`
	CreatedAt     int64             `json:"created_at"`
	ContextFiles  map[string]string `json:"context_files"`
	EnvVariables  map[string]string `json:"env_variables"`
	CombinedHash  string            `json:"combined_hash"`
	PreviousLayer string            `json:"previous_layer"`
}

type CacheDatabase struct {
	Records map[string]*CacheRecord `json:"records"`
}

func NewCacheOptimizer(buildContext string, pdf *parser.ParsedDockerfile) (*CacheOptimizer, error) {
	cacheDBPath := filepath.Join(buildContext, ".cache-db.json")
	db, err := loadCacheDB(cacheDBPath)
	if err != nil {
		return nil, err
	}

	return &CacheOptimizer{
		BuildContext:     buildContext,
		CacheDBPath:      cacheDBPath,
		CacheDB:          db,
		ParsedDockerfile: pdf,
	}, nil
}

func loadCacheDB(path string) (*CacheDatabase, error) {
	db := &CacheDatabase{
		Records: make(map[string]*CacheRecord),
	}

	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return db, nil
		}
		return nil, err
	}

	if err := json.Unmarshal(data, db); err != nil {
		return db, nil
	}

	return db, nil
}

func (co *CacheOptimizer) SaveCacheDB() error {
	co.mu.Lock()
	defer co.mu.Unlock()

	data, err := json.MarshalIndent(co.CacheDB, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(co.CacheDBPath, data, 0644)
}

func (co *CacheOptimizer) AddRecord(layerHash string, record *CacheRecord) {
	co.mu.Lock()
	defer co.mu.Unlock()
	co.CacheDB.Records[layerHash] = record
}

func (co *CacheOptimizer) PredictCacheHits(stage *parser.BuildStage) ([]*CachePrediction, error) {
	var predictions []*CachePrediction
	var previousLayers []string
	envVariables := make(map[string]string)
	previousLayer := ""

	for i, cmd := range stage.Commands {
		prediction := &CachePrediction{
			CommandIndex:   i,
			Command:        cmd,
			PreviousLayers: append([]string{}, previousLayers...),
			FileHashes:     make(map[string]string),
		}

		var contextFiles map[string]string
		var err error

		switch cmd.Type {
		case parser.CmdFrom:
			prediction = co.handleFrom(cmd, prediction)
			contextFiles = make(map[string]string)
		case parser.CmdRun:
			prediction = co.handleRun(cmd, prediction, envVariables)
			contextFiles = make(map[string]string)
		case parser.CmdCopy, parser.CmdAdd:
			prediction, contextFiles, err = co.handleCopyOrAddWithHash(cmd, prediction)
			if err != nil {
				return nil, err
			}
			prediction.FileHashes = contextFiles
		case parser.CmdEnv:
			prediction = co.handleEnv(cmd, prediction, envVariables)
			contextFiles = make(map[string]string)
		case parser.CmdArg:
			prediction = co.handleArg(cmd, prediction, envVariables)
			contextFiles = make(map[string]string)
		default:
			prediction = co.handleOther(cmd, prediction)
			contextFiles = make(map[string]string)
		}

		if cmd.Type.CreatesLayer() {
			combinedHash := co.calculateCombinedHash(cmd, previousLayer, contextFiles, envVariables)
			prediction.CombinedHash = combinedHash
			prediction.LayerHash = combinedHash

			cacheHit := co.checkCacheHit(combinedHash, cmd, contextFiles, envVariables, previousLayer)
			prediction.CacheHit = cacheHit
			if cacheHit {
				prediction.Confidence = 0.98
				prediction.Reason = "Combined hash matches cached record"
			}

			previousLayer = combinedHash
			previousLayers = append(previousLayers, combinedHash)
		}

		predictions = append(predictions, prediction)
	}

	return predictions, nil
}

func (co *CacheOptimizer) checkCacheHit(combinedHash string, cmd *parser.DockerCommand, 
	contextFiles map[string]string, envVariables map[string]string, previousLayer string) bool {
	co.mu.RLock()
	defer co.mu.RUnlock()

	record, exists := co.CacheDB.Records[combinedHash]
	if !exists {
		return false
	}

	if record.Command != cmd.Original {
		return false
	}

	if record.PreviousLayer != previousLayer {
		return false
	}

	for path, hash := range contextFiles {
		if record.ContextFiles[path] != hash {
			return false
		}
	}

	return true
}

func (co *CacheOptimizer) calculateCombinedHash(cmd *parser.DockerCommand, previousLayer string,
	contextFiles map[string]string, envVariables map[string]string) string {
	hasher := sha256.New()

	hasher.Write([]byte(cmd.Original))
	hasher.Write([]byte(previousLayer))

	for path, hash := range contextFiles {
		hasher.Write([]byte(path + ":" + hash + "|"))
	}

	keys := make([]string, 0, len(envVariables))
	for k := range envVariables {
		keys = append(keys, k)
	}
	for _, k := range keys {
		hasher.Write([]byte(fmt.Sprintf("%s=%s|", k, envVariables[k])))
	}

	return hex.EncodeToString(hasher.Sum(nil))
}

func (co *CacheOptimizer) handleFrom(cmd *parser.DockerCommand, prediction *CachePrediction) *CachePrediction {
	image := strings.Fields(cmd.Args)[0]
	prediction.CacheHit = true
	prediction.Confidence = 0.95
	prediction.Reason = fmt.Sprintf("Base image %s is likely cached locally", image)
	return prediction
}

func (co *CacheOptimizer) handleRun(cmd *parser.DockerCommand, prediction *CachePrediction, env map[string]string) *CachePrediction {
	command := cmd.Args
	
	if strings.Contains(command, "apt-get update") || 
	   strings.Contains(command, "yum update") ||
	   strings.Contains(command, "apk update") ||
	   strings.Contains(command, "pip install") ||
	   strings.Contains(command, "npm install") {
		prediction.CacheHit = false
		prediction.Confidence = 0.8
		prediction.Reason = "Package manager commands frequently update packages, breaking cache"
		return prediction
	}

	if strings.Contains(command, "curl") || 
	   strings.Contains(command, "wget") ||
	   strings.Contains(command, "git clone") {
		prediction.CacheHit = false
		prediction.Confidence = 0.7
		prediction.Reason = "Network commands may fetch updated resources"
		return prediction
	}

	prediction.CacheHit = true
	prediction.Confidence = 0.85
	prediction.Reason = "RUN command content unchanged"
	return prediction
}

func (co *CacheOptimizer) handleCopyOrAddWithHash(cmd *parser.DockerCommand, prediction *CachePrediction) (*CachePrediction, map[string]string, error) {
	srcFiles, err := co.extractSourceFiles(cmd.Args)
	if err != nil {
		prediction.CacheHit = false
		prediction.Confidence = 0.5
		prediction.Reason = "Cannot analyze source files"
		return prediction, make(map[string]string), err
	}

	fileHashes := make(map[string]string)
	var changedFiles []string

	for _, src := range srcFiles {
		hash, err := co.calculateFileHash(src)
		if err != nil {
			changedFiles = append(changedFiles, src+" (error)")
			continue
		}
		fileHashes[src] = hash
	}

	prediction.FileHashes = fileHashes
	prediction.FileChanges = changedFiles

	if len(changedFiles) > 0 {
		prediction.Reason = fmt.Sprintf("Source files changed: %s", strings.Join(changedFiles, ", "))
	} else {
		prediction.Reason = "All source file hashes computed"
	}

	return prediction, fileHashes, nil
}

func (co *CacheOptimizer) calculateFileHash(path string) (string, error) {
	fullPath := filepath.Join(co.BuildContext, path)
	
	info, err := os.Stat(fullPath)
	if err != nil {
		return "", err
	}

	if info.IsDir() {
		return co.calculateDirHash(fullPath)
	}

	return co.calculateSingleFileHash(fullPath)
}

func (co *CacheOptimizer) calculateSingleFileHash(path string) (string, error) {
	file, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer file.Close()

	hasher := sha256.New()
	if _, err := io.Copy(hasher, file); err != nil {
		return "", err
	}

	return hex.EncodeToString(hasher.Sum(nil)), nil
}

func (co *CacheOptimizer) calculateDirHash(dirPath string) (string, error) {
	hasher := sha256.New()

	err := filepath.Walk(dirPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		relPath, err := filepath.Rel(dirPath, path)
		if err != nil {
			return err
		}

		hasher.Write([]byte(relPath))
		hasher.Write([]byte(fmt.Sprintf("%d", info.Size())))
		hasher.Write([]byte(fmt.Sprintf("%d", info.Mode())))

		if !info.IsDir() {
			fileHash, err := co.calculateSingleFileHash(path)
			if err != nil {
				return err
			}
			hasher.Write([]byte(fileHash))
		}

		return nil
	})

	if err != nil {
		return "", err
	}

	return hex.EncodeToString(hasher.Sum(nil)), nil
}

func (co *CacheOptimizer) handleEnv(cmd *parser.DockerCommand, prediction *CachePrediction, env map[string]string) *CachePrediction {
	parts := strings.Fields(cmd.Args)
	if len(parts) >= 2 {
		key := parts[0]
		value := strings.Join(parts[1:], " ")
		env[key] = value
	}
	prediction.CacheHit = true
	prediction.Confidence = 0.9
	prediction.Reason = "ENV command typically caches well unless value changes"
	return prediction
}

func (co *CacheOptimizer) handleArg(cmd *parser.DockerCommand, prediction *CachePrediction, env map[string]string) *CachePrediction {
	prediction.CacheHit = false
	prediction.Confidence = 0.6
	prediction.Reason = "ARG values can be overridden at build time, cache is uncertain"
	return prediction
}

func (co *CacheOptimizer) handleOther(cmd *parser.DockerCommand, prediction *CachePrediction) *CachePrediction {
	prediction.CacheHit = true
	prediction.Confidence = 0.95
	prediction.Reason = fmt.Sprintf("%s command rarely invalidates cache", cmd.Type)
	return prediction
}

func (co *CacheOptimizer) extractSourceFiles(args string) ([]string, error) {
	var sources []string
	parts := strings.Fields(args)
	
	for i, part := range parts {
		if strings.HasPrefix(part, "--from=") {
			continue
		}
		if strings.HasPrefix(part, "--chown=") || strings.HasPrefix(part, "--chmod=") {
			continue
		}
		if i == len(parts)-1 {
			break
		}
		sources = append(sources, part)
	}

	return sources, nil
}



func (co *CacheOptimizer) GetOptimizationReport(stage *parser.BuildStage) (*CacheReport, error) {
	predictions, err := co.PredictCacheHits(stage)
	if err != nil {
		return nil, err
	}

	report := &CacheReport{
		StageName:        stage.Name,
		TotalCommands:    len(predictions),
		ExpectedCacheHits: 0,
		EstimatedTimeSavedMs: 0,
		Recommendations:  []string{},
		LayerPredictions: predictions,
	}

	var highRiskCommands []string
	for _, p := range predictions {
		if p.CacheHit {
			report.ExpectedCacheHits++
			report.EstimatedTimeSavedMs += 5000
		} else {
			if p.Command.Type.CreatesLayer() {
				highRiskCommands = append(highRiskCommands, 
					fmt.Sprintf("Line %d: %s", p.Command.LineNumber, p.Reason))
			}
		}
	}

	if len(highRiskCommands) > 0 {
		report.Recommendations = append(report.Recommendations,
			"Consider reordering high-risk cache commands to the end of the Dockerfile")
		report.Recommendations = append(report.Recommendations, highRiskCommands...)
	}

	report.CacheHitRate = float64(report.ExpectedCacheHits) / float64(report.TotalCommands)

	return report, nil
}

type CacheReport struct {
	StageName            string
	TotalCommands        int
	ExpectedCacheHits    int
	CacheHitRate         float64
	EstimatedTimeSavedMs int64
	Recommendations      []string
	LayerPredictions     []*CachePrediction
}

func (cr *CacheReport) Print() {
	fmt.Printf("\n=== Cache Optimization Report for %s ===\n", cr.StageName)
	fmt.Printf("Total Commands: %d\n", cr.TotalCommands)
	fmt.Printf("Expected Cache Hits: %d (%.1f%%)\n", cr.ExpectedCacheHits, cr.CacheHitRate*100)
	fmt.Printf("Estimated Time Saved: ~%.1f seconds\n", float64(cr.EstimatedTimeSavedMs)/1000)
	
	fmt.Println("\nLayer Details (with Combined Hash):")
	for _, p := range cr.LayerPredictions {
		if p.Command.Type.CreatesLayer() {
			cacheIcon := "✗"
			if p.CacheHit {
				cacheIcon = "✓"
			}
			hashDisplay := p.CombinedHash
			if len(hashDisplay) > 16 {
				hashDisplay = hashDisplay[:16] + "..."
			}
			fmt.Printf("  %s [%s] Line %d: %s - Hash: %s\n", 
				cacheIcon, p.Command.Type, p.Command.LineNumber, p.Reason, hashDisplay)
			
			if len(p.FileHashes) > 0 {
				fmt.Printf("      File Hashes:\n")
				for path, hash := range p.FileHashes {
					if len(hash) > 12 {
						hash = hash[:12] + "..."
					}
					fmt.Printf("        %s: %s\n", path, hash)
				}
			}
		}
	}
	
	if len(cr.Recommendations) > 0 {
		fmt.Println("\nRecommendations:")
		for _, rec := range cr.Recommendations {
			fmt.Printf("  - %s\n", rec)
		}
	}
}
