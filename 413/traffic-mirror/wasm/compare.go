//go:build tinygo.wasm

package main

import (
	"encoding/hex"
	"fmt"
	"hash/fnv"
	"strings"

	"github.com/tidwall/gjson"
	"github.com/tidwall/sjson"
)

type ComparisonResult struct {
	RequestID        string            `json:"request_id"`
	Timestamp        int64             `json:"timestamp"`
	Path             string            `json:"path"`
	Method           string            `json:"method"`
	ProdStatus       uint32            `json:"prod_status"`
	TestStatus       uint32            `json:"test_status"`
	StatusMatch      bool              `json:"status_match"`
	BodyMatch        bool              `json:"body_match"`
	HeaderMatch      bool              `json:"header_match"`
	Differences      []Difference      `json:"differences"`
	ProdBodyHash     string            `json:"prod_body_hash"`
	TestBodyHash     string            `json:"test_body_hash"`
	ProdBodyLen      int               `json:"prod_body_len"`
	TestBodyLen      int               `json:"test_body_len"`
	Headers          map[string]string `json:"headers,omitempty"`
	ProdHeaders      string            `json:"prod_headers,omitempty"`
	TestHeaders      string            `json:"test_headers,omitempty"`
	HasDiff          bool              `json:"has_diff"`
	Severity         string            `json:"severity"`
	IsProto          bool              `json:"is_proto"`
	ProtoMessageType string            `json:"proto_message_type,omitempty"`
	ProtoDifferences []ProtoFieldDiff  `json:"proto_differences,omitempty"`
}

type Difference struct {
	Field    string `json:"field"`
	Type     string `json:"type"`
	ProdVal  string `json:"prod_value"`
	TestVal  string `json:"test_value"`
	Severity string `json:"severity"`
}

type ProtoFieldDiff struct {
	FieldNumber int32  `json:"field_number"`
	FieldName   string `json:"field_name,omitempty"`
	WireType    int    `json:"wire_type"`
	ProdVal     string `json:"prod_value"`
	TestVal     string `json:"test_value"`
	Severity    string `json:"severity"`
}

type protoWireField struct {
	FieldNumber int32
	WireType    int
	Value       []byte
	RawLen      int
}

func compareResponses(prodBody, testBody []byte, prodStatus, testStatus uint32, isProto bool, protoMsgType string) ComparisonResult {
	result := ComparisonResult{
		Timestamp:        currentTimestamp(),
		ProdStatus:       prodStatus,
		TestStatus:       testStatus,
		StatusMatch:      prodStatus == testStatus,
		BodyMatch:        string(prodBody) == string(testBody),
		ProdBodyHash:     hashBody(prodBody),
		TestBodyHash:     hashBody(testBody),
		ProdBodyLen:      len(prodBody),
		TestBodyLen:      len(testBody),
		IsProto:          isProto,
		ProtoMessageType: protoMsgType,
	}

	result.Differences = findDifferences(prodBody, testBody, prodStatus, testStatus)

	if isProto {
		result.ProtoDifferences = compareProtoFields(prodBody, testBody)
		if len(result.ProtoDifferences) > 0 {
			for _, pd := range result.ProtoDifferences {
				result.Differences = append(result.Differences, Difference{
					Field:    fmt.Sprintf("proto_field_%d", pd.FieldNumber),
					Type:     "proto",
					ProdVal:  pd.ProdVal,
					TestVal:  pd.TestVal,
					Severity: pd.Severity,
				})
			}
		}
	}

	result.HasDiff = len(result.Differences) > 0
	result.Severity = computeSeverity(result.Differences)

	return result
}

