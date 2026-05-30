package validator

import (
	"nginx-lint/internal/model"
	"testing"
)

func TestGoodConfig(t *testing.T) {
	v := NewValidator()
	v.ResolveIncludes = false

	result, err := v.ValidateFile("../../testdata/good.conf")
	if err != nil {
		t.Fatalf("Failed to validate good.conf: %v", err)
	}

	if result.HasErrors() {
		t.Errorf("Expected no errors in good.conf, got %d errors", result.ErrorCount())
		for _, e := range result.Errors {
			t.Logf("  Error: %s:%d: %s [%s]", e.Pos.File, e.Pos.Line, e.Message, e.RuleID)
		}
	}
}

func TestBadSyntaxConfig(t *testing.T) {
	v := NewValidator()
	v.ResolveIncludes = false

	result, err := v.ValidateFile("../../testdata/bad_syntax.conf")
	if err != nil {
		t.Fatalf("Failed to validate bad_syntax.conf: %v", err)
	}

	if !result.HasErrors() {
		t.Error("Expected errors in bad_syntax.conf, got none")
	}

	foundUnterminated := false
	for _, e := range result.Errors {
		if e.RuleID == "ERR_UNTERMINATED" {
			foundUnterminated = true
		}
	}
	if !foundUnterminated {
		t.Error("Expected ERR_UNTERMINATED error for missing semicolons")
	}
}

func TestBadVariableConfig(t *testing.T) {
	v := NewValidator()
	v.ResolveIncludes = false

	result, err := v.ValidateFile("../../testdata/bad_variable.conf")
	if err != nil {
		t.Fatalf("Failed to validate bad_variable.conf: %v", err)
	}

	foundUndefined := false
	foundRedefined := false
	for _, e := range result.Errors {
		if e.RuleID == "ERR_UNDEFINED_VAR" {
			foundUndefined = true
		}
		if e.RuleID == "WARN_VAR_REDEFINED" {
			foundRedefined = true
		}
	}

	if !foundUndefined {
		t.Error("Expected ERR_UNDEFINED_VAR error for undefined variables")
	}
	if !foundRedefined {
		t.Error("Expected WARN_VAR_REDEFINED warning for redefined variable")
	}
}

func TestBadDirectiveConfig(t *testing.T) {
	v := NewValidator()
	v.ResolveIncludes = false

	result, err := v.ValidateFile("../../testdata/bad_directive.conf")
	if err != nil {
		t.Fatalf("Failed to validate bad_directive.conf: %v", err)
	}

	foundInvalidContext := false
	foundInvalidReturn := false
	for _, e := range result.Errors {
		if e.RuleID == "ERR_INVALID_CONTEXT" {
			foundInvalidContext = true
		}
		if e.RuleID == "ERR_INVALID_HTTP_CODE" {
			foundInvalidReturn = true
		}
	}

	if !foundInvalidContext {
		t.Error("Expected ERR_INVALID_CONTEXT error for misplaced directives")
	}
	if !foundInvalidReturn {
		t.Error("Expected ERR_INVALID_HTTP_CODE error for invalid return code")
	}
}

func TestThirdPartyWhitelist(t *testing.T) {
	v := NewValidator()
	v.ResolveIncludes = false

	result, err := v.ValidateFile("../../testdata/third_party.conf")
	if err != nil {
		t.Fatalf("Failed to validate third_party.conf: %v", err)
	}

	for _, e := range result.Errors {
		if e.Severity == model.SeverityError || e.Severity == model.SeverityWarning {
			if e.RuleID == "WARN_UNKNOWN_DIRECTIVE" {
				t.Errorf("Whitelist mode should not produce warnings for unknown directives, got: %s: %s", e.RuleID, e.Message)
			}
		}
	}
}

func TestThirdPartyStrictMode(t *testing.T) {
	v := NewValidator()
	v.ResolveIncludes = false
	v.StrictMode = true

	result, err := v.ValidateFile("../../testdata/third_party.conf")
	if err != nil {
		t.Fatalf("Failed to validate third_party.conf in strict mode: %v", err)
	}

	foundUnknownDirective := false
	for _, e := range result.Errors {
		if e.RuleID == "WARN_UNKNOWN_DIRECTIVE" {
			foundUnknownDirective = true
		}
	}
	if !foundUnknownDirective {
		t.Error("Strict mode should produce warnings for unknown directives")
	}
}

