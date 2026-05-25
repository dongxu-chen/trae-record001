package errors

import (
	"testing"
)

func TestNewErrorClassifier(t *testing.T) {
	classifier := NewErrorClassifier()
	if classifier == nil {
		t.Fatal("Failed to create error classifier")
	}
	if len(classifier.patterns) == 0 {
		t.Error("Expected patterns to be registered")
	}
}

func TestClassifyCompileError(t *testing.T) {
	classifier := NewErrorClassifier()

	testCases := []string{
		"main.go:12: syntax error near unexpected token",
		"Compilation failed: undefined symbol 'foo'",
		"error: cannot find symbol in file.go:42",
		"typescript error TS2345: Argument of type",
		"gradle build failed with exit code 1",
		"Build failed: package not found: github.com/example",
	}

	for _, tc := range testCases {
		result := classifier.Classify(tc)
		if result.Type != ErrorTypeCompile {
			t.Errorf("Expected compile_error for '%s', got '%s'", tc, result.Type)
		}
		if result.Retryable {
			t.Errorf("Expected compile error to be non-retryable for '%s'", tc)
		}
	}
}

func TestClassifyTestFailure(t *testing.T) {
	classifier := NewErrorClassifier()

	testCases := []string{
		"TestMain failed: assertion failed",
		"--- FAIL: TestExample (0.01s)",
		"expected 5 but was 3",
		"Tests failed: 1 failed, 99 passed",
	}

	for _, tc := range testCases {
		result := classifier.Classify(tc)
		if result.Type != ErrorTypeTestFailed {
			t.Errorf("Expected test_failed for '%s', got '%s'", tc, result.Type)
		}
		if result.Retryable {
			t.Errorf("Expected test failure to be non-retryable for '%s'", tc)
		}
	}
}

func TestClassifyNetworkError(t *testing.T) {
	classifier := NewErrorClassifier()

	testCases := []string{
		"connection refused to port 8080",
		"Connection timed out while downloading",
		"no route to host 192.168.1.1",
		"image pull failed: name or service not known",
		"failed to fetch https://example.com",
	}

	for _, tc := range testCases {
		result := classifier.Classify(tc)
		if result.Type != ErrorTypeNetwork {
			t.Errorf("Expected network_error for '%s', got '%s'", tc, result.Type)
		}
		if !result.Retryable {
			t.Errorf("Expected network error to be retryable for '%s'", tc)
		}
	}
}

func TestClassifyTimeoutError(t *testing.T) {
	classifier := NewErrorClassifier()

	testCases := []string{
		"Operation timed out after 30s",
		"context deadline exceeded",
		"i/o timeout",
	}

	for _, tc := range testCases {
		result := classifier.Classify(tc)
		if result.Type != ErrorTypeTimeout {
			t.Errorf("Expected timeout for '%s', got '%s'", tc, result.Type)
		}
		if !result.Retryable {
			t.Errorf("Expected timeout to be retryable for '%s'", tc)
		}
	}
}

func TestClassifyResourceError(t *testing.T) {
	classifier := NewErrorClassifier()

	testCases := []string{
		"Out of memory: killed process",
		"OOMKilled: memory limit exceeded",
		"no space left on device",
		"insufficient resources to schedule pod",
	}

	for _, tc := range testCases {
		result := classifier.Classify(tc)
		if result.Type != ErrorTypeResource {
			t.Errorf("Expected resource_exhausted for '%s', got '%s'", tc, result.Type)
		}
		if !result.Retryable {
			t.Errorf("Expected resource error to be retryable for '%s'", tc)
		}
	}
}

func TestClassifyConfigError(t *testing.T) {
	classifier := NewErrorClassifier()

	testCases := []string{
		"config error: invalid YAML format",
		"Configuration error: missing required field",
		"invalid config value for key 'timeout'",
	}

	for _, tc := range testCases {
		result := classifier.Classify(tc)
		if result.Type != ErrorTypeConfig {
			t.Errorf("Expected config_error for '%s', got '%s'", tc, result.Type)
		}
		if result.Retryable {
			t.Errorf("Expected config error to be non-retryable for '%s'", tc)
		}
	}
}

