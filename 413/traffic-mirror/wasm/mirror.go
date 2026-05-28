//go:build tinygo.wasm

package main

import (
	"github.com/tetratelabs/proxy-wasm-go-sdk/proxywasm"
)

func (ctx *httpContext) dispatchMirrorRequest() {
	if !ctx.mirrored {
		return
	}

	ctx.pluginCtx.mu.RLock()
	testCluster := ctx.pluginCtx.testCluster
	ctx.pluginCtx.mu.RUnlock()

	if testCluster == "" {
		proxywasm.LogWarn("test cluster not configured, skipping mirror")
		return
	}

	headers := make([]string, 0, len(ctx.requestHeaders)*2)
	for k, v := range ctx.requestHeaders {
		headers = append(headers, k, v)
	}

	headers = append(headers,
		"x-mirrored-from", "production",
		"x-mirror-timestamp", currentTimestampString(),
	)

	_, err := proxywasm.DispatchHttpCall(
		testCluster,
		headers,
		ctx.requestBody,
		nil,
		5000,
		ctx.handleTestResponseCallback,
	)

	if err != nil {
		proxywasm.LogErrorf("failed to dispatch mirror request: %v", err)
	}
}

func (ctx *httpContext) handleTestResponseCallback(numHeaders int, bodySize int, _ uint32) {
	if body, err := proxywasm.GetHttpCallResponseBody(0, bodySize); err == nil {
		ctx.testResponse = body
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

	comparison := compareResponses(ctx.prodResponse, ctx.testResponse, ctx.prodStatusCode, ctx.testStatusCode)

	comparison.Path = ctx.requestHeaders[":path"]
	comparison.Method = ctx.requestHeaders[":method"]
	comparison.TestHeaders = testHeaders

	ctx.reportComparison(comparison, ctx.pluginCtx.controlPlane)
}

func currentTimestampString() string {
	return "0"
}