func TestThirdPartyShowInfo(t *testing.T) {
	v := NewValidator()
	v.ResolveIncludes = false
	v.ShowInfo = true

	result, err := v.ValidateFile("../../testdata/third_party.conf")
	if err != nil {
		t.Fatalf("Failed to validate third_party.conf with show-info: %v", err)
	}

	foundInfoDirective := false
	for _, e := range result.Errors {
		if e.RuleID == "INFO_UNKNOWN_DIRECTIVE" && e.Severity == model.SeverityInfo {
			foundInfoDirective = true
		}
	}
	if !foundInfoDirective {
		t.Error("ShowInfo mode should produce INFO entries for unknown directives")
	}
}

func TestIsNginxConfigFile(t *testing.T) {
	tests := []struct {
		path     string
		expected bool
	}{
		{"nginx.conf", true},
		{"test.conf", true},
		{"test.txt", false},
		{"test", false},
		{"conf/test.conf", true},
	}

	for _, tt := range tests {
		result := isNginxConfigFile(tt.path)
		if result != tt.expected {
			t.Errorf("isNginxConfigFile(%q) = %v, expected %v", tt.path, result, tt.expected)
		}
	}
}

func TestSecurityCheck(t *testing.T) {
	v := NewValidator()
	v.ResolveIncludes = false

	result, err := v.ValidateFile("../../testdata/bad_security.conf")
	if err != nil {
		t.Fatalf("Failed to validate bad_security.conf: %v", err)
	}

	expectedRules := map[string]bool{
		"SEC_WEAK_SSL_PROTOCOL":         false,
		"SEC_DANGEROUS_ROOT":            false,
		"SEC_SENSITIVE_PATH":            false,
		"SEC_AUTOINDEX_ON":              false,
		"SEC_ACCESS_LOG_OFF":            false,
		"SEC_SSL_MISSING_KEY":           false,
		"SEC_NO_SSL_PROTOCOLS":          false,
		"SEC_NO_PREFER_SERVER_CIPHERS":  false,
		"SEC_WEAK_CIPHER":               false,
	}

	for _, e := range result.Errors {
		if _, ok := expectedRules[e.RuleID]; ok {
			expectedRules[e.RuleID] = true
		}
	}

	for rule, found := range expectedRules {
		if !found {
			t.Errorf("Expected security rule %s to be triggered", rule)
		}
	}
}

func TestPerfAnalysis(t *testing.T) {
	v := NewValidator()
	v.ResolveIncludes = false

	result, err := v.ValidateFile("../../testdata/good.conf")
	if err != nil {
		t.Fatalf("Failed to validate good.conf: %v", err)
	}

	if result.PerfReport == nil {
		t.Fatal("Expected PerfReport to be generated")
	}

	if result.PerfReport.TotalDirectives == 0 {
		t.Error("Expected TotalDirectives > 0")
	}

	if result.PerfReport.ServerCount == 0 {
		t.Error("Expected ServerCount > 0 for good.conf")
	}

	if result.PerfReport.LocationCount == 0 {
		t.Error("Expected LocationCount > 0 for good.conf")
	}

	if result.PerfReport.EstMemoryKB == 0 {
		t.Error("Expected EstMemoryKB > 0")
	}

	if result.PerfReport.ComplexityScore == 0 {
		t.Error("Expected ComplexityScore > 0")
	}
}

func TestFixSuggestions(t *testing.T) {
	v := NewValidator()
	v.ResolveIncludes = false

	result, err := v.ValidateFile("../../testdata/bad_security.conf")
	if err != nil {
		t.Fatalf("Failed to validate bad_security.conf: %v", err)
	}

	if len(result.Fixes) == 0 {
		t.Error("Expected fix suggestions for bad_security.conf")
	}

	autoFixable := false
	for _, fix := range result.Fixes {
		if fix.AutoFixable {
			autoFixable = true
		}
	}
	if !autoFixable {
		t.Error("Expected at least one auto-fixable suggestion")
	}
}
