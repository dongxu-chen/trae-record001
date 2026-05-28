package predictive

import (
	"context"
	"fmt"
	"hash/fnv"
	"io"
	"math"
	"sort"
	"sync"
	"time"

	"github.com/coldstart-optimizer/coldstart/internal/model"
)

type HistoryEntry struct {
	Function    string    `json:"function"`
	Runtime     string    `json:"runtime"`
	ImageRef    string    `json:"image_ref"`
	InvokedAt   time.Time `json:"invoked_at"`
	Region      string    `json:"region"`
	ColdStartMs int64     `json:"cold_start_ms"`
	Node        string    `json:"node"`
}

type FunctionStat struct {
	Function     string
	Runtime      string
	ImageRef     string
	TotalInvokes int64
	LastInvoke   time.Time
	FirstInvoke  time.Time
	HotHours     [24]int
	HotDays      [7]int
	FreqPerDay   float64
	Regions      map[string]int
	Nodes        map[string]int
	AvgColdMs    float64
}

type PredictorConfig struct {
	HotThreshold     float64
	MinInvocations   int64
	LookbackDays     int
	ProbThreshold    float64
	MaxPredictions   int
	DecayFactor      float64
}

func DefaultConfig() PredictorConfig {
	return PredictorConfig{
		HotThreshold:   3.0,
		MinInvocations: 5,
		LookbackDays:   14,
		ProbThreshold:  0.5,
		MaxPredictions: 20,
		DecayFactor:    0.9,
	}
}

type Predictor struct {
	mu      sync.RWMutex
	config  PredictorConfig
	history []HistoryEntry
	stats   map[string]*FunctionStat
}

func NewPredictor(config PredictorConfig) *Predictor {
	return &Predictor{
		config:  config,
		history: make([]HistoryEntry, 0, 1024),
		stats:   make(map[string]*FunctionStat),
	}
}

func (p *Predictor) Add(entry HistoryEntry) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.history = append(p.history, entry)
	key := statKey(entry.Function, entry.Runtime, entry.ImageRef)
	st, ok := p.stats[key]
	if !ok {
		st = &FunctionStat{
			Function: entry.Function,
			Runtime:  entry.Runtime,
			ImageRef: entry.ImageRef,
			Regions:  make(map[string]int),
			Nodes:    make(map[string]int),
		}
		p.stats[key] = st
	}
	st.TotalInvokes++
	if st.FirstInvoke.IsZero() || entry.InvokedAt.Before(st.FirstInvoke) {
		st.FirstInvoke = entry.InvokedAt
	}
	if entry.InvokedAt.After(st.LastInvoke) {
		st.LastInvoke = entry.InvokedAt
	}
	hour := entry.InvokedAt.Hour()
	st.HotHours[hour]++
	day := int(entry.InvokedAt.Weekday())
	st.HotDays[day]++
	if entry.Region != "" {
		st.Regions[entry.Region]++
	}
	if entry.Node != "" {
		st.Nodes[entry.Node]++
	}
	if entry.ColdStartMs > 0 {
		st.AvgColdMs = (st.AvgColdMs*float64(st.TotalInvokes-1) + float64(entry.ColdStartMs)) / float64(st.TotalInvokes)
	}
	if st.TotalInvokes > 0 {
		days := st.LastInvoke.Sub(st.FirstInvoke).Hours() / 24
		if days < 1 {
			days = 1
		}
		st.FreqPerDay = float64(st.TotalInvokes) / days
	}
}

func (p *Predictor) AddBatch(entries []HistoryEntry) {
	for _, e := range entries {
		p.Add(e)
	}
}

func (p *Predictor) LoadFromReader(r io.Reader) error {
	return nil
}

