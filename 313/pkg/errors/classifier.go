package errors

import (
	"fmt"
	"regexp"
	"strings"
	"time"
)

type ErrorType string

const (
	ErrorTypeCompile         ErrorType = "compile_error"
	ErrorTypeTestFailed      ErrorType = "test_failed"
	ErrorTypeNetwork         ErrorType = "network_error"
	ErrorTypeTimeout         ErrorType = "timeout"
	ErrorTypeResource        ErrorType = "resource_exhausted"
	ErrorTypeConfig          ErrorType = "config_error"
	ErrorTypeDependency      ErrorType = "dependency_error"
	ErrorTypeInfrastructure  ErrorType = "infrastructure_error"
	ErrorTypeUnknown         ErrorType = "unknown"
)

type ErrorClassification struct {
	Type        ErrorType
	Retryable   bool
	Severity    string
	Description string
	Pattern     string
}

type ErrorClassifier struct {
	patterns       map[ErrorType][]*regexp.Regexp
	retryableTypes map[ErrorType]bool
}

func NewErrorClassifier() *ErrorClassifier {
	ec := &ErrorClassifier{
		patterns:       make(map[ErrorType][]*regexp.Regexp),
		retryableTypes: make(map[ErrorType]bool),
	}

	ec.registerPattern(ErrorTypeCompile, []string{
		`(?i)compil(e|ation)`,
		`(?i)syntax error`,
		`(?i)undefined symbol`,
		`(?i)type error`,
		`(?i)cannot find`,
		`(?i)no such file or directory.*\.go`,
		`(?i)import error`,
		`(?i)package .* not found`,
		`(?i)missing .* module`,
		`(?i)\berror\b.*\.go:\d+`,
		`(?i)build failed`,
		`(?i)gradle build failed`,
		`(?i)maven build failed`,
		`(?i)npm run build failed`,
		`(?i)webpack failed`,
		`(?i)typescript error`,
		`(?i)java: cannot find symbol`,
		`(?i)error: cannot find symbol`,
		`(?i)exception in thread "main" java\.lang`,
	})

	ec.registerPattern(ErrorTypeTestFailed, []string{
		`(?i)test.*fail(ed)?`,
		`(?i)assertion failed`,
		`(?i)expected.*but was`,
		`(?i)FAIL.*\[`,
		`(?i)tests failed`,
		`(?i)unit test.*fail`,
		`(?i)integration test.*fail`,
	})

	ec.registerPattern(ErrorTypeNetwork, []string{
		`(?i)connection refused`,
		`(?i)connection timed out`,
		`(?i)no route to host`,
		`(?i)host unreachable`,
		`(?i)network is unreachable`,
		`(?i)name or service not known`,
		`(?i)dns.*error`,
		`(?i)tls handshake timeout`,
		`(?i)i/o timeout`,
		`(?i)download failed`,
		`(?i)failed to fetch`,
		`(?i)failed to pull`,
		`(?i)image pull failed`,
	})

	ec.registerPattern(ErrorTypeTimeout, []string{
		`(?i)time.?out`,
		`(?i)deadline exceeded`,
		`(?i)context deadline exceeded`,
		`(?i)operation timed out`,
	})

	ec.registerPattern(ErrorTypeResource, []string{
		`(?i)out of memory`,
		`(?i)OOM`,
		`(?i)memory limit exceeded`,
		`(?i)cpu limit exceeded`,
		`(?i)disk quota exceeded`,
		`(?i)no space left`,
		`(?i)insufficient resources`,
		`(?i)resource temporarily unavailable`,
		`(?i)too many open files`,
	})

	ec.registerPattern(ErrorTypeConfig, []string{
		`(?i)config.*error`,
		`(?i)configuration error`,
		`(?i)invalid config`,
		`(?i)missing required`,
		`(?i)unknown option`,
		`(?i)invalid value`,
	})

	ec.registerPattern(ErrorTypeDependency, []string{
		`(?i)dependency.*error`,
		`(?i)failed to resolve dependency`,
		`(?i)version conflict`,
		`(?i)incompatible version`,
		`(?i)cannot resolve`,
		`(?i)could not find.*dependency`,
	})

	ec.registerPattern(ErrorTypeInfrastructure, []string{
		`(?i)server error`,
		`(?i)internal server error`,
		`(?i)service unavailable`,
		`(?i)gateway timeout`,
		`(?i)bad gateway`,
		`(?i)etcdserver`,
		`(?i)kubernetes.*error`,
		`(?i)pod.*failed`,
		`(?i)scheduler.*error`,
	})

	ec.retryableTypes[ErrorTypeNetwork] = true
	ec.retryableTypes[ErrorTypeTimeout] = true
	ec.retryableTypes[ErrorTypeResource] = true
	ec.retryableTypes[ErrorTypeInfrastructure] = true
	ec.retryableTypes[ErrorTypeDependency] = true

	ec.retryableTypes[ErrorTypeCompile] = false
	ec.retryableTypes[ErrorTypeTestFailed] = false
	ec.retryableTypes[ErrorTypeConfig] = false

	return ec
}

