package scenario

import (
	"db-bench/internal/config"
	"db-bench/internal/driver"
	"fmt"
	"math/rand"
	"sync"
	"time"
)

type Generator interface {
	Next() driver.Operation
	Close()
}

type ScenarioGenerator struct {
	cfg               config.ScenarioConfig
	mu                sync.Mutex
	hotspotStartKey   int
	hotspotEndKey     int
	normalStartKey    int
	normalEndKey      int
	readThreshold     float64
	hotspotThreshold  float64
	zipfGenerator     *rand.Zipf
	randomSource      *rand.Rand
}

func NewGenerator(cfg config.ScenarioConfig) (*ScenarioGenerator, error) {
	if cfg.ReadRatio+cfg.WriteRatio != 1.0 {
		return nil, fmt.Errorf("read_ratio + write_ratio must equal 1.0, got %f + %f = %f",
			cfg.ReadRatio, cfg.WriteRatio, cfg.ReadRatio+cfg.WriteRatio)
	}

	if cfg.HotspotPercentage < 0 || cfg.HotspotPercentage > 100 {
		return nil, fmt.Errorf("hotspot_percentage must be between 0 and 100")
	}

	if cfg.HotspotAccessRatio < 0 || cfg.HotspotAccessRatio > 1.0 {
		return nil, fmt.Errorf("hotspot_access_ratio must be between 0 and 1.0")
	}

	hotspotCount := int(float64(cfg.TotalRecords) * cfg.HotspotPercentage / 100.0)
	if hotspotCount == 0 && cfg.HotspotPercentage > 0 {
		hotspotCount = 1
	}

	src := rand.NewSource(time.Now().UnixNano())
	r := rand.New(src)

	var zipf *rand.Zipf
	if hotspotCount > 0 && cfg.HotspotDistribution == config.HotspotZipf {
		s := cfg.HotspotSkew
		if s <= 1.0 {
			s = 1.001
		}
		zipf = rand.NewZipf(r, s, 1.0, uint64(hotspotCount-1))
	}

	gen := &ScenarioGenerator{
		cfg:              cfg,
		hotspotStartKey:  0,
		hotspotEndKey:    hotspotCount - 1,
		normalStartKey:   hotspotCount,
		normalEndKey:     cfg.TotalRecords - 1,
		readThreshold:    cfg.ReadRatio,
		hotspotThreshold: cfg.HotspotAccessRatio,
		zipfGenerator:    zipf,
		randomSource:     r,
	}

	return gen, nil
}

func (g *ScenarioGenerator) Next() driver.Operation {
	g.mu.Lock()
	defer g.mu.Unlock()

	opType := g.generateOpType()
	isHotspot := g.generateHotspot()
	key := g.generateKey(isHotspot)

	var value string
	if opType == driver.OpWrite {
		value = g.generateValue()
	}

	return driver.Operation{
		Type:      opType,
		Key:       key,
		Value:     value,
		IsHotspot: isHotspot,
	}
}

func (g *ScenarioGenerator) generateOpType() driver.OperationType {
	r := rand.Float64()
	if r < g.readThreshold {
		return driver.OpRead
	}
	return driver.OpWrite
}

func (g *ScenarioGenerator) generateHotspot() bool {
	if g.hotspotEndKey < g.hotspotStartKey {
		return false
	}
	r := rand.Float64()
	return r < g.hotspotThreshold
}

func (g *ScenarioGenerator) generateKey(isHotspot bool) int {
	if isHotspot && g.hotspotEndKey >= g.hotspotStartKey {
		hotspotRange := g.hotspotEndKey - g.hotspotStartKey + 1
		if g.zipfGenerator != nil && hotspotRange > 0 {
			idx := g.zipfGenerator.Uint64()
			return g.hotspotStartKey + int(idx)
		}
		return g.randomSource.Intn(hotspotRange) + g.hotspotStartKey
	}

	if g.normalEndKey >= g.normalStartKey {
		return g.randomSource.Intn(g.normalEndKey-g.normalStartKey+1) + g.normalStartKey
	}

	return g.randomSource.Intn(g.cfg.TotalRecords)
}

func (g *ScenarioGenerator) generateValue() string {
	const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	valueLen := 100 + rand.Intn(100)
	b := make([]byte, valueLen)
	for i := range b {
		b[i] = charset[rand.Intn(len(charset))]
	}
	return fmt.Sprintf("val_%d_%s", rand.Int63(), string(b))
}

func (g *ScenarioGenerator) GetConfig() config.ScenarioConfig {
	return g.cfg
}

func (g *ScenarioGenerator) Close() {
}
