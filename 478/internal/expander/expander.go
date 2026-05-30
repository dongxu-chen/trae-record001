package expander

import (
	"nginx-lint/internal/model"
	"regexp"
	"strconv"
	"strings"
)

type VariableExpander struct {
	context      *model.ConfigContext
	errors       []*model.LintError
	definedVars  map[string]*model.Variable
}

var builtinVariables = map[string]bool{
	"arg_":                      true,
	"args":                      true,
	"binary_remote_addr":        true,
	"body_bytes_sent":           true,
	"bytes_sent":                true,
	"connection":                true,
	"connection_requests":       true,
	"content_length":            true,
	"content_type":              true,
	"cookie_":                   true,
	"document_root":             true,
	"document_uri":              true,
	"fastcgi_path_info":         true,
	"fastcgi_script_name":       true,
	"gzip_ratio":                true,
	"host":                      true,
	"hostname":                  true,
	"http_":                     true,
	"https":                     true,
	"is_args":                   true,
	"limit_rate":                true,
	"msec":                      true,
	"nginx_version":             true,
	"pid":                       true,
	"pipe":                      true,
	"proxy_add_x_forwarded_for": true,
	"proxy_host":                true,
	"proxy_port":                true,
	"proxy_protocol_addr":       true,
	"proxy_protocol_port":       true,
	"query_string":              true,
	"realpath_root":             true,
	"remote_addr":               true,
	"remote_port":               true,
	"remote_user":               true,
	"request":                   true,
	"request_body":              true,
	"request_body_file":         true,
	"request_completion":        true,
	"request_filename":          true,
	"request_id":                true,
	"request_length":            true,
	"request_method":            true,
	"request_time":              true,
	"request_uri":               true,
	"scheme":                    true,
	"sent_http_":                true,
	"sent_trailer_":             true,
	"server_addr":               true,
	"server_name":               true,
	"server_port":               true,
	"server_protocol":           true,
	"session_log_binary_id":     true,
	"session_log_id":            true,
	"ssl_cipher":                true,
	"ssl_ciphers":               true,
	"ssl_client_cert":           true,
	"ssl_client_escaped_cert":   true,
	"ssl_client_fingerprint":    true,
	"ssl_client_i_dn":           true,
	"ssl_client_raw_cert":       true,
	"ssl_client_s_dn":           true,
	"ssl_client_serial":         true,
	"ssl_client_v_end":          true,
	"ssl_client_v_remain":       true,
	"ssl_client_v_start":        true,
	"ssl_client_verify":         true,
	"ssl_curves":                true,
	"ssl_early_data":            true,
	"ssl_preread_alpn_protocols": true,
	"ssl_preread_protocol":      true,
	"ssl_preread_server_name":   true,
	"ssl_protocol":              true,
	"ssl_server_name":           true,
	"ssl_session_id":            true,
	"ssl_session_reused":        true,
	"status":                    true,
	"tcpinfo_rtt":               true,
	"tcpinfo_rttvar":            true,
	"tcpinfo_snd_cwnd":          true,
	"tcpinfo_rcv_space":         true,
	"time_iso8601":              true,
	"time_local":                true,
	"upstream_addr":             true,
	"upstream_bytes_received":   true,
	"upstream_bytes_sent":       true,
	"upstream_cache_status":     true,
	"upstream_connect_time":     true,
	"upstream_header_time":      true,
	"upstream_http_":            true,
	"upstream_response_length":  true,
	"upstream_response_time":    true,
	"upstream_status":           true,
	"uri":                       true,
}

var variableRegex = regexp.MustCompile(`\$\{?([a-zA-Z_][a-zA-Z0-9_]*)\}?`)

func NewVariableExpander(ctx *model.ConfigContext) *VariableExpander {
	return &VariableExpander{
		context:     ctx,
		errors:      []*model.LintError{},
		definedVars: make(map[string]*model.Variable),
	}
}

func (ve *VariableExpander) Errors() []*model.LintError {
	return ve.errors
}

func (ve *VariableExpander) Process(nodes []*model.Node) {
	ve.collectAllDefinitions(nodes)
	ve.mergeIntoContext()
	ve.checkAllReferences(nodes)
}

func (ve *VariableExpander) collectAllDefinitions(nodes []*model.Node) {
	ve.collectDefinitionsRecursive(nodes)
}

func (ve *VariableExpander) collectDefinitionsRecursive(nodes []*model.Node) {
	for _, node := range nodes {
		ve.collectFromNode(node)
		if node.Type == model.NodeBlock && len(node.Children) > 0 {
			ve.collectDefinitionsRecursive(node.Children)
		}
	}
}

func (ve *VariableExpander) collectFromNode(node *model.Node) {
	if node.Type == model.NodeDirective || node.Type == model.NodeInclude {
		switch node.Directive {
		case "set":
			ve.collectSetVariable(node)
		case "map":
			ve.collectMapVariable(node)
		case "geo":
			ve.collectGeoVariable(node)
		case "split_clients":
			ve.collectSplitClientsVariable(node)
		case "limit_req_zone":
			ve.collectLimitReqZoneVariable(node)
		}
	}
}

func (ve *VariableExpander) collectSetVariable(node *model.Node) {
	if len(node.Arguments) < 2 {
		return
	}
	varName := extractVarName(node.Arguments[0])
	if varName == "" {
		return
	}
	pos := node.Pos
	if existing, ok := ve.definedVars[varName]; ok {
		ve.addWarning(node.Pos, "WARN_VAR_REDEFINED",
			"变量重新定义: $"+varName,
			"变量已在 "+formatPosition(*existing.Definition)+" 定义，检查是否需要重新赋值",
			existing.Definition)
	} else {
		ve.definedVars[varName] = &model.Variable{
			Name:       varName,
			Definition: &pos,
			IsBuiltin:  false,
		}
	}
}

