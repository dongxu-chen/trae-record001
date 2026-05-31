package compliance

import (
	"encoding/json"
	"regexp"
	"strings"

	"gopkg.in/yaml.v3"
	"nacos-audit-tool/models"
)

type Checker struct{}

type CheckResult struct {
	Pass    bool
	Message string
	RuleName string
	Severity string
}

type SensitivePattern struct {
	Name        string
	Pattern     string
	Description string
	Severity    string
}

var BuiltinSensitivePatterns = []SensitivePattern{
	{
		Name:        "阿里云 AccessKey",
		Pattern:     `LTAI[a-zA-Z0-9]{16}`,
		Description: "检测到阿里云 AccessKey",
		Severity:    "CRITICAL",
	},
	{
		Name:        "阿里云 SecretKey",
		Pattern:     `["']?[a-zA-Z0-9+/]{30}["']?`,
		Description: "检测到可能的阿里云 SecretKey",
		Severity:    "CRITICAL",
	},
	{
		Name:        "AWS Access Key ID",
		Pattern:     `AKIA[0-9A-Z]{16}`,
		Description: "检测到 AWS Access Key ID",
		Severity:    "CRITICAL",
	},
	{
		Name:        "AWS Secret Access Key",
		Pattern:     `["']?[a-zA-Z0-9/+=]{40}["']?`,
		Description: "检测到可能的 AWS Secret Access Key",
		Severity:    "CRITICAL",
	},
	{
		Name:        "腾讯云 SecretId",
		Pattern:     `AKID[a-zA-Z0-9]{16,32}`,
		Description: "检测到腾讯云 SecretId",
		Severity:    "CRITICAL",
	},
	{
		Name:        "腾讯云 SecretKey",
		Pattern:     `["']?[a-zA-Z0-9]{32}["']?`,
		Description: "检测到可能的腾讯云 SecretKey",
		Severity:    "CRITICAL",
	},
	{
		Name:        "华为云 AK",
		Pattern:     `[A-Z0-9]{10,30}`,
		Description: "检测到可能的华为云 Access Key",
		Severity:    "HIGH",
	},
	{
		Name:        "API Key 通用模式",
		Pattern:     `api[_-]?key["']?\s*[:=]\s*["']([a-zA-Z0-9]{20,})["']`,
		Description: "检测到 API Key",
		Severity:    "HIGH",
	},
	{
		Name:        "数据库连接字符串密码",
		Pattern:     `(jdbc|mysql|postgresql|mongodb|redis):[^:]+:([^@]+)@`,
		Description: "检测到数据库连接字符串中的密码",
		Severity:    "HIGH",
	},
	{
		Name:        "RSA 私钥",
		Pattern:     `-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----`,
		Description: "检测到私钥文件",
		Severity:    "CRITICAL",
	},
	{
		Name:        "SSH 私钥",
		Pattern:     `-----BEGIN OPENSSH PRIVATE KEY-----`,
		Description: "检测到 SSH 私钥",
		Severity:    "CRITICAL",
	},
	{
		Name:        "密码弱模式",
		Pattern:     `(password|passwd|pwd|secret)["']?\s*[:=]\s*["'](123456|admin|password|root)["']`,
		Description: "检测到弱密码",
		Severity:    "HIGH",
	},
	{
		Name:        "明文手机号",
		Pattern:     `1[3-9]\d{9}`,
		Description: "检测到明文手机号",
		Severity:    "MEDIUM",
	},
	{
		Name:        "明文身份证号",
		Pattern:     `[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]`,
		Description: "检测到明文身份证号",
		Severity:    "MEDIUM",
	},
	{
		Name:        "银行卡号",
		Pattern:     `\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}`,
		Description: "检测到银行卡号",
		Severity:    "MEDIUM",
	},
}

func NewChecker() *Checker {
	return &Checker{}
}

func (c *Checker) CheckContent(content, contentType string, rules []models.ComplianceRule) []CheckResult {
	var results []CheckResult

	for _, rule := range rules {
		if !rule.IsEnabled {
			continue
		}

		pass, msg := c.checkRule(content, contentType, rule)
		results = append(results, CheckResult{
			Pass:     pass,
			Message:  msg,
			RuleName: rule.Name,
			Severity: rule.Severity,
		})
	}

	builtinResults := c.CheckBuiltinSensitiveData(content)
	results = append(results, builtinResults...)

	return results
}

