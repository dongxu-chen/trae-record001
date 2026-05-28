//go:build tinygo.wasm

package main

import (
	"hash/fnv"
	"strings"
	"sync"

	"github.com/tetratelabs/proxy-wasm-go-sdk/proxywasm"
	"github.com/tetratelabs/proxy-wasm-go-sdk/proxywasm/types"
)

func main() {
	proxywasm.SetVMContext(&vmContext{})
}

type vmContext struct {
	types.DefaultVMContext
}

func (*vmContext) NewPluginContext(contextID uint32) types.PluginContext {
	return &pluginContext{
		contextID:       contextID,
		mu:              sync.RWMutex{},
		samplingRate:    0.1,
		headerRules:     make([]HeaderRule, 0),
		samplingHashKey: "x-request-id",
		protoContentTypes: []string{
			"application/grpc",
			"application/grpc+proto",
			"application/x-protobuf",
			"application/protobuf",
		},
		colorEnabled:    false,
		colorHeader:     "x-traffic-color",
		colorValue:      "mirrored",
		anomalyEnabled:  true,
		anomalyThreshold: 0.0,
	}
}

type pluginContext struct {
	types.DefaultPluginContext
	contextID          uint32
	mu                 sync.RWMutex
	samplingRate       float64
	headerRules        []HeaderRule
	testCluster        string
	controlPlane       string
	samplingHashKey    string
	protoContentTypes  []string
	colorEnabled       bool
	colorHeader        string
	colorValue         string
	anomalyEnabled     bool
	anomalyThreshold   float64
}

func (ctx *pluginContext) OnPluginStart(pluginConfigurationSize int) types.OnPluginStartStatus {
	configData, err := proxywasm.GetPluginConfiguration()
	if err != nil {
		proxywasm.LogWarnf("failed to get plugin configuration: %v", err)
		return types.OnPluginStartStatusOK
	}

	ctx.mu.Lock()
	defer ctx.mu.Unlock()

	cfg := parseConfig(string(configData))
	ctx.samplingRate = cfg.SamplingRate
	ctx.headerRules = cfg.HeaderRules
	ctx.testCluster = cfg.TestCluster
	ctx.controlPlane = cfg.ControlPlane
	ctx.samplingHashKey = cfg.SamplingHashKey
	ctx.protoContentTypes = cfg.ProtoContentTypes
	ctx.colorEnabled = cfg.ColorEnabled
	ctx.colorHeader = cfg.ColorHeader
	ctx.colorValue = cfg.ColorValue
	ctx.anomalyEnabled = cfg.AnomalyEnabled
	ctx.anomalyThreshold = cfg.AnomalyThreshold

	proxywasm.LogInfof("plugin config loaded: sampling_rate=%.2f, test_cluster=%s, hash_key=%s, color=%v, anomaly=%v",
		ctx.samplingRate, ctx.testCluster, ctx.samplingHashKey, ctx.colorEnabled, ctx.anomalyEnabled)

	return types.OnPluginStartStatusOK
}

func (ctx *pluginContext) NewHttpContext(contextID uint32) types.HttpContext {
	return &httpContext{
		contextID:      contextID,
		pluginCtx:      ctx,
		mirrored:       false,
		requestHeaders: make(map[string]string),
		requestBody:    make([]byte, 0),
		prodResponse:   make([]byte, 0),
		testResponse:   make([]byte, 0),
		prodStatusCode: 0,
		testStatusCode: 0,
	}
}

type httpContext struct {
	types.DefaultHttpContext
	contextID        uint32
	pluginCtx        *pluginContext
	mirrored         bool
	requestHeaders   map[string]string
	requestBody      []byte
	prodResponse     []byte
	testResponse     []byte
	prodStatusCode   uint32
	testStatusCode   uint32
	reqTotalSize     int
	respTotalSize    int
	isProto          bool
	protoMessageType string
	anomaly          string
}

