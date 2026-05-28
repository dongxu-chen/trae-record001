//go:build tinygo.wasm

package main

import (
	"strings"

	"github.com/tetratelabs/proxy-wasm-go-sdk/proxywasm"
)

func (ctx *httpContext) applyHeaderRules() {
	ctx.pluginCtx.mu.RLock()
	rules := ctx.pluginCtx.headerRules
	ctx.pluginCtx.mu.RUnlock()

	for _, rule := range rules {
		if !rule.shouldApply(ctx.requestHeaders) {
			continue
		}

		switch rule.Operation {
		case "add":
			ctx.applyAddHeader(rule)
		case "remove":
			ctx.applyRemoveHeader(rule)
		case "replace":
			ctx.applyReplaceHeader(rule)
		case "rename":
			ctx.applyRenameHeader(rule)
		}
	}
}

func (ctx *httpContext) applyAddHeader(rule HeaderRule) {
	currentValue, exists := ctx.requestHeaders[rule.Name]
	if exists && !rule.Override {
		return
	}

	ctx.requestHeaders[rule.Name] = rule.Value
	_ = proxywasm.AddHttpRequestHeader(rule.Name, rule.Value)
	_ = currentValue
}

func (ctx *httpContext) applyRemoveHeader(rule HeaderRule) {
	delete(ctx.requestHeaders, rule.Name)
	_ = proxywasm.RemoveHttpRequestHeader(rule.Name)
}

func (ctx *httpContext) applyReplaceHeader(rule HeaderRule) {
	currentValue, exists := ctx.requestHeaders[rule.Name]
	if !exists {
		return
	}

	if rule.Match != "" && !strings.Contains(currentValue, rule.Match) {
		return
	}

	var newValue string
	if rule.Match != "" {
		newValue = strings.Replace(currentValue, rule.Match, rule.Value, 1)
	} else {
		newValue = rule.Value
	}

	ctx.requestHeaders[rule.Name] = newValue
	_ = proxywasm.ReplaceHttpRequestHeader(rule.Name, newValue)
}

func (ctx *httpContext) applyRenameHeader(rule HeaderRule) {
	currentValue, exists := ctx.requestHeaders[rule.Name]
	if !exists {
		return
	}

	delete(ctx.requestHeaders, rule.Name)
	ctx.requestHeaders[rule.Value] = currentValue

	_ = proxywasm.RemoveHttpRequestHeader(rule.Name)
	_ = proxywasm.AddHttpRequestHeader(rule.Value, currentValue)
}