func (c *Checker) CheckBuiltinSensitiveData(content string) []CheckResult {
	var results []CheckResult

	for _, pattern := range BuiltinSensitivePatterns {
		re, err := regexp.Compile(pattern.Pattern)
		if err != nil {
			continue
		}

		if re.MatchString(content) {
			matches := re.FindAllString(content, -1)
			if len(matches) > 0 {
				results = append(results, CheckResult{
					Pass:     false,
					Message:  pattern.Description + ": " + matches[0],
					RuleName: pattern.Name,
					Severity: pattern.Severity,
				})
			}
		}
	}

	return results
}

func (c *Checker) checkRule(content, contentType string, rule models.ComplianceRule) (bool, string) {
	switch rule.RuleType {
	case "regex":
		return c.checkRegex(content, rule.Pattern)
	case "required_key":
		return c.checkRequiredKey(content, contentType, rule.Pattern)
	case "forbidden_key":
		return c.checkForbiddenKey(content, contentType, rule.Pattern)
	case "password_strength":
		return c.checkPasswordStrength(content, rule.Pattern)
	case "sensitive_data":
		return c.checkCustomSensitiveData(content, rule.Pattern)
	default:
		return true, ""
	}
}

func (c *Checker) checkRegex(content, pattern string) (bool, string) {
	re, err := regexp.Compile(pattern)
	if err != nil {
		return false, "正则表达式编译失败: " + err.Error()
	}

	if !re.MatchString(content) {
		return false, "内容不符合正则规则: " + pattern
	}
	return true, ""
}

func (c *Checker) checkRequiredKey(content, contentType, keyPath string) (bool, string) {
	keys := parseKeyPath(keyPath)
	var data map[string]interface{}

	var err error
	switch contentType {
	case "json":
		err = json.Unmarshal([]byte(content), &data)
	case "yaml", "yml":
		err = yaml.Unmarshal([]byte(content), &data)
	default:
		return true, ""
	}

	if err != nil {
		return false, "解析配置失败: " + err.Error()
	}

	if !hasNestedKey(data, keys) {
		return false, "缺少必需的配置项: " + keyPath
	}
	return true, ""
}

func (c *Checker) checkForbiddenKey(content, contentType, keyPath string) (bool, string) {
	keys := parseKeyPath(keyPath)
	var data map[string]interface{}

	var err error
	switch contentType {
	case "json":
		err = json.Unmarshal([]byte(content), &data)
	case "yaml", "yml":
		err = yaml.Unmarshal([]byte(content), &data)
	default:
		return true, ""
	}

	if err != nil {
		return true, ""
	}

	if hasNestedKey(data, keys) {
		return false, "存在禁止的配置项: " + keyPath
	}
	return true, ""
}

func (c *Checker) checkPasswordStrength(content, pattern string) (bool, string) {
	passwordPatterns := []string{
		`password["']?\s*[:=]\s*["']([^"']+)["']`,
		`passwd["']?\s*[:=]\s*["']([^"']+)["']`,
	}

	weakPatterns := []string{
		`^[0-9]+$`,
		`^[a-zA-Z]+$`,
		`^.{1,7}$`,
		`123456`,
		`password`,
		`admin`,
	}

	for _, pp := range passwordPatterns {
		re := regexp.MustCompile(pp)
		matches := re.FindAllStringSubmatch(content, -1)
		for _, match := range matches {
			if len(match) > 1 {
				pwd := match[1]
				for _, wp := range weakPatterns {
					if matched, _ := regexp.MatchString(wp, pwd); matched {
						return false, "检测到弱密码: " + pwd
					}
				}
			}
		}
	}

	return true, ""
}

func parseKeyPath(path string) []string {
	return strings.Split(path, ".")
}

func (c *Checker) checkCustomSensitiveData(content, pattern string) (bool, string) {
	re, err := regexp.Compile(pattern)
	if err != nil {
		return false, "正则表达式编译失败: " + err.Error()
	}

	if re.MatchString(content) {
		matches := re.FindAllString(content, -1)
		if len(matches) > 0 {
			return false, "检测到敏感数据: " + matches[0]
		}
	}
	return true, ""
}

func hasNestedKey(data map[string]interface{}, keys []string) bool {
	if len(keys) == 0 {
		return true
	}

	value, ok := data[keys[0]]
	if !ok {
		return false
	}

	if len(keys) == 1 {
		return true
	}

	if nested, ok := value.(map[string]interface{}); ok {
		return hasNestedKey(nested, keys[1:])
	}

	return false
}