func (ec *ErrorClassifier) registerPattern(errorType ErrorType, patterns []string) {
	for _, pattern := range patterns {
		re, err := regexp.Compile(pattern)
		if err == nil {
			ec.patterns[errorType] = append(ec.patterns[errorType], re)
		}
	}
}

func (ec *ErrorClassifier) Classify(errorMsg string) *ErrorClassification {
	errorMsg = strings.TrimSpace(errorMsg)
	if errorMsg == "" {
		return &ErrorClassification{
			Type:        ErrorTypeUnknown,
			Retryable:   true,
			Severity:    "low",
			Description: "No error message provided",
		}
	}

	errorLines := strings.Split(errorMsg, "\n")
	allText := strings.ToLower(errorMsg)

	type matchResult struct {
		errorType ErrorType
		matches   int
		pattern   string
	}

	matches := make([]matchResult, 0)

	for errorType, patterns := range ec.patterns {
		count := 0
		matchedPattern := ""
		for _, re := range patterns {
			for _, line := range errorLines {
				if re.MatchString(line) {
					count++
					matchedPattern = re.String()
					break
				}
			}
			if count > 0 {
				break
			}
		}
		if count > 0 {
			matches = append(matches, matchResult{
				errorType: errorType,
				matches:   count,
				pattern:   matchedPattern,
			})
		}
	}

	if len(matches) == 0 {
		return &ErrorClassification{
			Type:        ErrorTypeUnknown,
			Retryable:   true,
			Severity:    "medium",
			Description: "Unknown error type",
		}
	}

	typePriority := map[ErrorType]int{
		ErrorTypeCompile:        10,
		ErrorTypeTestFailed:     9,
		ErrorTypeConfig:         8,
		ErrorTypeResource:       7,
		ErrorTypeNetwork:        6,
		ErrorTypeTimeout:        5,
		ErrorTypeDependency:     4,
		ErrorTypeInfrastructure: 3,
		ErrorTypeUnknown:        0,
	}

	bestMatch := matches[0]
	for _, m := range matches[1:] {
		if typePriority[m.errorType] > typePriority[bestMatch.errorType] {
			bestMatch = m
		}
	}

	retryable := ec.retryableTypes[bestMatch.errorType]
	severity := getSeverity(bestMatch.errorType)

	return &ErrorClassification{
		Type:        bestMatch.errorType,
		Retryable:   retryable,
		Severity:    severity,
		Description: getDescription(bestMatch.errorType),
		Pattern:     bestMatch.pattern,
	}
}

func (ec *ErrorClassifier) IsRetryable(errorMsg string) bool {
	classification := ec.Classify(errorMsg)
	return classification.Retryable
}

func (ec *ErrorClassifier) IsCompileError(errorMsg string) bool {
	return ec.Classify(errorMsg).Type == ErrorTypeCompile
}

func (ec *ErrorClassifier) IsTestFailure(errorMsg string) bool {
	return ec.Classify(errorMsg).Type == ErrorTypeTestFailed
}

func getSeverity(errorType ErrorType) string {
	switch errorType {
	case ErrorTypeCompile, ErrorTypeTestFailed, ErrorTypeConfig:
		return "high"
	case ErrorTypeResource, ErrorTypeInfrastructure:
		return "medium"
	default:
		return "low"
	}
}

func getDescription(errorType ErrorType) string {
	switch errorType {
	case ErrorTypeCompile:
		return "编译错误：代码语法或类型错误，需要修复源代码"
	case ErrorTypeTestFailed:
		return "测试失败：单元测试或集成测试未通过"
	case ErrorTypeNetwork:
		return "网络错误：网络连接或下载失败，可重试"
	case ErrorTypeTimeout:
		return "超时错误：操作耗时过长，可重试"
	case ErrorTypeResource:
		return "资源不足：CPU/内存/磁盘耗尽，可重试"
	case ErrorTypeConfig:
		return "配置错误：配置文件无效或缺失"
	case ErrorTypeDependency:
		return "依赖错误：依赖包下载或版本冲突，可重试"
	case ErrorTypeInfrastructure:
		return "基础设施错误：K8s或集群故障，可重试"
	default:
		return "未知错误"
	}
}

func (ec *ErrorClassification) ShouldAlert() bool {
	return ec.Severity == "high" || !ec.Retryable
}

func (ec *ErrorClassification) GetAlertMessage() string {
	alertType := ""
	switch ec.Type {
	case ErrorTypeCompile:
		alertType = "【编译错误告警】"
	case ErrorTypeTestFailed:
		alertType = "【测试失败告警】"
	case ErrorTypeConfig:
		alertType = "【配置错误告警】"
	default:
		alertType = "【错误告警】"
	}

	return fmt.Sprintf("%s %s\n类型: %s\n是否可重试: %v\n严重程度: %s\n说明: %s",
		alertType,
		time.Now().Format("2006-01-02 15:04:05"),
		ec.Type,
		ec.Retryable,
		ec.Severity,
		ec.Description)
}
