package fixer

import (
	"nginx-lint/internal/model"
	"strconv"
	"strings"
)

type FixSuggestion struct {
	RuleID      string
	File        string
	Line        int
	Description string
	Command     string
	AutoFixable bool
}

type Fixer struct {
	suggestions []*FixSuggestion
	fileContent map[string][]string
}

func NewFixer() *Fixer {
	return &Fixer{
		suggestions: []*FixSuggestion{},
		fileContent: make(map[string][]string),
	}
}

func (f *Fixer) Suggestions() []*FixSuggestion {
	return f.suggestions
}

func (f *Fixer) GenerateFixes(errors []*model.LintError) {
	for _, e := range errors {
		fix := f.generateFix(e)
		if fix != nil {
			f.suggestions = append(f.suggestions, fix)
		}
	}
}

func (f *Fixer) generateFix(err *model.LintError) *FixSuggestion {
	switch err.RuleID {
	case "ERR_UNTERMINATED":
		return f.fixUnterminatedDirective(err)
	case "ERR_UNMATCHED_BRACE":
		return f.fixUnmatchedBrace(err)
	case "ERR_INCLUDE_NOT_FOUND":
		return f.fixIncludeNotFound(err)
	case "SEC_WEAK_SSL_PROTOCOL":
		return f.fixWeakSSLProtocol(err)
	case "SEC_NO_SSL_PROTOCOLS":
		return f.fixMissingSSLProtocols(err)
	case "SEC_NO_SSL_CIPHERS":
		return f.fixMissingSSLCiphers(err)
	case "SEC_NO_PREFER_SERVER_CIPHERS":
		return f.fixPreferServerCiphers(err)
	case "SEC_NO_HTTPS":
		return f.fixNoHTTPS(err)
	case "SEC_AUTOINDEX_ON":
		return f.fixAutoindexOn(err)
	case "SEC_ACCESS_LOG_OFF":
		return f.fixAccessLogOff(err)
	case "SEC_DANGEROUS_ROOT":
		return f.fixDangerousRoot(err)
	case "SEC_SSL_MISSING_KEY":
		return f.fixMissingSSLKey(err)
	case "SEC_SSL_MISSING_CERT":
		return f.fixMissingSSLCert(err)
	case "ERR_INVALID_BOOLEAN":
		return f.fixInvalidBoolean(err)
	case "ERR_INVALID_SIZE":
		return f.fixInvalidSize(err)
	case "ERR_INVALID_TIME":
		return f.fixInvalidTime(err)
	case "ERR_INVALID_HTTP_CODE":
		return f.fixInvalidHTTPCode(err)
	default:
		return nil
	}
}

func (f *Fixer) fixUnterminatedDirective(err *model.LintError) *FixSuggestion {
	return &FixSuggestion{
		RuleID:      err.RuleID,
		File:        err.Pos.File,
		Line:        err.Pos.Line,
		Description: "在指令末尾添加分号",
		Command:     "sed -i '" + strconv.Itoa(err.Pos.Line) + "s/$/;/' " + err.Pos.File,
		AutoFixable: true,
	}
}

func (f *Fixer) fixUnmatchedBrace(err *model.LintError) *FixSuggestion {
	return &FixSuggestion{
		RuleID:      err.RuleID,
		File:        err.Pos.File,
		Line:        err.Pos.Line,
		Description: "在适当位置添加右大括号 '}'",
		Command:     "sed -i '" + strconv.Itoa(err.Pos.Line) + "a\\}' " + err.Pos.File,
		AutoFixable: false,
	}
}

func (f *Fixer) fixIncludeNotFound(err *model.LintError) *FixSuggestion {
	if err.Suggestion == "" {
		return nil
	}
	path := extractPathFromMessage(err.Message)
	if path == "" {
		return nil
	}
	return &FixSuggestion{
		RuleID:      err.RuleID,
		File:        err.Pos.File,
		Line:        err.Pos.Line,
		Description: "创建缺失的include文件",
		Command:     "touch " + path,
		AutoFixable: true,
	}
}

func (f *Fixer) fixWeakSSLProtocol(err *model.LintError) *FixSuggestion {
	proto := extractWeakProtocol(err.Message)
	if proto == "" {
		proto = "SSLv[23]|TLSv1\\.1?"
	}
	return &FixSuggestion{
		RuleID:      err.RuleID,
		File:        err.Pos.File,
		Line:        err.Pos.Line,
		Description: "移除弱SSL协议，仅保留TLSv1.2和TLSv1.3",
		Command:     "sed -i 's/\\b" + proto + "\\b//g' " + err.Pos.File + " && sed -i '/ssl_protocols/s/  */ /g' " + err.Pos.File,
		AutoFixable: true,
	}
}

