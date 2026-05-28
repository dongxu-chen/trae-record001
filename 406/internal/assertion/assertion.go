package assertion

import (
	"encoding/json"
	"encoding/xml"
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"health-check/internal/model"
)

type Engine struct{}

func NewEngine() *Engine {
	return &Engine{}
}

func (e *Engine) Evaluate(assertions []model.Assertion, body string, contentType string) []model.AssertionResult {
	results := make([]model.AssertionResult, 0, len(assertions))

	for _, assertion := range assertions {
		result := model.AssertionResult{
			Type: assertion.Type,
			Path: assertion.Path,
		}

		switch assertion.Type {
		case model.AssertionJSONPath:
			e.evaluateJSONPath(&assertion, body, &result)
		case model.AssertionXPath:
			e.evaluateXPath(&assertion, body, &result)
		case model.AssertionContains:
			e.evaluateContains(&assertion, body, &result)
		case model.AssertionRegex:
			e.evaluateRegex(&assertion, body, &result)
		default:
			result.Error = fmt.Sprintf("unsupported assertion type: %s", assertion.Type)
		}

		results = append(results, result)
	}

	return results
}

func (e *Engine) evaluateJSONPath(assertion *model.Assertion, body string, result *model.AssertionResult) {
	var data interface{}
	if err := json.Unmarshal([]byte(body), &data); err != nil {
		result.Error = fmt.Sprintf("invalid JSON: %v", err)
		return
	}

	value := extractJSONPath(data, assertion.Path)
	result.Actual = fmt.Sprintf("%v", value)

	result.Passed = compareValues(value, assertion.Operator, assertion.Value)
	if !result.Passed {
		result.Error = fmt.Sprintf("expected %s %s, got %v", assertion.Operator, assertion.Value, value)
	}
}

func extractJSONPath(data interface{}, path string) interface{} {
	if path == "$" || path == "" {
		return data
	}

	parts := strings.Split(strings.TrimPrefix(path, "$."), ".")
	current := data

	for _, part := range parts {
		if current == nil {
			return nil
		}

		if strings.Contains(part, "[") {
			current = extractArrayIndex(current, part)
		} else {
			switch v := current.(type) {
			case map[string]interface{}:
				current = v[part]
			default:
				return nil
			}
		}
	}

	return current
}

func extractArrayIndex(data interface{}, part string) interface{} {
	re := regexp.MustCompile(`(\w+)\[(\d+)\]`)
	matches := re.FindStringSubmatch(part)

	if len(matches) != 3 {
		return nil
	}

	key := matches[1]
	index, _ := strconv.Atoi(matches[2])

	if m, ok := data.(map[string]interface{}); ok {
		if arr, ok := m[key].([]interface{}); ok && index < len(arr) {
			return arr[index]
		}
	}

	return nil
}

func (e *Engine) evaluateXPath(assertion *model.Assertion, body string, result *model.AssertionResult) {
	var xmlData map[string]interface{}
	if err := xml.Unmarshal([]byte(body), &xmlData); err != nil {
		result.Error = fmt.Sprintf("invalid XML: %v", err)
		return
	}

	value := extractXPath(xmlData, assertion.Path)
	result.Actual = fmt.Sprintf("%v", value)

	result.Passed = compareValues(value, assertion.Operator, assertion.Value)
	if !result.Passed {
		result.Error = fmt.Sprintf("expected %s %s, got %v", assertion.Operator, assertion.Value, value)
	}
}

func extractXPath(data map[string]interface{}, path string) interface{} {
	path = strings.TrimPrefix(path, "/")
	parts := strings.Split(path, "/")

	var current interface{} = data

	for _, part := range parts {
		if current == nil {
			return nil
		}

		if m, ok := current.(map[string]interface{}); ok {
			current = m[part]
		} else {
			return nil
		}
	}

	return current
}

func (e *Engine) evaluateContains(assertion *model.Assertion, body string, result *model.AssertionResult) {
	result.Actual = body
	result.Passed = strings.Contains(body, assertion.Value)

	if !result.Passed {
		result.Error = fmt.Sprintf("body does not contain '%s'", assertion.Value)
	}
}

func (e *Engine) evaluateRegex(assertion *model.Assertion, body string, result *model.AssertionResult) {
	re, err := regexp.Compile(assertion.Value)
	if err != nil {
		result.Error = fmt.Sprintf("invalid regex: %v", err)
		return
	}

	result.Actual = body
	result.Passed = re.MatchString(body)

	if !result.Passed {
		result.Error = fmt.Sprintf("body does not match regex '%s'", assertion.Value)
	}
}

func compareValues(actual interface{}, operator string, expected string) bool {
	actualStr := fmt.Sprintf("%v", actual)

	switch operator {
	case "==", "equals":
		return actualStr == expected
	case "!=", "not_equals":
		return actualStr != expected
	case ">":
		actualNum, err1 := strconv.ParseFloat(actualStr, 64)
		expectedNum, err2 := strconv.ParseFloat(expected, 64)
		if err1 != nil || err2 != nil {
			return actualStr > expected
		}
		return actualNum > expectedNum
	case ">=":
		actualNum, err1 := strconv.ParseFloat(actualStr, 64)
		expectedNum, err2 := strconv.ParseFloat(expected, 64)
		if err1 != nil || err2 != nil {
			return actualStr >= expected
		}
		return actualNum >= expectedNum
	case "<":
		actualNum, err1 := strconv.ParseFloat(actualStr, 64)
		expectedNum, err2 := strconv.ParseFloat(expected, 64)
		if err1 != nil || err2 != nil {
			return actualStr < expected
		}
		return actualNum < expectedNum
	case "<=":
		actualNum, err1 := strconv.ParseFloat(actualStr, 64)
		expectedNum, err2 := strconv.ParseFloat(expected, 64)
		if err1 != nil || err2 != nil {
			return actualStr <= expected
		}
		return actualNum <= expectedNum
	case "contains":
		return strings.Contains(actualStr, expected)
	case "not_contains":
		return !strings.Contains(actualStr, expected)
	case "exists", "not_nil":
		return actual != nil
	case "not_exists", "is_nil":
		return actual == nil
	case "regex", "matches":
		re, err := regexp.Compile(expected)
		if err != nil {
			return false
		}
		return re.MatchString(actualStr)
	case "empty":
		return actualStr == "" || actualStr == "<nil>"
	case "not_empty":
		return actualStr != "" && actualStr != "<nil>"
	default:
		return actualStr == expected
	}
}

func AllPassed(results []model.AssertionResult) bool {
	for _, r := range results {
		if !r.Passed {
			return false
		}
	}
	return true
}