func findDifferences(prodBody, testBody []byte, prodStatus, testStatus uint32) []Difference {
	var diffs []Difference

	if prodStatus != testStatus {
		diffs = append(diffs, Difference{
			Field:    "status_code",
			Type:     "status",
			ProdVal:  fmt.Sprintf("%d", prodStatus),
			TestVal:  fmt.Sprintf("%d", testStatus),
			Severity: "critical",
		})
	}

	prodBodyStr := string(prodBody)
	testBodyStr := string(testBody)

	if prodBodyStr != testBodyStr {
		diffs = append(diffs, Difference{
			Field:    "body",
			Type:     "body",
			ProdVal:  truncateString(prodBodyStr, 500),
			TestVal:  truncateString(testBodyStr, 500),
			Severity: bodyDiffSeverity(prodBodyStr, testBodyStr),
		})

		jsonDiffs := compareJSON(prodBodyStr, testBodyStr)
		diffs = append(diffs, jsonDiffs...)
	}

	return diffs
}

func compareProtoFields(prodBody, testBody []byte) []ProtoFieldDiff {
	var diffs []ProtoFieldDiff

	prodFields := parseProtoFields(prodBody)
	testFields := parseProtoFields(testBody)

	prodMap := make(map[int32]protoWireField)
	for _, f := range prodFields {
		prodMap[f.FieldNumber] = f
	}

	testMap := make(map[int32]protoWireField)
	for _, f := range testFields {
		testMap[f.FieldNumber] = f
	}

	allFieldNums := make(map[int32]bool)
	for fn := range prodMap {
		allFieldNums[fn] = true
	}
	for fn := range testMap {
		allFieldNums[fn] = true
	}

	for fn := range allFieldNums {
		prodField, prodOk := prodMap[fn]
		testField, testOk := testMap[fn]

		if !prodOk {
			diffs = append(diffs, ProtoFieldDiff{
				FieldNumber: fn,
				WireType:    testField.WireType,
				ProdVal:     "<missing>",
				TestVal:     truncateString(hex.EncodeToString(testField.Value), 100),
				Severity:    "critical",
			})
			continue
		}
		if !testOk {
			diffs = append(diffs, ProtoFieldDiff{
				FieldNumber: fn,
				WireType:    prodField.WireType,
				ProdVal:     truncateString(hex.EncodeToString(prodField.Value), 100),
				TestVal:     "<missing>",
				Severity:    "critical",
			})
			continue
		}

		if prodField.WireType != testField.WireType {
			diffs = append(diffs, ProtoFieldDiff{
				FieldNumber: fn,
				WireType:    prodField.WireType,
				ProdVal:     fmt.Sprintf("wire_type=%d, value=%s", prodField.WireType, truncateString(hex.EncodeToString(prodField.Value), 64)),
				TestVal:     fmt.Sprintf("wire_type=%d, value=%s", testField.WireType, truncateString(hex.EncodeToString(testField.Value), 64)),
				Severity:    "critical",
			})
			continue
		}

		if string(prodField.Value) != string(testField.Value) {
			prodStr := protoValueToString(prodField.WireType, prodField.Value)
			testStr := protoValueToString(testField.WireType, testField.Value)
			diffs = append(diffs, ProtoFieldDiff{
				FieldNumber: fn,
				WireType:    prodField.WireType,
				ProdVal:     prodStr,
				TestVal:     testStr,
				Severity:    "warning",
			})
		}
	}

	return diffs
}

func parseProtoFields(data []byte) []protoWireField {
	var fields []protoWireField
	offset := 0

	for offset < len(data) {
		if offset+1 > len(data) {
			break
		}

		tag, tagLen := readVarint(data[offset:])
		if tagLen == 0 {
			break
		}

		fieldNumber := int32(tag >> 3)
		wireType := int(tag & 0x07)
		offset += tagLen

		if fieldNumber <= 0 || fieldNumber > 100000 {
			break
		}

		var value []byte
		var valueLen int

		switch wireType {
		case 0:
			v, l := readVarint(data[offset:])
			value = make([]byte, l)
			copy(value, data[offset:offset+l])
			valueLen = l
		case 1:
			if offset+8 > len(data) {
				break
			}
			value = make([]byte, 8)
			copy(value, data[offset:offset+8])
			valueLen = 8
		case 2:
			length, l := readVarint(data[offset:])
			valueLen = l + int(length)
			if offset+valueLen > len(data) {
				break
			}
			value = make([]byte, length)
			copy(value, data[offset+l:offset+l+int(length)])
		case 5:
			if offset+4 > len(data) {
				break
			}
			value = make([]byte, 4)
			copy(value, data[offset:offset+4])
			valueLen = 4
		default:
			break
		}

		fields = append(fields, protoWireField{
			FieldNumber: fieldNumber,
			WireType:    wireType,
			Value:       value,
			RawLen:      tagLen + valueLen,
		})
		offset += valueLen
	}

	return fields
}