func (f *Fixer) fixMissingSSLProtocols(err *model.LintError) *FixSuggestion {
	return &FixSuggestion{
		RuleID:      err.RuleID,
		File:        err.Pos.File,
		Line:        err.Pos.Line,
		Description: "在server块中添加ssl_protocols指令",
		Command:     "sed -i '/ssl_certificate/a\\    ssl_protocols TLSv1.2 TLSv1.3;' " + err.Pos.File,
		AutoFixable: true,
	}
}

func (f *Fixer) fixMissingSSLCiphers(err *model.LintError) *FixSuggestion {
	return &FixSuggestion{
		RuleID:      err.RuleID,
		File:        err.Pos.File,
		Line:        err.Pos.Line,
		Description: "在server块中添加ssl_ciphers指令",
		Command:     "sed -i '/ssl_protocols/a\\    ssl_ciphers HIGH:!aNULL:!MD5;' " + err.Pos.File,
		AutoFixable: true,
	}
}

func (f *Fixer) fixPreferServerCiphers(err *model.LintError) *FixSuggestion {
	return &FixSuggestion{
		RuleID:      err.RuleID,
		File:        err.Pos.File,
		Line:        err.Pos.Line,
		Description: "启用ssl_prefer_server_ciphers",
		Command:     "sed -i '/ssl_ciphers/a\\    ssl_prefer_server_ciphers on;' " + err.Pos.File,
		AutoFixable: true,
	}
}

func (f *Fixer) fixNoHTTPS(err *model.LintError) *FixSuggestion {
	return &FixSuggestion{
		RuleID:      err.RuleID,
		File:        err.Pos.File,
		Line:        err.Pos.Line,
		Description: "添加HTTPS server配置（需提供证书路径）",
		Command:     "参考模板: server { listen 443 ssl; server_name _; ssl_certificate /path/to/cert.pem; ssl_certificate_key /path/to/key.pem; ssl_protocols TLSv1.2 TLSv1.3; ssl_ciphers HIGH:!aNULL:!MD5; }",
		AutoFixable: false,
	}
}

func (f *Fixer) fixAutoindexOn(err *model.LintError) *FixSuggestion {
	return &FixSuggestion{
		RuleID:      err.RuleID,
		File:        err.Pos.File,
		Line:        err.Pos.Line,
		Description: "关闭autoindex",
		Command:     "sed -i '" + strconv.Itoa(err.Pos.Line) + "s/autoindex on/autoindex off/' " + err.Pos.File,
		AutoFixable: true,
	}
}

func (f *Fixer) fixAccessLogOff(err *model.LintError) *FixSuggestion {
	return &FixSuggestion{
		RuleID:      err.RuleID,
		File:        err.Pos.File,
		Line:        err.Pos.Line,
		Description: "启用access_log",
		Command:     "sed -i '" + strconv.Itoa(err.Pos.Line) + "s/access_log off/access_log \\/var\\/log\\/nginx\\/access.log/' " + err.Pos.File,
		AutoFixable: true,
	}
}

func (f *Fixer) fixDangerousRoot(err *model.LintError) *FixSuggestion {
	return &FixSuggestion{
		RuleID:      err.RuleID,
		File:        err.Pos.File,
		Line:        err.Pos.Line,
		Description: "修改root为安全的Web目录",
		Command:     "sed -i '" + strconv.Itoa(err.Pos.Line) + "s|root .*|root /var/www/html;|' " + err.Pos.File,
		AutoFixable: true,
	}
}

func (f *Fixer) fixMissingSSLKey(err *model.LintError) *FixSuggestion {
	return &FixSuggestion{
		RuleID:      err.RuleID,
		File:        err.Pos.File,
		Line:        err.Pos.Line,
		Description: "添加ssl_certificate_key指令（需指定密钥文件路径）",
		Command:     "sed -i '/ssl_certificate /a\\    ssl_certificate_key /path/to/key.pem;' " + err.Pos.File,
		AutoFixable: false,
	}
}

func (f *Fixer) fixMissingSSLCert(err *model.LintError) *FixSuggestion {
	return &FixSuggestion{
		RuleID:      err.RuleID,
		File:        err.Pos.File,
		Line:        err.Pos.Line,
		Description: "添加ssl_certificate指令（需指定证书文件路径）",
		Command:     "sed -i '/ssl_certificate_key/a\\    ssl_certificate /path/to/cert.pem;' " + err.Pos.File,
		AutoFixable: false,
	}
}

func (f *Fixer) fixInvalidBoolean(err *model.LintError) *FixSuggestion {
	return &FixSuggestion{
		RuleID:      err.RuleID,
		File:        err.Pos.File,
		Line:        err.Pos.Line,
		Description: "将布尔值替换为 on 或 off",
		Command:     "sed -i '" + strconv.Itoa(err.Pos.Line) + "s/\\b" + extractArgFromMessage(err.Message) + "\\b/on/' " + err.Pos.File,
		AutoFixable: false,
	}
}