func (ctx *httpContext) OnHttpRequestHeaders(numHeaders int, endOfStream bool) types.Action {
	headers, err := proxywasm.GetHttpRequestHeaders()
	if err != nil {
		proxywasm.LogErrorf("failed to get request headers: %v", err)
		return types.ActionContinue
	}

	for _, h := range headers {
		ctx.requestHeaders[h[0]] = h[1]
	}

	contentType := ctx.requestHeaders["content-type"]
	ctx.isProto = isProtoContentType(contentType, ctx.pluginCtx.protoContentTypes)

	if msgType := ctx.requestHeaders["x-proto-message-type"]; msgType != "" {
		ctx.protoMessageType = msgType
	}

	ctx.pluginCtx.mu.RLock()
	samplingRate := ctx.pluginCtx.samplingRate
	hashKey := ctx.pluginCtx.samplingHashKey
	headerRules := ctx.pluginCtx.headerRules
	ctx.pluginCtx.mu.RUnlock()

	hashInput := ctx.buildHashInput(hashKey)
	consistentHash := fnv64a(hashInput)
	threshold := uint64(samplingRate * 10000)
	if consistentHash%10000 < threshold {
		ctx.mirrored = true

		proxywasm.LogInfof("consistent hash sampling: key=%s hash=%d threshold=%d selected",
			truncateString(hashInput, 128), consistentHash, threshold)

		for _, rule := range headerRules {
			if !rule.shouldApply(ctx.requestHeaders) {
				continue
			}
			switch rule.Operation {
			case "add":
				if _, exists := ctx.requestHeaders[rule.Name]; !exists || rule.Override {
					ctx.requestHeaders[rule.Name] = rule.Value
					_ = proxywasm.AddHttpRequestHeader(rule.Name, rule.Value)
				}
			case "remove":
				delete(ctx.requestHeaders, rule.Name)
				_ = proxywasm.RemoveHttpRequestHeader(rule.Name)
			case "replace":
				if strings.Contains(ctx.requestHeaders[rule.Name], rule.Match) {
					newValue := strings.Replace(ctx.requestHeaders[rule.Name], rule.Match, rule.Value, 1)
					ctx.requestHeaders[rule.Name] = newValue
					_ = proxywasm.ReplaceHttpRequestHeader(rule.Name, newValue)
				}
			case "rename":
				if val, exists := ctx.requestHeaders[rule.Name]; exists {
					delete(ctx.requestHeaders, rule.Name)
					ctx.requestHeaders[rule.Value] = val
					_ = proxywasm.RemoveHttpRequestHeader(rule.Name)
					_ = proxywasm.AddHttpRequestHeader(rule.Value, val)
				}
			}
		}
	}

	return types.ActionContinue
}

func (ctx *httpContext) OnHttpRequestBody(bodySize int, endOfStream bool) types.Action {
	if !ctx.mirrored {
		return types.ActionContinue
	}

	ctx.reqTotalSize += bodySize
	if body, err := proxywasm.GetHttpRequestBody(0, bodySize); err == nil {
		ctx.requestBody = append(ctx.requestBody, body...)
	}

	return types.ActionContinue
}

func (ctx *httpContext) OnHttpResponseHeaders(numHeaders int, endOfStream bool) types.Action {
	if !ctx.mirrored {
		return types.ActionContinue
	}

	if status, err := proxywasm.GetHttpResponseHeader(":status"); err == nil {
		_ = status
	}

	if ct := ctx.requestHeaders["content-type"]; ct != "" {
		ctx.isProto = isProtoContentType(ct, ctx.pluginCtx.protoContentTypes)
	}

	return types.ActionContinue
}

func (ctx *httpContext) OnHttpResponseBody(bodySize int, endOfStream bool) types.Action {
	if !ctx.mirrored {
		return types.ActionContinue
	}

	ctx.respTotalSize += bodySize
	if body, err := proxywasm.GetHttpResponseBody(0, bodySize); err == nil {
		ctx.prodResponse = append(ctx.prodResponse, body...)
	}

	if endOfStream {
		if status, err := proxywasm.GetHttpResponseHeader(":status"); err == nil {
			ctx.prodStatusCode = parseStatusCode(status)
		}

		ctx.prodResponse = stripGrpcPrefix(ctx.prodResponse)

		ctx.dispatchMirrorRequest()
	}

	return types.ActionContinue
}

func (ctx *httpContext) dispatchMirrorRequest() {
	ctx.pluginCtx.mu.RLock()
	testCluster := ctx.pluginCtx.testCluster
	controlPlane := ctx.pluginCtx.controlPlane
	colorEnabled := ctx.pluginCtx.colorEnabled
	colorHeader := ctx.pluginCtx.colorHeader
	colorValue := ctx.pluginCtx.colorValue
	ctx.pluginCtx.mu.RUnlock()

	if testCluster == "" {
		return
	}

	headers := make([]string, 0, len(ctx.requestHeaders)*2)
	for k, v := range ctx.requestHeaders {
		headers = append(headers, k, v)
	}

	headers = append(headers,
		"x-mirrored-request", "true",
		"x-mirrored-from", "production",
	)

	if colorEnabled {
		headers = append(headers, colorHeader, colorValue)
		proxywasm.LogInfof("traffic coloring applied: %s=%s", colorHeader, colorValue)
	}

	_, err := proxywasm.DispatchHttpCall(
		testCluster,
		headers,
		ctx.requestBody,
		nil,
		5000,
		func(numHeaders int, bodySize int, _ uint32) {
			ctx.handleTestResponseCallback(numHeaders, bodySize, controlPlane)
		},
	)

	if err != nil {
		proxywasm.LogErrorf("failed to dispatch mirror request: %v", err)
	}
}