func readVarint(data []byte) (uint64, int) {
	var result uint64
	var shift uint
	for i, b := range data {
		if i > 9 {
			return 0, 0
		}
		result |= uint64(b&0x7F) << shift
		if b&0x80 == 0 {
			return result, i + 1
		}
		shift += 7
	}
	return 0, 0
}

func protoValueToString(wireType int, value []byte) string {
	switch wireType {
	case 0:
		v, _ := readVarint(value)
		return fmt.Sprintf("varint:%d", v)
	case 1:
		return "fixed64:" + hex.EncodeToString(value)
	case 2:
		s := string(value)
		if isPrintable(s) {
			return truncateString("len-delim:\""+s+"\"", 120)
		}
		return truncateString("len-delim:0x"+hex.EncodeToString(value), 120)
	case 5:
		return "fixed32:" + hex.EncodeToString(value)
	default:
		return truncateString("0x"+hex.EncodeToString(value), 120)
	}
}

func isPrintable(s string) bool {
	if len(s) == 0 {
		return false
	}
	printableCount := 0
	for _, c := range s {
		if c >= 32 && c < 127 {
			printableCount++
		}
	}
	return float64(printableCount)/float64(len(s)) > 0.7
}

func compareJSON(prodStr, testStr string) []Difference {
	var diffs []Difference

	prodIsJSON := strings.HasPrefix(strings.TrimSpace(prodStr), "{") || strings.HasPrefix(strings.TrimSpace(prodStr), "[")
	testIsJSON := strings.HasPrefix(strings.TrimSpace(testStr), "{") || strings.HasPrefix(strings.TrimSpace(testStr), "[")

	if !prodIsJSON || !testIsJSON {
		return diffs
	}

	prodPaths := getJSONPaths(prodStr)
	testPaths := getJSONPaths(testStr)

	allPaths := make(map[string]bool)
	for p := range prodPaths {
		allPaths[p] = true
	}
	for p := range testPaths {
		allPaths[p] = true
	}

	for path := range allPaths {
		prodVal := gjsonGet(prodStr, path)
		testVal := gjsonGet(testStr, path)

		if prodVal != testVal {
			diffs = append(diffs, Difference{
				Field:    path,
				Type:     "json_field",
				ProdVal:  truncateString(prodVal, 200),
				TestVal:  truncateString(testVal, 200),
				Severity: "warning",
			})
		}
	}

	return diffs
}

func getJSONPaths(jsonStr string) map[string]bool {
	paths := make(map[string]bool)
	collectJSONPaths("", jsonStr, paths)
	return paths
}

func collectJSONPaths(prefix string, jsonStr string, paths map[string]bool) {
	result := gjsonParse(jsonStr)
	if !result.Exists() {
		return
	}

	if result.IsObject() {
		result.ForEach(func(key, value gjson.Result) bool {
			fullPath := key.String()
			if prefix != "" {
				fullPath = prefix + "." + key.String()
			}
			paths[fullPath] = true
			if value.IsObject() || value.IsArray() {
				collectJSONPaths(fullPath, value.Raw, paths)
			}
			return true
		})
	} else if result.IsArray() {
		result.ForEach(func(_, value gjson.Result) bool {
			if value.IsObject() || value.IsArray() {
				collectJSONPaths(prefix, value.Raw, paths)
			}
			return true
		})
	}
}