func (f *Fixer) fixInvalidSize(err *model.LintError) *FixSuggestion {
	return &FixSuggestion{
		RuleID:      err.RuleID,
		File:        err.Pos.File,
		Line:        err.Pos.Line,
		Description: "修正大小值格式",
		Command:     "检查第 " + strconv.Itoa(err.Pos.Line) + " 行的大小值，使用格式如 10m, 1g",
		AutoFixable: false,
	}
}

func (f *Fixer) fixInvalidTime(err *model.LintError) *FixSuggestion {
	return &FixSuggestion{
		RuleID:      err.RuleID,
		File:        err.Pos.File,
		Line:        err.Pos.Line,
		Description: "修正时间值格式",
		Command:     "检查第 " + strconv.Itoa(err.Pos.Line) + " 行的时间值，使用格式如 30s, 5m, 1h",
		AutoFixable: false,
	}
}

func (f *Fixer) fixInvalidHTTPCode(err *model.LintError) *FixSuggestion {
	return &FixSuggestion{
		RuleID:      err.RuleID,
		File:        err.Pos.File,
		Line:        err.Pos.Line,
		Description: "修正HTTP状态码为100-599之间的有效值",
		Command:     "检查第 " + strconv.Itoa(err.Pos.Line) + " 行的return指令状态码",
		AutoFixable: false,
	}
}

func GenerateFixes(errors []*model.LintError) []*FixSuggestion {
	fixer := NewFixer()
	fixer.GenerateFixes(errors)
	return fixer.Suggestions()
}

func FormatFixScript(suggestions []*FixSuggestion) string {
	var sb strings.Builder
	sb.WriteString("#!/bin/bash\n")
	sb.WriteString("# Nginx 配置自动修复脚本\n")
	sb.WriteString("# 由 nginx-lint 自动生成\n")
	sb.WriteString("# 请在执行前备份配置文件！\n")
	sb.WriteString("set -e\n\n")
	sb.WriteString("echo '开始修复 Nginx 配置...'\n\n")

	autoFixCount := 0
	for _, fix := range suggestions {
		if fix.AutoFixable {
			autoFixCount++
			sb.WriteString("# 修复 [" + fix.RuleID + "] " + fix.Description + "\n")
			sb.WriteString(fix.Command + "\n\n")
		}
	}

	if autoFixCount == 0 {
		sb.WriteString("# 没有可自动修复的问题\n")
	}

	sb.WriteString("echo '修复完成，请运行 nginx -t 验证配置'\n")
	return sb.String()
}

func FormatFixSummary(suggestions []*FixSuggestion) string {
	var sb strings.Builder

	autoCount := 0
	manualCount := 0
	for _, fix := range suggestions {
		if fix.AutoFixable {
			autoCount++
		} else {
			manualCount++
		}
	}

	sb.WriteString("修复建议摘要:\n")
	sb.WriteString("  可自动修复: " + strconv.Itoa(autoCount) + " 项\n")
	sb.WriteString("  需手动修复: " + strconv.Itoa(manualCount) + " 项\n\n")

	if autoCount > 0 {
		sb.WriteString("可自动修复的项目:\n")
		for _, fix := range suggestions {
			if fix.AutoFixable {
				sb.WriteString("  [" + fix.RuleID + "] " + fix.File + ":" + strconv.Itoa(fix.Line) + " - " + fix.Description + "\n")
				sb.WriteString("    命令: " + fix.Command + "\n")
			}
		}
	}

	if manualCount > 0 {
		sb.WriteString("\n需手动修复的项目:\n")
		for _, fix := range suggestions {
			if !fix.AutoFixable {
				sb.WriteString("  [" + fix.RuleID + "] " + fix.File + ":" + strconv.Itoa(fix.Line) + " - " + fix.Description + "\n")
				sb.WriteString("    参考: " + fix.Command + "\n")
			}
		}
	}

	return sb.String()
}

func extractPathFromMessage(msg string) string {
	parts := strings.Split(msg, ": ")
	if len(parts) >= 2 {
		return strings.TrimSpace(parts[len(parts)-1])
	}
	return ""
}

func extractWeakProtocol(msg string) string {
	protocols := []string{"SSLv2", "SSLv3", "TLSv1", "TLSv1.1"}
	for _, p := range protocols {
		if strings.Contains(msg, p) {
			return p
		}
	}
	return ""
}

func extractArgFromMessage(msg string) string {
	start := strings.Index(msg, "'")
	end := strings.LastIndex(msg, "'")
	if start >= 0 && end > start {
		return msg[start+1 : end]
	}
	return ""
}


