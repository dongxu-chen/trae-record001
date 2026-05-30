package proxy

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/prometheus/downsampler/pkg/config"
	"github.com/prometheus/downsampler/pkg/downsampling"
)

type TransparentProxy struct {
	cfg             config.ProxyConfig
	promCfg         config.PrometheusConfig
	rules           []config.MetricRule
	namespace       string
	metricMatchers  map[string]*MetricMatcher
	cache           *QueryCache
	httpClient      *http.Client
}

type MetricMatcher struct {
	rule              config.MetricRule
	metricPattern     *regexp.Regexp
	extractor         *regexp.Regexp
	availableLevels   []config.DownsamplingLevel
	defaultAgg        config.AggregationFunction
}

type QueryCache struct {
	sync.RWMutex
	entries map[string]*CacheEntry
	ttl     time.Duration
}

type CacheEntry struct {
	Data      []byte
	ExpiresAt time.Time
}

type rewriteInfo struct {
	originalQuery  string
	rewrittenQuery string
	level          config.DownsamplingLevel
	aggregation    config.AggregationFunction
	wasRewritten   bool
}

func NewTransparentProxy(
	cfg config.ProxyConfig,
	promCfg config.PrometheusConfig,
	rules []config.MetricRule,
	namespace string,
) (*TransparentProxy, error) {
	matchers := make(map[string]*MetricMatcher)

	for _, rule := range rules {
		matcher, err := buildMetricMatcher(rule)
		if err != nil {
			log.Printf("Warning: failed to build matcher for rule '%s': %v", rule.Name, err)
			continue
		}
		matchers[rule.Name] = matcher
	}

	return &TransparentProxy{
		cfg:            cfg,
		promCfg:        promCfg,
		rules:          rules,
		namespace:      namespace,
		metricMatchers: matchers,
		cache:          newQueryCache(cfg.CacheTTL),
		httpClient: &http.Client{
			Timeout: promCfg.Timeout,
		},
	}, nil
}

func buildMetricMatcher(rule config.MetricRule) (*MetricMatcher, error) {
	metricName := extractMetricName(rule.Match)
	if metricName == "" {
		return nil, fmt.Errorf("could not extract metric name from match pattern")
	}

	pattern := regexp.QuoteMeta(metricName)
	pattern = strings.ReplaceAll(pattern, "\\.\\*", ".*")
	pattern = strings.ReplaceAll(pattern, "\\[.*\\]", ".*")
	pattern = strings.ReplaceAll(pattern, "\\(", "(")
	pattern = strings.ReplaceAll(pattern, "\\)", ")")
	pattern = strings.ReplaceAll(pattern, "\\|", "|")

	metricRegex, err := regexp.Compile(pattern)
	if err != nil {
		return nil, err
	}

	var defaultAgg config.AggregationFunction
	if containsAgg(rule.Aggregations, config.AggAvg) {
		defaultAgg = config.AggAvg
	} else if len(rule.Aggregations) > 0 {
		defaultAgg = rule.Aggregations[0]
	} else {
		defaultAgg = config.AggAvg
	}

	return &MetricMatcher{
		rule:            rule,
		metricPattern:   metricRegex,
		extractor:       regexp.MustCompile(pattern),
		availableLevels: rule.DownsamplingLevels,
		defaultAgg:      defaultAgg,
	}, nil
}

func containsAgg(aggs []config.AggregationFunction, target config.AggregationFunction) bool {
	for _, a := range aggs {
		if a == target {
			return true
		}
	}
	return false
}

func extractMetricName(match string) string {
	if strings.HasPrefix(match, "{") && strings.HasSuffix(match, "}") {
		inner := match[1 : len(match)-1]
		parts := strings.Split(inner, ",")
		for _, part := range parts {
			part = strings.TrimSpace(part)
			if strings.HasPrefix(part, "__name__") {
				kv := strings.SplitN(part, "=", 2)
				if len(kv) == 2 {
					value := strings.TrimSpace(kv[1])
					value = strings.Trim(value, `"`)
					value = strings.Trim(value, "~")
					value = strings.Trim(value, `"`)
					return value
				}
			}
		}
	}
	return match
}

func newQueryCache(ttl time.Duration) *QueryCache {
	qc := &QueryCache{
		entries: make(map[string]*CacheEntry),
		ttl:     ttl,
	}
	go qc.cleanupLoop()
	return qc
}

func (c *QueryCache) cleanupLoop() {
	ticker := time.NewTicker(time.Minute)
	defer ticker.Stop()

	for range ticker.C {
		c.Lock()
		now := time.Now()
		for key, entry := range c.entries {
			if entry.ExpiresAt.Before(now) {
				delete(c.entries, key)
			}
		}
		c.Unlock()
	}
}

func (c *QueryCache) Get(key string) ([]byte, bool) {
	c.RLock()
	defer c.RUnlock()

	entry, exists := c.entries[key]
	if !exists {
		return nil, false
	}

	if entry.ExpiresAt.Before(time.Now()) {
		return nil, false
	}

	return entry.Data, true
}