func (ve *VariableExpander) collectMapVariable(node *model.Node) {
	if len(node.Arguments) < 2 {
		return
	}
	varName := extractVarName(node.Arguments[1])
	if varName == "" {
		return
	}
	pos := node.Pos
	ve.definedVars[varName] = &model.Variable{
		Name:       varName,
		Definition: &pos,
		IsBuiltin:  false,
	}
	if node.Type == model.NodeBlock && len(node.Children) > 0 {
		for _, child := range node.Children {
			if child.Type == model.NodeDirective && len(child.Arguments) >= 2 {
				valueVarName := extractVarName(child.Arguments[1])
				if valueVarName != "" {
					if _, exists := ve.definedVars[valueVarName]; !exists {
						childPos := child.Pos
						ve.definedVars[valueVarName] = &model.Variable{
							Name:       valueVarName,
							Definition: &childPos,
							IsBuiltin:  false,
						}
					}
				}
			}
		}
	}
}

func (ve *VariableExpander) collectGeoVariable(node *model.Node) {
	if len(node.Arguments) < 2 {
		return
	}
	varName := extractVarName(node.Arguments[1])
	if varName == "" {
		return
	}
	pos := node.Pos
	ve.definedVars[varName] = &model.Variable{
		Name:       varName,
		Definition: &pos,
		IsBuiltin:  false,
	}
}

func (ve *VariableExpander) collectSplitClientsVariable(node *model.Node) {
	if len(node.Arguments) < 2 {
		return
	}
	varName := extractVarName(node.Arguments[1])
	if varName == "" {
		return
	}
	pos := node.Pos
	ve.definedVars[varName] = &model.Variable{
		Name:       varName,
		Definition: &pos,
		IsBuiltin:  false,
	}
}

func (ve *VariableExpander) collectLimitReqZoneVariable(node *model.Node) {
	if len(node.Arguments) < 1 {
		return
	}
	keyArg := node.Arguments[0]
	varNames := variableRegex.FindAllStringSubmatch(keyArg, -1)
	for _, match := range varNames {
		varName := match[1]
		if _, exists := ve.definedVars[varName]; !exists && !ve.isBuiltinVariable(varName) {
			pos := node.Pos
			ve.definedVars[varName] = &model.Variable{
				Name:       varName,
				Definition: &pos,
				IsBuiltin:  false,
			}
		}
	}
}

func (ve *VariableExpander) mergeIntoContext() {
	for name, v := range ve.definedVars {
		ve.context.Variables[name] = v
	}
}

func (ve *VariableExpander) checkAllReferences(nodes []*model.Node) {
	ve.checkReferencesRecursive(nodes)
}

func (ve *VariableExpander) checkReferencesRecursive(nodes []*model.Node) {
	for _, node := range nodes {
		if node.Type == model.NodeDirective || node.Type == model.NodeBlock || node.Type == model.NodeInclude {
			allValues := append([]string{node.Directive}, node.Arguments...)
			for _, val := range allValues {
				ve.checkValueVariables(val, node.Pos)
			}
		}

		if node.Type == model.NodeBlock && len(node.Children) > 0 {
			ve.checkReferencesRecursive(node.Children)
		}
	}
}

func (ve *VariableExpander) checkValueVariables(value string, pos model.Position) {
	matches := variableRegex.FindAllStringSubmatch(value, -1)
	for _, match := range matches {
		varFull := match[0]
		varName := match[1]

		if ve.isBuiltinVariable(varName) {
			continue
		}

		if v, ok := ve.definedVars[varName]; ok {
			v.References = append(v.References, pos)
		} else {
			ve.addError(pos, "ERR_UNDEFINED_VAR",
				"使用了未定义的变量: "+varFull,
				"使用 set/map/geo 指令定义变量: set $"+varName+" \"value\"; 或检查变量名拼写")
		}

		if strings.HasPrefix(varFull, "${") && !strings.HasSuffix(varFull, "}") {
			ve.addError(pos, "ERR_VAR_SYNTAX",
				"变量语法错误: "+varFull,
				"使用正确的变量语法: ${variable_name}")
		}
	}
}

func (ve *VariableExpander) isBuiltinVariable(name string) bool {
	if builtinVariables[name] {
		return true
	}

	prefixes := []string{"arg_", "cookie_", "http_", "sent_http_", "sent_trailer_", "upstream_http_", "upstream_cookie_"}
	for _, prefix := range prefixes {
		if strings.HasPrefix(name, prefix) && len(name) > len(prefix) {
			return true
		}
	}

	return false
}

func extractVarName(arg string) string {
	name := strings.TrimPrefix(arg, "$")
	name = strings.Trim(name, "{}")
	return name
}

func (ve *VariableExpander) addError(pos model.Position, ruleID, msg, suggestion string) {
	ve.errors = append(ve.errors, &model.LintError{
		Pos:        pos,
		Severity:   model.SeverityError,
		RuleID:     ruleID,
		Message:    msg,
		Suggestion: suggestion,
	})
}

func (ve *VariableExpander) addWarning(pos model.Position, ruleID, msg, suggestion string, related *model.Position) {
	ve.errors = append(ve.errors, &model.LintError{
		Pos:             pos,
		Severity:        model.SeverityWarning,
		RuleID:          ruleID,
		Message:         msg,
		Suggestion:      suggestion,
		RelatedPosition: related,
	})
}

func formatPosition(pos model.Position) string {
	return pos.File + ":" + strconv.Itoa(pos.Line)
}

func CheckVariables(nodes []*model.Node, ctx *model.ConfigContext) []*model.LintError {
	expander := NewVariableExpander(ctx)
	expander.Process(nodes)
	return expander.Errors()
}
