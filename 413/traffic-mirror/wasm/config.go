//go:build tinygo.wasm

package main

import (
	"strings"

	"github.com/tidwall/gjson"
)

type PluginConfig struct {
	SamplingRate      float64
	HeaderRules       []HeaderRule
	TestCluster       string
	ControlPlane      string
	SamplingHashKey   string
	ProtoContentTypes []string
	ColorEnabled      bool
	ColorHeader       string
	ColorValue        string
	AnomalyEnabled    bool
	AnomalyThreshold  float64
}

type HeaderRule struct {
	Name       string
	Value      string
	Operation  string
	Match      string
	Override   bool
}

func parseConfig(jsonStr string) PluginConfig {
	cfg := PluginConfig{
		SamplingRate:    0.1,
		HeaderRules:     make([]HeaderRule, 0),
		TestCluster:     "test_service",
		ControlPlane:    "",
		SamplingHashKey: "x-request-id",
		ProtoContentTypes: []string{
			"application/grpc",
			"application/grpc+proto",
			"application/x-protobuf",
			"application/protobuf",
		},
		ColorEnabled:     false,
		ColorHeader:      "x-traffic-color",
		ColorValue:       "mirrored",
		AnomalyEnabled:   true,
		AnomalyThreshold: 0.0,
	}

	if jsonStr == "" {
		return cfg
	}

	if sr := gjson.Get(jsonStr, "sampling_rate"); sr.Exists() {
		cfg.SamplingRate = sr.Float()
	}

	if tc := gjson.Get(jsonStr, "test_cluster"); tc.Exists() {
		cfg.TestCluster = tc.String()
	}

	if cp := gjson.Get(jsonStr, "control_plane"); cp.Exists() {
		cfg.ControlPlane = cp.String()
	}

	if hk := gjson.Get(jsonStr, "sampling_hash_key"); hk.Exists() {
		cfg.SamplingHashKey = hk.String()
	}

	if pct := gjson.Get(jsonStr, "proto_content_types"); pct.Exists() {
		pct.ForEach(func(_, value gjson.Result) bool {
			cfg.ProtoContentTypes = append(cfg.ProtoContentTypes, value.String())
			return true
		})
	}

	if ce := gjson.Get(jsonStr, "color_enabled"); ce.Exists() {
		cfg.ColorEnabled = ce.Bool()
	}
	if ch := gjson.Get(jsonStr, "color_header"); ch.Exists() {
		cfg.ColorHeader = ch.String()
	}
	if cv := gjson.Get(jsonStr, "color_value"); cv.Exists() {
		cfg.ColorValue = cv.String()
	}

	if ae := gjson.Get(jsonStr, "anomaly_enabled"); ae.Exists() {
		cfg.AnomalyEnabled = ae.Bool()
	}
	if at := gjson.Get(jsonStr, "anomaly_threshold"); at.Exists() {
		cfg.AnomalyThreshold = at.Float()
	}

	if rules := gjson.Get(jsonStr, "header_rules"); rules.Exists() {
		rules.ForEach(func(_, value gjson.Result) bool {
			rule := HeaderRule{
				Name:      value.Get("name").String(),
				Value:     value.Get("value").String(),
				Operation: value.Get("operation").String(),
				Match:     value.Get("match").String(),
				Override:  value.Get("override").Bool(),
			}
			cfg.HeaderRules = append(cfg.HeaderRules, rule)
			return true
		})
	}

	return cfg
}

func (r HeaderRule) shouldApply(headers map[string]string) bool {
	if r.Match != "" {
		val, exists := headers[r.Name]
		if !exists {
			return false
		}
		return strings.Contains(val, r.Match)
	}
	return true
}