func bodyDiffSeverity(prod, test string) string {
	if len(prod) == 0 && len(test) > 0 {
		return "critical"
	}
	if len(test) == 0 && len(prod) > 0 {
		return "critical"
	}
	diffRatio := float64(abs(len(prod)-len(test))) / float64(max(len(prod), len(test))+1)
	if diffRatio > 0.5 {
		return "critical"
	}
	if diffRatio > 0.2 {
		return "warning"
	}
	return "info"
}

func computeSeverity(diffs []Difference) string {
	if len(diffs) == 0 {
		return "none"
	}
	for _, d := range diffs {
		if d.Severity == "critical" {
			return "critical"
		}
	}
	for _, d := range diffs {
		if d.Severity == "warning" {
			return "warning"
		}
	}
	return "info"
}

func hashBody(body []byte) string {
	h := fnv.New64a()
	h.Write(body)
	return hex.EncodeToString(h.Sum(nil))
}

func currentTimestamp() int64 {
	return 0
}

func truncateString(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "..."
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func gjsonGet(json, path string) string {
	return gjson.Get(json, path).String()
}

func gjsonParse(json string) gjson.Result {
	return gjson.Parse(json)
}

func (r ComparisonResult) ToJSON() string {
	json := "{}"
	json, _ = sjson.Set(json, "request_id", r.RequestID)
	json, _ = sjson.Set(json, "timestamp", r.Timestamp)
	json, _ = sjson.Set(json, "path", r.Path)
	json, _ = sjson.Set(json, "method", r.Method)
	json, _ = sjson.Set(json, "prod_status", r.ProdStatus)
	json, _ = sjson.Set(json, "test_status", r.TestStatus)
	json, _ = sjson.Set(json, "status_match", r.StatusMatch)
	json, _ = sjson.Set(json, "body_match", r.BodyMatch)
	json, _ = sjson.Set(json, "header_match", r.HeaderMatch)
	json, _ = sjson.Set(json, "prod_body_hash", r.ProdBodyHash)
	json, _ = sjson.Set(json, "test_body_hash", r.TestBodyHash)
	json, _ = sjson.Set(json, "prod_body_len", r.ProdBodyLen)
	json, _ = sjson.Set(json, "test_body_len", r.TestBodyLen)
	json, _ = sjson.Set(json, "has_diff", r.HasDiff)
	json, _ = sjson.Set(json, "severity", r.Severity)
	json, _ = sjson.Set(json, "is_proto", r.IsProto)
	if r.ProtoMessageType != "" {
		json, _ = sjson.Set(json, "proto_message_type", r.ProtoMessageType)
	}
	if r.Anomaly != "" {
		json, _ = sjson.Set(json, "anomaly", r.Anomaly)
	}

	diffArr := make([]string, 0, len(r.Differences))
	for _, d := range r.Differences {
		diffJSON := "{}"
		diffJSON, _ = sjson.Set(diffJSON, "field", d.Field)
		diffJSON, _ = sjson.Set(diffJSON, "type", d.Type)
		diffJSON, _ = sjson.Set(diffJSON, "prod_value", d.ProdVal)
		diffJSON, _ = sjson.Set(diffJSON, "test_value", d.TestVal)
		diffJSON, _ = sjson.Set(diffJSON, "severity", d.Severity)
		diffArr = append(diffArr, diffJSON)
	}
	json, _ = sjson.Set(json, "differences", diffArr)

	if len(r.ProtoDifferences) > 0 {
		protoArr := make([]string, 0, len(r.ProtoDifferences))
		for _, pd := range r.ProtoDifferences {
			pdJSON := "{}"
			pdJSON, _ = sjson.Set(pdJSON, "field_number", pd.FieldNumber)
			pdJSON, _ = sjson.Set(pdJSON, "wire_type", pd.WireType)
			pdJSON, _ = sjson.Set(pdJSON, "prod_value", pd.ProdVal)
			pdJSON, _ = sjson.Set(pdJSON, "test_value", pd.TestVal)
			pdJSON, _ = sjson.Set(pdJSON, "severity", pd.Severity)
			protoArr = append(protoArr, pdJSON)
		}
		json, _ = sjson.Set(json, "proto_differences", protoArr)
	}

	return json
}