func (c *QueryCache) Set(key string, data []byte) {
	c.Lock()
	defer c.Unlock()

	c.entries[key] = &CacheEntry{
		Data:      data,
		ExpiresAt: time.Now().Add(c.ttl),
	}
}

func (p *TransparentProxy) selectOptimalLevel(
	timeRange time.Duration,
	step time.Duration,
	matcher *MetricMatcher,
) config.DownsamplingLevel {
	if len(matcher.availableLevels) == 0 {
		return config.LevelRaw
	}

	var targetLevel config.DownsamplingLevel

	for _, level := range matcher.availableLevels {
		duration, err := level.Duration()
		if err != nil || duration == 0 {
			continue
		}

		if step >= duration {
			targetLevel = level
		}
	}

	if targetLevel == "" {
		if timeRange > 7*24*time.Hour {
			targetLevel = p.findHighestLevel(matcher.availableLevels)
		} else if timeRange > 24*time.Hour {
			targetLevel = p.findLevelByMinDuration(matcher.availableLevels, time.Hour)
		} else if timeRange > 6*time.Hour {
			targetLevel = p.findLevelByMinDuration(matcher.availableLevels, 15*time.Minute)
		} else if timeRange > time.Hour {
			targetLevel = p.findLevelByMinDuration(matcher.availableLevels, time.Minute)
		} else {
			return config.LevelRaw
		}
	}

	return targetLevel
}

func (p *TransparentProxy) findHighestLevel(levels []config.DownsamplingLevel) config.DownsamplingLevel {
	priority := []config.DownsamplingLevel{
		config.LevelDay,
		config.Level6Hours,
		config.LevelHour,
		config.Level15Minutes,
		config.Level5Minutes,
		config.LevelMinute,
	}

	levelSet := make(map[config.DownsamplingLevel]bool)
	for _, l := range levels {
		levelSet[l] = true
	}

	for _, l := range priority {
		if levelSet[l] {
			return l
		}
	}

	return config.LevelRaw
}

func (p *TransparentProxy) findLevelByMinDuration(levels []config.DownsamplingLevel, minDuration time.Duration) config.DownsamplingLevel {
	var bestLevel config.DownsamplingLevel
	var bestDuration time.Duration

	for _, l := range levels {
		d, err := l.Duration()
		if err != nil || d == 0 {
			continue
		}
		if d >= minDuration && (bestDuration == 0 || d < bestDuration) {
			bestDuration = d
			bestLevel = l
		}
	}

	if bestLevel == "" {
		return config.LevelRaw
	}
	return bestLevel
}

func (p *TransparentProxy) rewriteQuery(
	originalQuery string,
	start, end time.Time,
	step time.Duration,
) *rewriteInfo {
	timeRange := end.Sub(start)

	for _, matcher := range p.metricMatchers {
		if !matcher.metricPattern.MatchString(originalQuery) {
			continue
		}

		level := p.selectOptimalLevel(timeRange, step, matcher)
		if level == config.LevelRaw {
			return &rewriteInfo{
				originalQuery: originalQuery,
				wasRewritten:  false,
			}
		}

		matches := matcher.extractor.FindAllString(originalQuery, -1)
		rewritten := originalQuery

		for _, match := range matches {
			dsMetricName := p.buildDownsampledMetricName(match, matcher.defaultAgg, level)

			labels := p.buildLevelLabels(level, matcher.defaultAgg)
			rewritten = strings.ReplaceAll(rewritten, match, dsMetricName+labels)
		}

		return &rewriteInfo{
			originalQuery:  originalQuery,
			rewrittenQuery: rewritten,
			level:          level,
			aggregation:    matcher.defaultAgg,
			wasRewritten:   true,
		}
	}

	return &rewriteInfo{
		originalQuery: originalQuery,
		wasRewritten:  false,
	}
}

func (p *TransparentProxy) buildDownsampledMetricName(
	originalMetric string,
	agg config.AggregationFunction,
	level config.DownsamplingLevel,
) string {
	engine := downsampling.NewEngine(p.namespace)
	return engine.GenerateMetricName(originalMetric, agg, level)
}

func (p *TransparentProxy) buildLevelLabels(level config.DownsamplingLevel, agg config.AggregationFunction) string {
	return fmt.Sprintf(`{ds_level="%s",ds_agg="%s"}`, level, agg)
}

