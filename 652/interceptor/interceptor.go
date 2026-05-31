package interceptor

import (
	"crypto/rand"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"sync"

	"github.com/Shopify/sarama"
)

type MessageInterceptor interface {
	Intercept(msg *sarama.ConsumerMessage) (*sarama.ProducerMessage, bool)
}

type FilterInterceptor struct {
	keyRegex    *regexp.Regexp
	valueRegex  *regexp.Regexp
	topicRegex  *regexp.Regexp
	jsonPaths   []compiledJSONPath
	jsonPathMu  sync.Once
	rawJSONPaths []RawJSONPath
	valuePool   sync.Pool
}

type RawJSONPath struct {
	Path     string
	Operator string
	Value    string
}

type compiledJSONPath struct {
	segments []string
	operator string
	value    string
}

func NewFilterInterceptor(keyRegex, valueRegex, topicRegex string, jsonPathFilters []RawJSONPath) (*FilterInterceptor, error) {
	fi := &FilterInterceptor{
		rawJSONPaths: jsonPathFilters,
		valuePool: sync.Pool{
			New: func() interface{} {
				return make(map[string]interface{})
			},
		},
	}

	var err error
	if keyRegex != "" {
		fi.keyRegex, err = regexp.Compile(keyRegex)
		if err != nil {
			return nil, err
		}
	}
	if valueRegex != "" {
		fi.valueRegex, err = regexp.Compile(valueRegex)
		if err != nil {
			return nil, err
		}
	}
	if topicRegex != "" {
		fi.topicRegex, err = regexp.Compile(topicRegex)
		if err != nil {
			return nil, err
		}
	}

	return fi, nil
}

func (f *FilterInterceptor) compileJSONPaths() {
	compiled := make([]compiledJSONPath, 0, len(f.rawJSONPaths))
	for _, jp := range f.rawJSONPaths {
		segments := strings.Split(strings.TrimPrefix(jp.Path, "$."), ".")
		compiled = append(compiled, compiledJSONPath{
			segments: segments,
			operator: jp.Operator,
			value:    jp.Value,
		})
	}
	f.jsonPaths = compiled
	f.rawJSONPaths = nil
}

func (f *FilterInterceptor) Intercept(msg *sarama.ConsumerMessage) (*sarama.ProducerMessage, bool) {
	if f.keyRegex != nil && msg.Key != nil {
		if !f.keyRegex.Match(msg.Key) {
			return nil, false
		}
	}

	if f.valueRegex != nil && msg.Value != nil {
		if !f.valueRegex.Match(msg.Value) {
			return nil, false
		}
	}

	if f.topicRegex != nil {
		if !f.topicRegex.MatchString(msg.Topic) {
			return nil, false
		}
	}

	if len(f.rawJSONPaths) > 0 || len(f.jsonPaths) > 0 {
		f.jsonPathMu.Do(f.compileJSONPaths)
		if len(f.jsonPaths) > 0 && msg.Value != nil {
			if !f.matchJSONPaths(msg.Value) {
				return nil, false
			}
		}
	}

	producerMsg := &sarama.ProducerMessage{
		Topic:    msg.Topic,
		Key:      sarama.ByteEncoder(msg.Key),
		Value:    sarama.ByteEncoder(msg.Value),
		Headers:  convertHeaders(msg.Headers),
		Metadata: msg.Offset,
	}

	return producerMsg, true
}

func (f *FilterInterceptor) matchJSONPaths(data []byte) bool {
	poolMap := f.valuePool.Get().(map[string]interface{})
	defer func() {
		for k := range poolMap {
			delete(poolMap, k)
		}
		f.valuePool.Put(poolMap)
	}()

	if err := json.Unmarshal(data, &poolMap); err != nil {
		return false
	}

	for _, jp := range f.jsonPaths {
		val := resolveNestedField(poolMap, jp.segments)
		if val == nil {
			return false
		}
		if !matchOperator(fmt.Sprintf("%v", val), jp.operator, jp.value) {
			return false
		}
	}

	return true
}

func resolveNestedField(data map[string]interface{}, segments []string) interface{} {
	var current interface{} = data

	for _, seg := range segments {
		switch v := current.(type) {
		case map[string]interface{}:
			var ok bool
			current, ok = v[seg]
			if !ok {
				return nil
			}
		case []interface{}:
			idx, err := strconv.Atoi(seg)
			if err != nil || idx < 0 || idx >= len(v) {
				return nil
			}
			current = v[idx]
		default:
			return nil
		}
	}

	return current
}

func matchOperator(actual, operator, expected string) bool {
	switch operator {
	case "eq", "==", "=":
		return actual == expected
	case "neq", "!=":
		return actual != expected
	case "contains":
		return strings.Contains(actual, expected)
	case "prefix":
		return strings.HasPrefix(actual, expected)
	case "suffix":
		return strings.HasSuffix(actual, expected)
	case "gt":
		a, e := parseFloat(actual, expected)
		return a > e
	case "gte":
		a, e := parseFloat(actual, expected)
		return a >= e
	case "lt":
		a, e := parseFloat(actual, expected)
		return a < e
	case "lte":
		a, e := parseFloat(actual, expected)
		return a <= e
	case "regex":
		re, err := regexp.Compile(expected)
		if err != nil {
			return false
		}
		return re.MatchString(actual)
	case "exists":
		return actual != ""
	default:
		return actual == expected
	}
}