func (p *Predictor) Predict(ctx context.Context) *model.PredictedPreheat {
	p.mu.RLock()
	defer p.mu.RUnlock()

	cutoff := time.Now().AddDate(0, 0, -p.config.LookbackDays)
	var candidates []*FunctionStat
	for _, st := range p.stats {
		if st.LastInvoke.Before(cutoff) {
			continue
		}
		if st.TotalInvokes < p.config.MinInvocations {
			continue
		}
		if st.FreqPerDay < p.config.HotThreshold {
			continue
		}
		candidates = append(candidates, st)
	}

	now := time.Now()
	type scored struct {
		st   *FunctionStat
		rec  model.PredictionRecord
		score float64
	}
	var scoredList []scored
	for _, st := range candidates {
		hoursSinceLast := now.Sub(st.LastInvoke).Hours()
		decay := math.Pow(p.config.DecayFactor, hoursSinceLast/24.0)

		freqScore := st.FreqPerDay / 50.0
		if freqScore > 1.0 {
			freqScore = 1.0
		}

		coldScore := math.Min(st.AvgColdMs/5000.0, 1.0)
		recencyScore := decay

		totalScore := freqScore*0.4 + coldScore*0.35 + recencyScore*0.25
		probability := math.Min(totalScore, 1.0)

		if probability < p.config.ProbThreshold {
			continue
		}

		region := topRegion(st.Regions)
		hotHours := topHours(st.HotHours, 4)

		reason := fmt.Sprintf("freq=%.1f/day avg_cold=%.0fms decayed=%.2f",
			st.FreqPerDay, st.AvgColdMs, decay)

		scoredList = append(scoredList, scored{
			st:    st,
			score: totalScore,
			rec: model.PredictionRecord{
				Function:    st.Function,
				Runtime:     st.Runtime,
				ImageRef:    st.ImageRef,
				Score:       totalScore,
				Probability: probability,
				Reason:      reason,
				Region:      region,
				HotHours:    hotHours,
				LastSeen:    st.LastInvoke,
				FreqPerDay:  st.FreqPerDay,
			},
		})
	}

	sort.SliceStable(scoredList, func(i, k int) bool {
		return scoredList[i].score > scoredList[k].score
	})

	if p.config.MaxPredictions > 0 && len(scoredList) > p.config.MaxPredictions {
		scoredList = scoredList[:p.config.MaxPredictions]
	}

	out := &model.PredictedPreheat{
		GeneratedAt: now,
		Window:      time.Duration(p.config.LookbackDays) * 24 * time.Hour,
		Threshold:   p.config.ProbThreshold,
	}
	for _, s := range scoredList {
		out.Predictions = append(out.Predictions, s.rec)
	}
	return out
}

func (p *Predictor) IsResident(function, runtime, imageRef string) bool {
	p.mu.RLock()
	defer p.mu.RUnlock()
	key := statKey(function, runtime, imageRef)
	st, ok := p.stats[key]
	if !ok {
		return false
	}
	return st.FreqPerDay >= p.config.HotThreshold && st.TotalInvokes >= p.config.MinInvocations
}

func (p *Predictor) Stats() map[string]*FunctionStat {
	p.mu.RLock()
	defer p.mu.RUnlock()
	out := make(map[string]*FunctionStat, len(p.stats))
	for k, v := range p.stats {
		out[k] = v
	}
	return out
}

func (p *Predictor) HistoryCount() int {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return len(p.history)
}

func statKey(function, runtime, imageRef string) string {
	h := fnv.New64a()
	io.WriteString(h, function+"|"+runtime+"|"+imageRef)
	return fmt.Sprintf("%x", h.Sum64())
}

func topRegion(regions map[string]int) string {
	best := ""
	max := 0
	for r, c := range regions {
		if c > max {
			max = c
			best = r
		}
	}
	return best
}

func topHours(hours [24]int, n int) []int {
	type pair struct {
		hour  int
		count int
	}
	var pairs []pair
	for h, c := range hours {
		if c > 0 {
			pairs = append(pairs, pair{hour: h, count: c})
		}
	}
	sort.SliceStable(pairs, func(i, k int) bool { return pairs[i].count > pairs[k].count })
	if n > len(pairs) {
		n = len(pairs)
	}
	out := make([]int, 0, n)
	for i := 0; i < n; i++ {
		out = append(out, pairs[i].hour)
	}
	return out
}