func TestClassifyInfrastructureError(t *testing.T) {
	classifier := NewErrorClassifier()

	testCases := []string{
		"Internal server error (500)",
		"service unavailable",
		"kubernetes api server error",
		"502 Bad Gateway",
	}

	for _, tc := range testCases {
		result := classifier.Classify(tc)
		if result.Type != ErrorTypeInfrastructure {
			t.Errorf("Expected infrastructure_error for '%s', got '%s'", tc, result.Type)
		}
		if !result.Retryable {
			t.Errorf("Expected infrastructure error to be retryable for '%s'", tc)
		}
	}
}

func TestIsRetryable(t *testing.T) {
	classifier := NewErrorClassifier()

	if classifier.IsRetryable("syntax error in main.go") {
		t.Error("Compile error should not be retryable")
	}

	if classifier.IsRetryable("Test failed: assertion error") {
		t.Error("Test failure should not be retryable")
	}

	if !classifier.IsRetryable("connection timed out") {
		t.Error("Network error should be retryable")
	}

	if !classifier.IsRetryable("context deadline exceeded") {
		t.Error("Timeout should be retryable")
	}

	if classifier.IsRetryable("config error: missing field") {
		t.Error("Config error should not be retryable")
	}
}

func TestIsCompileError(t *testing.T) {
	classifier := NewErrorClassifier()

	if !classifier.IsCompileError("Compilation failed") {
		t.Error("Expected compile error")
	}

	if classifier.IsCompileError("connection refused") {
		t.Error("Network error should not be classified as compile error")
	}
}

func TestIsTestFailure(t *testing.T) {
	classifier := NewErrorClassifier()

	if !classifier.IsTestFailure("Test failed: expected 5 got 3") {
		t.Error("Expected test failure")
	}

	if classifier.IsTestFailure("syntax error") {
		t.Error("Compile error should not be classified as test failure")
	}
}

func TestShouldAlert(t *testing.T) {
	classifier := NewErrorClassifier()

	compileResult := classifier.Classify("syntax error")
	if !compileResult.ShouldAlert() {
		t.Error("Compile error should trigger alert")
	}

	testResult := classifier.Classify("test failed")
	if !testResult.ShouldAlert() {
		t.Error("Test failure should trigger alert")
	}

	networkResult := classifier.Classify("connection refused")
	if networkResult.ShouldAlert() {
		t.Error("Retryable network error should not trigger alert immediately")
	}
}

func TestGetSeverity(t *testing.T) {
	classifier := NewErrorClassifier()

	compileResult := classifier.Classify("syntax error")
	if compileResult.Severity != "high" {
		t.Errorf("Expected high severity for compile error, got %s", compileResult.Severity)
	}

	networkResult := classifier.Classify("connection refused")
	if networkResult.Severity != "low" {
		t.Errorf("Expected low severity for network error, got %s", networkResult.Severity)
	}

	resourceResult := classifier.Classify("out of memory")
	if resourceResult.Severity != "medium" {
		t.Errorf("Expected medium severity for resource error, got %s", resourceResult.Severity)
	}
}

func TestEmptyErrorMessage(t *testing.T) {
	classifier := NewErrorClassifier()

	result := classifier.Classify("")
	if result.Type != ErrorTypeUnknown {
		t.Errorf("Expected unknown error for empty message, got %s", result.Type)
	}
	if !result.Retryable {
		t.Error("Empty error should be retryable by default")
	}
}

func TestUnknownError(t *testing.T) {
	classifier := NewErrorClassifier()

	result := classifier.Classify("some random error message that doesn't match any pattern")
	if result.Type != ErrorTypeUnknown {
		t.Errorf("Expected unknown error, got %s", result.Type)
	}
	if !result.Retryable {
		t.Error("Unknown error should be retryable by default")
	}
}