func (ctx *httpContext) handleTestResponseCallback(numHeaders int, bodySize int, controlPlane string) {
	if body, err := proxywasm.GetHttpCallResponseBody(0, bodySize); err == nil {
		ctx.testResponse = stripGrpcPrefix(body)
	}

	if status, err := proxywasm.GetHttpCallResponseHeader(":status"); err == nil {
		ctx.testStatusCode = parseStatusCode(status)
	}

	testHeaders := make(map[string]string)
	if hs, err := proxywasm.GetHttpCallResponseHeaders(); err == nil {
		for _, h := range hs {
			testHeaders[h[0]] = h[1]
		}
	}

	ctx.pluginCtx.mu.RLock()
	anomalyEnabled := ctx.pluginCtx.anomalyEnabled
	ctx.pluginCtx.mu.RUnlock()

	comparison := compareResponses(
		ctx.prodResponse, ctx.testResponse,
		ctx.prodStatusCode, ctx.testStatusCode,
		ctx.isProto, ctx.protoMessageType,
	)

	if anomalyEnabled {
		ctx.anomaly = detectAnomaly(
			ctx.prodStatusCode, ctx.testStatusCode,
			ctx.prodResponse, ctx.testResponse,
			comparison,
		)
		comparison.Anomaly = ctx.anomaly
		if ctx.anomaly != "" {
			proxywasm.LogWarnf("anomaly detected for %s %s: %s",
				ctx.requestHeaders[":method"], ctx.requestHeaders[":path"], ctx.anomaly)
		}
	}

	comparison.Path = ctx.requestHeaders[":path"]
	comparison.Method = ctx.requestHeaders[":method"]
	comparison.ProdHeaders = mapToJSON(ctx.requestHeaders)
	comparison.TestHeaders = mapToJSON(testHeaders)
	comparison.IsProto = ctx.isProto
	comparison.ProtoMessageType = ctx.protoMessageType

	ctx.reportComparison(comparison, controlPlane)
}

func (ctx *httpContext) reportComparison(result ComparisonResult, controlPlane string) {
	if controlPlane == "" {
		proxywasm.LogInfo("control plane not configured, skipping report")
		return
	}

	body := result.ToJSON()
	headers := []string{
		"content-type", "application/json",
		":method", "POST",
		":path", "/api/v1/comparisons",
		":authority", controlPlane,
	}

	_, err := proxywasm.DispatchHttpCall(
		controlPlane,
		headers,
		[]byte(body),
		nil,
		3000,
		func(_ int, _ int, _ uint32) {
			proxywasm.LogDebug("comparison result reported")
		},
	)

	if err != nil {
		proxywasm.LogErrorf("failed to report comparison: %v", err)
	}
}

func (ctx *httpContext) buildHashInput(hashKey string) string {
	var parts []string

	if hashKey != "" {
		if val, ok := ctx.requestHeaders[hashKey]; ok && val != "" {
			parts = append(parts, val)
		}
	}

	if method, ok := ctx.requestHeaders[":method"]; ok {
		parts = append(parts, method)
	}
	if path, ok := ctx.requestHeaders[":path"]; ok {
		if idx := strings.Index(path, "?"); idx > 0 {
			parts = append(parts, path[:idx])
		} else {
			parts = append(parts, path)
		}
	}
	if authority, ok := ctx.requestHeaders[":authority"]; ok {
		parts = append(parts, authority)
	}

	return strings.Join(parts, "|")
}

func fnv64a(s string) uint64 {
	h := fnv.New64a()
	h.Write([]byte(s))
	return h.Sum64()
}

func isProtoContentType(contentType string, protoTypes []string) bool {
	if contentType == "" {
		return false
	}
	ct := strings.ToLower(contentType)
	for _, pt := range protoTypes {
		if strings.HasPrefix(ct, pt) {
			return true
		}
	}
	return false
}

func stripGrpcPrefix(body []byte) []byte {
	if len(body) <= 5 {
		return body
	}
	if body[0] == 0x00 || body[0] == 0x01 {
		return body[5:]
	}
	return body
}

func mapToJSON(m map[string]string) string {
	if len(m) == 0 {
		return "{}"
	}
	var parts []string
	for k, v := range m {
		parts = append(parts, "\""+k+"\":\""+v+"\"")
	}
	return "{" + strings.Join(parts, ",") + "}"
}

func parseStatusCode(status string) uint32 {
	if len(status) < 3 {
		return 0
	}
	var code uint32
	for _, c := range status[:3] {
		if c >= '0' && c <= '9' {
			code = code*10 + uint32(c-'0')
		}
	}
	return code
}

func truncateString(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "..."
}

func detectAnomaly(prodStatus, testStatus uint32, prodBody, testBody []byte, comparison ComparisonResult) string {
	if testStatus >= 500 {
		return "error_5xx"
	}

	if prodStatus < 400 && testStatus >= 400 {
		return "error_4xx"
	}

	if testStatus == 0 {
		return "timeout"
	}

	if !comparison.BodyMatch && len(prodBody) > 0 {
		bodyDiff := float64(len(prodBody)-len(testBody)) / float64(max(len(prodBody), 1))
		if bodyDiff > 0.8 || bodyDiff < -0.8 {
			return "body_mismatch_severe"
		}
	}

	if comparison.Severity == "critical" {
		return "critical_diff"
	}

	return ""
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