func (p *TransparentProxy) proxyToPrometheus(
	w http.ResponseWriter,
	r *http.Request,
	rewrite *rewriteInfo,
) {
	ctx := r.Context()

	values := r.URL.Query()
	if rewrite.wasRewritten {
		values.Set("query", rewrite.rewrittenQuery)
	}

	requestURL, err := url.Parse(p.promCfg.Address)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	requestURL.Path = r.URL.Path
	requestURL.RawQuery = values.Encode()

	cacheKey := requestURL.String()
	if cached, ok := p.cache.Get(cacheKey); ok && r.Method == http.MethodGet {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("X-Downsampled-Level", string(rewrite.level))
		w.Header().Set("X-Cache", "HIT")
		w.Write(cached)
		return
	}

	proxyReq, err := http.NewRequestWithContext(ctx, r.Method, requestURL.String(), r.Body)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	for key, values := range r.Header {
		for _, v := range values {
			proxyReq.Header.Add(key, v)
		}
	}

	resp, err := p.httpClient.Do(proxyReq)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	for key, values := range resp.Header {
		for _, v := range values {
			w.Header().Add(key, v)
		}
	}

	if rewrite.wasRewritten {
		w.Header().Set("X-Downsampled-Level", string(rewrite.level))
		w.Header().Set("X-Downsampled-Agg", string(rewrite.aggregation))
	} else {
		w.Header().Set("X-Downsampled-Level", "raw")
	}
	w.Header().Set("X-Cache", "MISS")

	w.WriteHeader(resp.StatusCode)
	w.Write(body)

	if resp.StatusCode == http.StatusOK && r.Method == http.MethodGet {
		p.cache.Set(cacheKey, body)
	}
}

func (p *TransparentProxy) HandleQueryRange(w http.ResponseWriter, r *http.Request) {
	if err := r.ParseForm(); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	query := r.FormValue("query")
	startStr := r.FormValue("start")
	endStr := r.FormValue("end")
	stepStr := r.FormValue("step")

	start, err := parseTime(startStr)
	if err != nil {
		start = time.Now().Add(-1 * time.Hour)
	}

	end, err := parseTime(endStr)
	if err != nil {
		end = time.Now()
	}

	step, err := time.ParseDuration(stepStr)
	if err != nil {
		step = time.Minute
	}

	var rewrite *rewriteInfo
	if p.cfg.AutoSelectLevel {
		rewrite = p.rewriteQuery(query, start, end, step)
		if rewrite.wasRewritten {
			log.Printf("Transparent rewrite: '%s' -> '%s' (level: %s)",
				rewrite.originalQuery, rewrite.rewrittenQuery, rewrite.level)
		}
	} else {
		rewrite = &rewriteInfo{originalQuery: query, wasRewritten: false}
	}

	p.proxyToPrometheus(w, r, rewrite)
}

func (p *TransparentProxy) HandleQuery(w http.ResponseWriter, r *http.Request) {
	if err := r.ParseForm(); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	rewrite := &rewriteInfo{
		originalQuery: r.FormValue("query"),
		wasRewritten:  false,
	}

	p.proxyToPrometheus(w, r, rewrite)
}

func parseTime(s string) (time.Time, error) {
	if s == "" {
		return time.Time{}, fmt.Errorf("empty time")
	}

	if f, err := strconv.ParseFloat(s, 64); err == nil {
		sec := int64(f)
		nsec := int64((f - float64(sec)) * 1e9)
		return time.Unix(sec, nsec), nil
	}

	return time.Parse(time.RFC3339, s)
}

func (p *TransparentProxy) HandleStatus(w http.ResponseWriter, r *http.Request) {
	rulesStatus := make([]map[string]interface{}, 0, len(p.rules))
	for name, matcher := range p.metricMatchers {
		levels := make([]string, 0, len(matcher.availableLevels))
		for _, l := range matcher.availableLevels {
			levels = append(levels, string(l))
		}
		rulesStatus = append(rulesStatus, map[string]interface{}{
			"name":               name,
			"match_pattern":      matcher.rule.Match,
			"available_levels":   levels,
			"default_aggregation": string(matcher.defaultAgg),
		})
	}

	status := map[string]interface{}{
		"status":             "running",
		"namespace":          p.namespace,
		"auto_select_level":  p.cfg.AutoSelectLevel,
		"cache_ttl":          p.cfg.CacheTTL.String(),
		"listen_address":     p.cfg.ListenAddress,
		"prometheus_address": p.promCfg.Address,
		"rules_count":        len(p.metricMatchers),
		"rules":              rulesStatus,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(status)
}

func (p *TransparentProxy) Start() error {
	mux := http.NewServeMux()

	mux.HandleFunc("/api/v1/query_range", p.HandleQueryRange)
	mux.HandleFunc("/api/v1/query", p.HandleQuery)
	mux.HandleFunc("/api/v1/status", p.HandleStatus)
	mux.HandleFunc("/api/v1/", func(w http.ResponseWriter, r *http.Request) {
		rewrite := &rewriteInfo{wasRewritten: false}
		p.proxyToPrometheus(w, r, rewrite)
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		rewrite := &rewriteInfo{wasRewritten: false}
		p.proxyToPrometheus(w, r, rewrite)
	})

	log.Printf("Starting transparent query proxy on %s", p.cfg.ListenAddress)
	log.Printf("Proxying to Prometheus: %s", p.promCfg.Address)
	log.Printf("Auto select level: %v", p.cfg.AutoSelectLevel)

	return http.ListenAndServe(p.cfg.ListenAddress, mux)
}