func parseFloat(a, b string) (float64, float64) {
	af, _ := strconv.ParseFloat(a, 64)
	bf, _ := strconv.ParseFloat(b, 64)
	return af, bf
}

func convertHeaders(headers []*sarama.RecordHeader) []sarama.RecordHeader {
	result := make([]sarama.RecordHeader, len(headers))
	for i, h := range headers {
		result[i] = sarama.RecordHeader{
			Key:   h.Key,
			Value: h.Value,
		}
	}
	return result
}

type HopHeader struct {
	TraceID string `json:"trace_id"`
	HopCount int   `json:"hop_count"`
}

type LoopPreventionInterceptor struct {
	headerKey string
	maxHops   int
}

func NewLoopPreventionInterceptor(headerKey string, maxHops int) *LoopPreventionInterceptor {
	return &LoopPreventionInterceptor{
		headerKey: headerKey,
		maxHops:   maxHops,
	}
}

func (l *LoopPreventionInterceptor) Intercept(msg *sarama.ConsumerMessage) (*sarama.ProducerMessage, bool) {
	var hop *HopHeader

	for _, header := range msg.Headers {
		if string(header.Key) == l.headerKey {
			parsed, err := parseHopHeader(header.Value)
			if err == nil {
				hop = parsed
			}
			break
		}
	}

	if hop != nil {
		if hop.HopCount <= 0 {
			return nil, false
		}
		hop.HopCount--
	} else {
		hop = &HopHeader{
			TraceID:  generateUUID(),
			HopCount: l.maxHops - 1,
		}
	}

	producerMsg := &sarama.ProducerMessage{
		Topic:    msg.Topic,
		Key:      sarama.ByteEncoder(msg.Key),
		Value:    sarama.ByteEncoder(msg.Value),
		Headers:  convertHeaders(msg.Headers),
		Metadata: msg.Offset,
	}

	hopValue, err := serializeHopHeader(hop)
	if err == nil {
		producerMsg.Headers = append(producerMsg.Headers, sarama.RecordHeader{
			Key:   []byte(l.headerKey),
			Value: hopValue,
		})
	}

	return producerMsg, true
}

func parseHopHeader(data []byte) (*HopHeader, error) {
	var hop HopHeader
	if err := json.Unmarshal(data, &hop); err != nil {
		return nil, err
	}
	return &hop, nil
}

func serializeHopHeader(hop *HopHeader) ([]byte, error) {
	return json.Marshal(hop)
}

func generateUUID() string {
	var uuid [16]byte
	_, _ = rand.Read(uuid[:])
	uuid[6] = (uuid[6] & 0x0f) | 0x40
	uuid[8] = (uuid[8] & 0x3f) | 0x80
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x",
		binary.BigEndian.Uint32(uuid[0:4]),
		binary.BigEndian.Uint16(uuid[4:6]),
		binary.BigEndian.Uint16(uuid[6:8]),
		binary.BigEndian.Uint16(uuid[8:10]),
		uint64(uuid[10])<<40|uint64(uuid[11])<<32|uint64(uuid[12])<<24|uint64(uuid[13])<<16|uint64(uuid[14])<<8|uint64(uuid[15]),
	)
}

type ChainInterceptor struct {
	interceptors []MessageInterceptor
}

func NewChainInterceptor(interceptors ...MessageInterceptor) *ChainInterceptor {
	return &ChainInterceptor{
		interceptors: interceptors,
	}
}

func (c *ChainInterceptor) Intercept(msg *sarama.ConsumerMessage) (*sarama.ProducerMessage, bool) {
	currentMsg := msg

	for _, interceptor := range c.interceptors {
		producerMsg, ok := interceptor.Intercept(currentMsg)
		if !ok {
			return nil, false
		}

		currentMsg = &sarama.ConsumerMessage{
			Topic:     producerMsg.Topic,
			Key:       producerMsg.Key.(sarama.ByteEncoder),
			Value:     producerMsg.Value.(sarama.ByteEncoder),
			Headers:   convertProducerHeaders(producerMsg.Headers),
			Offset:    currentMsg.Offset,
			Partition: currentMsg.Partition,
		}
	}

	finalMsg := &sarama.ProducerMessage{
		Topic:    currentMsg.Topic,
		Key:      sarama.ByteEncoder(currentMsg.Key),
		Value:    sarama.ByteEncoder(currentMsg.Value),
		Headers:  convertProducerHeaders(currentMsg.Headers),
		Metadata: currentMsg.Offset,
	}

	return finalMsg, true
}

func convertProducerHeaders(headers []sarama.RecordHeader) []*sarama.RecordHeader {
	result := make([]*sarama.RecordHeader, len(headers))
	for i, h := range headers {
		result[i] = &sarama.RecordHeader{
			Key:   h.Key,
			Value: h.Value,
		}
	}
	return result
}
