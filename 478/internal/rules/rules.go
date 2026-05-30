package rules

import (
	"nginx-lint/internal/model"
	"regexp"
	"strconv"
	"strings"
)

type DirectiveContext int

const (
	CtxMain DirectiveContext = 1 << iota
	CtxHttp
	CtxServer
	CtxLocation
	CtxUpstream
	CtxIf
	CtxLimitExcept
	CtxTypes
	CtxMap
	CtxGeo
	CtxMail
	CtxEvents
)

type ArgType int

const (
	ArgString ArgType = iota
	ArgNumber
	ArgBoolean
	ArgPath
	ArgRegex
	ArgSize
	ArgTime
	ArgUrl
	ArgHost
	ArgIp
)

type DirectiveRule struct {
	Name        string
	MinArgs     int
	MaxArgs     int
	Contexts    DirectiveContext
	ArgTypes    []ArgType
	IsBlock     bool
	Validator   func(*model.Node, []string) *model.LintError
	Description string
}

type RuleEngine struct {
	errors   []*model.LintError
	infos    []*model.LintError
	strict   bool
}

func NewRuleEngine() *RuleEngine {
	return &RuleEngine{
		errors: []*model.LintError{},
		infos:  []*model.LintError{},
		strict: false,
	}
}

func NewStrictRuleEngine() *RuleEngine {
	return &RuleEngine{
		errors: []*model.LintError{},
		infos:  []*model.LintError{},
		strict: true,
	}
}

func (re *RuleEngine) Errors() []*model.LintError {
	return re.errors
}

func (re *RuleEngine) Infos() []*model.LintError {
	return re.infos
}

var directiveRules = map[string]DirectiveRule{
	"worker_processes": {
		Name:        "worker_processes",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxMain,
		ArgTypes:    []ArgType{ArgString},
		Description: "设置工作进程数量",
	},
	"worker_connections": {
		Name:        "worker_connections",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxEvents,
		ArgTypes:    []ArgType{ArgNumber},
		Description: "设置每个工作进程的最大连接数",
	},
	"multi_accept": {
		Name:        "multi_accept",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxEvents,
		ArgTypes:    []ArgType{ArgBoolean},
		Description: "允许同时接受多个连接",
	},
	"error_log": {
		Name:        "error_log",
		MinArgs:     1,
		MaxArgs:     2,
		Contexts:    CtxMain | CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgPath, ArgString},
		Description: "配置错误日志",
	},
	"access_log": {
		Name:        "access_log",
		MinArgs:     1,
		MaxArgs:     3,
		Contexts:    CtxHttp | CtxServer | CtxLocation | CtxLimitExcept,
		ArgTypes:    []ArgType{ArgPath, ArgString, ArgString},
		Description: "配置访问日志",
	},
	"http": {
		Name:        "http",
		MinArgs:     0,
		MaxArgs:     0,
		Contexts:    CtxMain,
		IsBlock:     true,
		Description: "HTTP服务器配置块",
	},
	"server": {
		Name:        "server",
		MinArgs:     0,
		MaxArgs:     -1,
		Contexts:    CtxHttp | CtxUpstream,
		IsBlock:     false,
		Description: "虚拟服务器配置块或上游服务器",
		Validator:   validateServer,
	},
	"location": {
		Name:        "location",
		MinArgs:     1,
		MaxArgs:     2,
		Contexts:    CtxServer | CtxLocation,
		IsBlock:     true,
		ArgTypes:    []ArgType{ArgString, ArgString},
		Description: "位置匹配配置块",
	},
	"upstream": {
		Name:        "upstream",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp,
		IsBlock:     true,
		ArgTypes:    []ArgType{ArgString},
		Description: "上游服务器组配置块",
	},
	"events": {
		Name:        "events",
		MinArgs:     0,
		MaxArgs:     0,
		Contexts:    CtxMain,
		IsBlock:     true,
		Description: "事件配置块",
	},
	"server_name": {
		Name:        "server_name",
		MinArgs:     1,
		MaxArgs:     -1,
		Contexts:    CtxServer,
		ArgTypes:    []ArgType{ArgHost},
		Description: "设置虚拟服务器名称",
	},
	"listen": {
		Name:        "listen",
		MinArgs:     1,
		MaxArgs:     -1,
		Contexts:    CtxServer,
		ArgTypes:    []ArgType{ArgString},
		Description: "设置监听地址和端口",
		Validator:   validateListen,
	},
	"root": {
		Name:        "root",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation | CtxIf,
		ArgTypes:    []ArgType{ArgPath},
		Description: "设置文档根目录",
	},
	"index": {
		Name:        "index",
		MinArgs:     1,
		MaxArgs:     -1,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgString},
		Description: "设置默认索引文件",
	},
	"try_files": {
		Name:        "try_files",
		MinArgs:     2,
		MaxArgs:     -1,
		Contexts:    CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgPath},
		Description: "按顺序检查文件是否存在",
	},
	"return": {
		Name:        "return",
		MinArgs:     1,
		MaxArgs:     2,
		Contexts:    CtxServer | CtxLocation | CtxIf,
		ArgTypes:    []ArgType{ArgString, ArgString},
		Description: "返回响应码或重定向",
		Validator:   validateReturn,
	},
	"rewrite": {
		Name:        "rewrite",
		MinArgs:     2,
		MaxArgs:     3,
		Contexts:    CtxServer | CtxLocation | CtxIf,
		ArgTypes:    []ArgType{ArgRegex, ArgString, ArgString},
		Description: "URL重写规则",
	},
	"proxy_pass": {
		Name:        "proxy_pass",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxLocation | CtxIf | CtxLimitExcept,
		ArgTypes:    []ArgType{ArgUrl},
		Description: "设置代理服务器地址",
	},
	"proxy_set_header": {
		Name:        "proxy_set_header",
		MinArgs:     2,
		MaxArgs:     2,
		Contexts:    CtxHttp | CtxServer | CtxLocation | CtxIf,
		ArgTypes:    []ArgType{ArgString, ArgString},
		Description: "设置传递给代理服务器的请求头",
	},
	"proxy_connect_timeout": {
		Name:        "proxy_connect_timeout",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgTime},
		Description: "设置代理连接超时时间",
	},
	"proxy_read_timeout": {
		Name:        "proxy_read_timeout",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgTime},
		Description: "设置代理读取超时时间",
	},
	"proxy_send_timeout": {
		Name:        "proxy_send_timeout",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgTime},
		Description: "设置代理发送超时时间",
	},
	"fastcgi_pass": {
		Name:        "fastcgi_pass",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxLocation | CtxIf | CtxLimitExcept,
		ArgTypes:    []ArgType{ArgString},
		Description: "设置FastCGI服务器地址",
	},
	"fastcgi_param": {
		Name:        "fastcgi_param",
		MinArgs:     2,
		MaxArgs:     2,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgString, ArgString},
		Description: "设置传递给FastCGI服务器的参数",
	},
	"include": {
		Name:        "include",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxMain | CtxHttp | CtxServer | CtxLocation | CtxUpstream | CtxIf | CtxEvents,
		ArgTypes:    []ArgType{ArgPath},
		Description: "包含其他配置文件",
	},
	"types": {
		Name:        "types",
		MinArgs:     0,
		MaxArgs:     0,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		IsBlock:     true,
		Description: "MIME类型映射块",
	},
	"default_type": {
		Name:        "default_type",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgString},
		Description: "设置默认MIME类型",
	},
	"charset": {
		Name:        "charset",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation | CtxIf,
		ArgTypes:    []ArgType{ArgString},
		Description: "设置默认字符集",
	},
	"gzip": {
		Name:        "gzip",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation | CtxIf,
		ArgTypes:    []ArgType{ArgBoolean},
		Description: "启用或禁用gzip压缩",
	},
	"gzip_types": {
		Name:        "gzip_types",
		MinArgs:     1,
		MaxArgs:     -1,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgString},
		Description: "设置需要gzip压缩的MIME类型",
	},
	"client_max_body_size": {
		Name:        "client_max_body_size",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgSize},
		Description: "设置客户端请求体最大大小",
		Validator:   validateSize,
	},
	"client_body_timeout": {
		Name:        "client_body_timeout",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgTime},
		Description: "设置读取客户端请求体超时时间",
	},
	"client_header_timeout": {
		Name:        "client_header_timeout",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgTime},
		Description: "设置读取客户端请求头超时时间",
	},
	"send_timeout": {
		Name:        "send_timeout",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgTime},
		Description: "设置发送响应超时时间",
	},
	"keepalive_timeout": {
		Name:        "keepalive_timeout",
		MinArgs:     1,
		MaxArgs:     2,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgTime, ArgTime},
		Description: "设置keep-alive超时时间",
	},
	"keepalive_requests": {
		Name:        "keepalive_requests",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgNumber},
		Description: "设置一个keep-alive连接可以处理的最大请求数",
	},
	"sendfile": {
		Name:        "sendfile",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgBoolean},
		Description: "启用或禁用sendfile",
	},
	"tcp_nopush": {
		Name:        "tcp_nopush",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgBoolean},
		Description: "启用或禁用TCP_NOPUSH",
	},
	"tcp_nodelay": {
		Name:        "tcp_nodelay",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgBoolean},
		Description: "启用或禁用TCP_NODELAY",
	},
	"set": {
		Name:        "set",
		MinArgs:     2,
		MaxArgs:     2,
		Contexts:    CtxServer | CtxLocation | CtxIf,
		ArgTypes:    []ArgType{ArgString, ArgString},
		Description: "定义变量",
	},
	"map": {
		Name:        "map",
		MinArgs:     2,
		MaxArgs:     2,
		Contexts:    CtxHttp,
		IsBlock:     true,
		ArgTypes:    []ArgType{ArgString, ArgString},
		Description: "创建变量映射表",
	},
	"geo": {
		Name:        "geo",
		MinArgs:     2,
		MaxArgs:     2,
		Contexts:    CtxHttp,
		IsBlock:     true,
		ArgTypes:    []ArgType{ArgString, ArgString},
		Description: "根据IP地址创建变量",
	},
	"if": {
		Name:        "if",
		MinArgs:     1,
		MaxArgs:     -1,
		Contexts:    CtxServer | CtxLocation,
		IsBlock:     true,
		ArgTypes:    []ArgType{ArgString},
		Description: "条件判断块",
	},

	"ip_hash": {
		Name:        "ip_hash",
		MinArgs:     0,
		MaxArgs:     0,
		Contexts:    CtxUpstream,
		Description: "启用IP哈希负载均衡",
	},
	"least_conn": {
		Name:        "least_conn",
		MinArgs:     0,
		MaxArgs:     0,
		Contexts:    CtxUpstream,
		Description: "启用最少连接负载均衡",
	},
	"limit_req_zone": {
		Name:        "limit_req_zone",
		MinArgs:     3,
		MaxArgs:     3,
		Contexts:    CtxHttp,
		ArgTypes:    []ArgType{ArgString, ArgString, ArgString},
		Description: "定义请求限制区域",
	},
	"limit_req": {
		Name:        "limit_req",
		MinArgs:     1,
		MaxArgs:     -1,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgString},
		Description: "应用请求限制",
	},
	"limit_conn_zone": {
		Name:        "limit_conn_zone",
		MinArgs:     2,
		MaxArgs:     2,
		Contexts:    CtxHttp,
		ArgTypes:    []ArgType{ArgString, ArgString},
		Description: "定义连接限制区域",
	},
	"limit_conn": {
		Name:        "limit_conn",
		MinArgs:     2,
		MaxArgs:     2,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgString, ArgNumber},
		Description: "应用连接限制",
	},
	"ssl_certificate": {
		Name:        "ssl_certificate",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer,
		ArgTypes:    []ArgType{ArgPath},
		Description: "SSL证书文件路径",
	},
	"ssl_certificate_key": {
		Name:        "ssl_certificate_key",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer,
		ArgTypes:    []ArgType{ArgPath},
		Description: "SSL证书密钥文件路径",
	},
	"ssl_protocols": {
		Name:        "ssl_protocols",
		MinArgs:     1,
		MaxArgs:     -1,
		Contexts:    CtxHttp | CtxServer,
		ArgTypes:    []ArgType{ArgString},
		Description: "启用的SSL协议",
	},
	"ssl_ciphers": {
		Name:        "ssl_ciphers",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer,
		ArgTypes:    []ArgType{ArgString},
		Description: "启用的SSL加密套件",
	},
	"ssl_prefer_server_ciphers": {
		Name:        "ssl_prefer_server_ciphers",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer,
		ArgTypes:    []ArgType{ArgBoolean},
		Description: "优先使用服务器端加密套件",
	},
	"resolver": {
		Name:        "resolver",
		MinArgs:     1,
		MaxArgs:     -1,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgIp},
		Description: "DNS解析服务器",
	},
	"resolver_timeout": {
		Name:        "resolver_timeout",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgTime},
		Description: "DNS解析超时时间",
	},
	"error_page": {
		Name:        "error_page",
		MinArgs:     2,
		MaxArgs:     -1,
		Contexts:    CtxHttp | CtxServer | CtxLocation | CtxIf,
		ArgTypes:    []ArgType{ArgString},
		Description: "自定义错误页面",
	},
	"add_header": {
		Name:        "add_header",
		MinArgs:     2,
		MaxArgs:     3,
		Contexts:    CtxHttp | CtxServer | CtxLocation | CtxIf,
		ArgTypes:    []ArgType{ArgString, ArgString, ArgString},
		Description: "添加响应头",
	},
	"expires": {
		Name:        "expires",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation | CtxIf,
		ArgTypes:    []ArgType{ArgString},
		Description: "设置Expires和Cache-Control响应头",
	},
	"log_format": {
		Name:        "log_format",
		MinArgs:     2,
		MaxArgs:     -1,
		Contexts:    CtxHttp,
		ArgTypes:    []ArgType{ArgString, ArgString},
		Description: "自定义日志格式",
	},
	"pid": {
		Name:        "pid",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxMain,
		ArgTypes:    []ArgType{ArgPath},
		Description: "设置PID文件路径",
	},
	"user": {
		Name:        "user",
		MinArgs:     1,
		MaxArgs:     2,
		Contexts:    CtxMain,
		ArgTypes:    []ArgType{ArgString, ArgString},
		Description: "设置工作进程运行用户和组",
	},
	"daemon": {
		Name:        "daemon",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxMain,
		ArgTypes:    []ArgType{ArgBoolean},
		Description: "是否以守护进程方式运行",
	},
	"master_process": {
		Name:        "master_process",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxMain,
		ArgTypes:    []ArgType{ArgBoolean},
		Description: "是否启用主进程",
	},
	"autoindex": {
		Name:        "autoindex",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation,
		ArgTypes:    []ArgType{ArgBoolean},
		Description: "启用或禁用目录列表",
	},
	"auth_basic": {
		Name:        "auth_basic",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation | CtxLimitExcept,
		ArgTypes:    []ArgType{ArgString},
		Description: "启用HTTP基本认证",
	},
	"auth_basic_user_file": {
		Name:        "auth_basic_user_file",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation | CtxLimitExcept,
		ArgTypes:    []ArgType{ArgPath},
		Description: "HTTP基本认证用户文件路径",
	},
	"limit_except": {
		Name:        "limit_except",
		MinArgs:     1,
		MaxArgs:     -1,
		Contexts:    CtxLocation,
		IsBlock:     true,
		ArgTypes:    []ArgType{ArgString},
		Description: "限制特定HTTP方法之外的访问",
	},
	"allow": {
		Name:        "allow",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation | CtxLimitExcept,
		ArgTypes:    []ArgType{ArgString},
		Description: "允许访问的IP地址或网络",
	},
	"deny": {
		Name:        "deny",
		MinArgs:     1,
		MaxArgs:     1,
		Contexts:    CtxHttp | CtxServer | CtxLocation | CtxLimitExcept,
		ArgTypes:    []ArgType{ArgString},
		Description: "拒绝访问的IP地址或网络",
	},
}

var blockContexts = map[string]DirectiveContext{
	"main":        CtxMain,
	"http":        CtxHttp,
	"server":      CtxServer,
	"location":    CtxLocation,
	"upstream":    CtxUpstream,
	"if":          CtxIf,
	"limit_except": CtxLimitExcept,
	"types":       CtxTypes,
	"map":         CtxMap,
	"geo":         CtxGeo,
	"events":      CtxEvents,
}

func (re *RuleEngine) Validate(nodes []*model.Node, currentContext DirectiveContext, contextStack []string) {
	for _, node := range nodes {
		if node.Type == model.NodeComment {
			continue
		}

		rule, ok := directiveRules[node.Directive]
		if !ok {
			if re.strict {
				re.addWarning(node.Pos, "WARN_UNKNOWN_DIRECTIVE",
					"未知指令: "+node.Directive,
					"检查指令拼写，或确认该指令是否需要加载特定模块")
			} else {
				re.addInfo(node.Pos, "INFO_UNKNOWN_DIRECTIVE",
					"未知指令(可能是第三方模块): "+node.Directive,
					"如需验证此指令，请使用 -strict 模式")
			}
			if node.Type == model.NodeBlock && len(node.Children) > 0 {
				newContext := getContextForBlock(node.Directive)
				re.Validate(node.Children, newContext, append(contextStack, node.Directive))
			}
			continue
		}

		if rule.IsBlock && node.Type != model.NodeBlock {
			re.addError(node.Pos, "ERR_EXPECT_BLOCK",
				"指令 '"+node.Directive+"' 需要配置块",
				"在指令后添加 '{' 和 '}' 包裹配置内容")
			continue
		}

		if !rule.IsBlock && node.Type == model.NodeBlock {
			re.addError(node.Pos, "ERR_UNEXPECT_BLOCK",
				"指令 '"+node.Directive+"' 不应该有配置块",
				"移除多余的 '{' 和 '}'，使用分号 ';' 结束指令")
			continue
		}

		argCount := len(node.Arguments)
		if rule.MinArgs > 0 && argCount < rule.MinArgs {
			re.addError(node.Pos, "ERR_TOO_FEW_ARGS",
				"指令 '"+node.Directive+"' 缺少参数，至少需要 "+strconv.Itoa(rule.MinArgs)+" 个参数",
				"参考Nginx文档补充必要的参数")
		}
		if rule.MaxArgs > 0 && argCount > rule.MaxArgs {
			re.addError(node.Pos, "ERR_TOO_MANY_ARGS",
				"指令 '"+node.Directive+"' 参数过多，最多允许 "+strconv.Itoa(rule.MaxArgs)+" 个参数",
				"移除多余的参数")
		}

		if currentContext != CtxMain && (rule.Contexts&currentContext) == 0 {
			allowed := getAllowedContexts(rule.Contexts)
			current := "main"
			if len(contextStack) > 0 {
				current = contextStack[len(contextStack)-1]
			}
			re.addError(node.Pos, "ERR_INVALID_CONTEXT",
				"指令 '"+node.Directive+"' 不允许在 '"+current+"' 块中使用",
				"将该指令移动到允许的上下文中: "+strings.Join(allowed, ", "))
		}

		for i, arg := range node.Arguments {
			if i < len(rule.ArgTypes) {
				if err := re.validateArgument(arg, rule.ArgTypes[i], node.Pos); err != nil {
					re.errors = append(re.errors, err)
				}
			}
		}

		if rule.Validator != nil {
			if err := rule.Validator(node, contextStack); err != nil {
				re.errors = append(re.errors, err)
			}
		}

		if node.Type == model.NodeBlock && len(node.Children) > 0 {
			newContext := getContextForBlock(node.Directive)
			re.Validate(node.Children, newContext, append(contextStack, node.Directive))
		}
	}
}

func getContextForBlock(directive string) DirectiveContext {
	if ctx, ok := blockContexts[directive]; ok {
		return ctx
	}
	return CtxMain
}

func getAllowedContexts(contexts DirectiveContext) []string {
	var allowed []string
	all := []struct {
		ctx  DirectiveContext
		name string
	}{
		{CtxMain, "main"},
		{CtxHttp, "http"},
		{CtxServer, "server"},
		{CtxLocation, "location"},
		{CtxUpstream, "upstream"},
		{CtxEvents, "events"},
		{CtxIf, "if"},
	}
	for _, c := range all {
		if (contexts & c.ctx) != 0 {
			allowed = append(allowed, c.name)
		}
	}
	return allowed
}

func (re *RuleEngine) validateArgument(arg string, argType ArgType, pos model.Position) *model.LintError {
	switch argType {
	case ArgNumber:
		if _, err := strconv.Atoi(arg); err != nil {
			if _, err := strconv.ParseFloat(arg, 64); err != nil {
				return &model.LintError{
					Pos:        pos,
					Severity:   model.SeverityError,
					RuleID:     "ERR_INVALID_NUMBER",
					Message:    "参数 '" + arg + "' 不是有效的数字",
					Suggestion: "使用有效的数字值",
				}
			}
		}
	case ArgBoolean:
		argLower := strings.ToLower(arg)
		if argLower != "on" && argLower != "off" && argLower != "true" && argLower != "false" && argLower != "yes" && argLower != "no" {
			return &model.LintError{
				Pos:        pos,
				Severity:   model.SeverityError,
				RuleID:     "ERR_INVALID_BOOLEAN",
				Message:    "参数 '" + arg + "' 不是有效的布尔值",
				Suggestion: "使用 on/off, true/false, 或 yes/no",
			}
		}
	case ArgSize:
		sizeRegex := regexp.MustCompile(`^(\d+)([kKmMgG]?)$`)
		if !sizeRegex.MatchString(arg) {
			return &model.LintError{
				Pos:        pos,
				Severity:   model.SeverityError,
				RuleID:     "ERR_INVALID_SIZE",
				Message:    "参数 '" + arg + "' 不是有效的大小值",
				Suggestion: "使用有效的大小格式，如 1024, 1k, 10m",
			}
		}
	case ArgTime:
		timeRegex := regexp.MustCompile(`^(\d+)(ms|s|m|h|d|w|M|y)?$`)
		if !timeRegex.MatchString(arg) {
			return &model.LintError{
				Pos:        pos,
				Severity:   model.SeverityError,
				RuleID:     "ERR_INVALID_TIME",
				Message:    "参数 '" + arg + "' 不是有效的时间值",
				Suggestion: "使用有效的时间格式，如 30s, 1m, 2h",
			}
		}
	case ArgIp:
		ipRegex := regexp.MustCompile(`^(\d{1,3}\.){3}\d{1,3}$|^[0-9a-fA-F:]+$`)
		if !ipRegex.MatchString(arg) {
			return &model.LintError{
				Pos:        pos,
				Severity:   model.SeverityWarning,
				RuleID:     "WARN_INVALID_IP",
				Message:    "参数 '" + arg + "' 可能不是有效的IP地址",
				Suggestion: "检查IP地址格式是否正确",
			}
		}
	case ArgUrl:
		if !strings.HasPrefix(arg, "http://") && !strings.HasPrefix(arg, "https://") &&
			!strings.HasPrefix(arg, "unix:") && !strings.HasPrefix(arg, "grpcs://") &&
			!strings.HasPrefix(arg, "grpc://") {
			return &model.LintError{
				Pos:        pos,
				Severity:   model.SeverityWarning,
				RuleID:     "WARN_INVALID_URL",
				Message:    "参数 '" + arg + "' 可能不是有效的URL",
				Suggestion: "URL应以 http://, https://, unix: 等协议开头",
			}
		}
	}
	return nil
}

func validateListen(node *model.Node, contextStack []string) *model.LintError {
	arg := node.Arguments[0]
	listenRegex := regexp.MustCompile(`^(\*|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|[0-9a-fA-F:]+|\[[0-9a-fA-F:]+\])?(:\d+)?(.*)$`)
	if !listenRegex.MatchString(arg) {
		return &model.LintError{
			Pos:        node.Pos,
			Severity:   model.SeverityError,
			RuleID:     "ERR_INVALID_LISTEN",
			Message:    "listen 指令参数格式无效: " + arg,
			Suggestion: "使用正确的格式: [address]:port [options]",
		}
	}
	return nil
}

func validateServer(node *model.Node, contextStack []string) *model.LintError {
	inUpstream := false
	for _, ctx := range contextStack {
		if ctx == "upstream" {
			inUpstream = true
			break
		}
	}

	if inUpstream {
		if node.Type == model.NodeBlock {
			return &model.LintError{
				Pos:        node.Pos,
				Severity:   model.SeverityError,
				RuleID:     "ERR_UNEXPECT_BLOCK",
				Message:    "upstream 中的 'server' 不应该有配置块",
				Suggestion: "移除多余的 '{' 和 '}'，使用分号 ';' 结束指令",
			}
		}
		if len(node.Arguments) < 1 {
			return &model.LintError{
				Pos:        node.Pos,
				Severity:   model.SeverityError,
				RuleID:     "ERR_TOO_FEW_ARGS",
				Message:    "upstream 中的 'server' 缺少参数，至少需要 1 个参数",
				Suggestion: "指定服务器地址，如: server 127.0.0.1:8080;",
			}
		}
		return validateUpstreamServer(node, contextStack)
	} else {
		if node.Type != model.NodeBlock {
			return &model.LintError{
				Pos:        node.Pos,
				Severity:   model.SeverityError,
				RuleID:     "ERR_EXPECT_BLOCK",
				Message:    "http 中的 'server' 需要配置块",
				Suggestion: "在指令后添加 '{' 和 '}' 包裹配置内容",
			}
		}
		if len(node.Arguments) > 0 {
			return &model.LintError{
				Pos:        node.Pos,
				Severity:   model.SeverityError,
				RuleID:     "ERR_TOO_MANY_ARGS",
				Message:    "http 中的 'server' 不应该有参数",
				Suggestion: "移除 'server' 后的参数，使用 server_name 指令设置服务器名称",
			}
		}
	}
	return nil
}

func validateReturn(node *model.Node, contextStack []string) *model.LintError {
	arg := node.Arguments[0]
	code, err := strconv.Atoi(arg)
	if err != nil {
		if !strings.HasPrefix(arg, "http://") && !strings.HasPrefix(arg, "https://") {
			return &model.LintError{
				Pos:        node.Pos,
				Severity:   model.SeverityError,
				RuleID:     "ERR_INVALID_RETURN",
				Message:    "return 指令参数无效: " + arg,
				Suggestion: "使用HTTP状态码或完整的重定向URL",
			}
		}
		return nil
	}
	if code < 100 || code > 599 {
		return &model.LintError{
			Pos:        node.Pos,
			Severity:   model.SeverityError,
			RuleID:     "ERR_INVALID_HTTP_CODE",
			Message:    "无效的HTTP状态码: " + arg,
			Suggestion: "使用100-599之间的有效HTTP状态码",
		}
	}
	return nil
}

func validateSize(node *model.Node, contextStack []string) *model.LintError {
	arg := node.Arguments[0]
	sizeRegex := regexp.MustCompile(`^(\d+)([kKmMgG]?)$`)
	matches := sizeRegex.FindStringSubmatch(arg)
	if matches == nil {
		return &model.LintError{
			Pos:        node.Pos,
			Severity:   model.SeverityError,
			RuleID:     "ERR_INVALID_SIZE",
			Message:    "无效的大小值: " + arg,
			Suggestion: "使用有效的大小格式，如 1024, 1k, 10m",
		}
	}
	val, _ := strconv.ParseInt(matches[1], 10, 64)
	unit := strings.ToUpper(matches[2])
	switch unit {
	case "G":
		val *= 1024
		fallthrough
	case "M":
		val *= 1024
		fallthrough
	case "K":
		val *= 1024
	}
	if val == 0 {
		return &model.LintError{
			Pos:        node.Pos,
			Severity:   model.SeverityWarning,
			RuleID:     "WARN_ZERO_SIZE",
			Message:    "大小设置为0可能导致意外行为",
			Suggestion: "确认是否确实需要设置为0",
		}
	}
	return nil
}

func validateUpstreamServer(node *model.Node, contextStack []string) *model.LintError {
	arg := node.Arguments[0]
	serverRegex := regexp.MustCompile(`^([^:]+)(:\d+)?(.*)$`)
	if !serverRegex.MatchString(arg) {
		return &model.LintError{
			Pos:        node.Pos,
			Severity:   model.SeverityError,
			RuleID:     "ERR_INVALID_UPSTREAM_SERVER",
			Message:    "上游服务器地址格式无效: " + arg,
			Suggestion: "使用正确的格式: address:port [parameters]",
		}
	}
	return nil
}

func (re *RuleEngine) addError(pos model.Position, ruleID, msg, suggestion string) {
	re.errors = append(re.errors, &model.LintError{
		Pos:        pos,
		Severity:   model.SeverityError,
		RuleID:     ruleID,
		Message:    msg,
		Suggestion: suggestion,
	})
}

func (re *RuleEngine) addWarning(pos model.Position, ruleID, msg, suggestion string) {
	re.errors = append(re.errors, &model.LintError{
		Pos:        pos,
		Severity:   model.SeverityWarning,
		RuleID:     ruleID,
		Message:    msg,
		Suggestion: suggestion,
	})
}

func (re *RuleEngine) addInfo(pos model.Position, ruleID, msg, suggestion string) {
	re.infos = append(re.infos, &model.LintError{
		Pos:        pos,
		Severity:   model.SeverityInfo,
		RuleID:     ruleID,
		Message:    msg,
		Suggestion: suggestion,
	})
}

func ValidateDirectives(nodes []*model.Node) []*model.LintError {
	engine := NewRuleEngine()
	engine.Validate(nodes, CtxMain, []string{"main"})
	var all []*model.LintError
	all = append(all, engine.Errors()...)
	all = append(all, engine.Infos()...)
	return all
}

func ValidateDirectivesStrict(nodes []*model.Node) []*model.LintError {
	engine := NewStrictRuleEngine()
	engine.Validate(nodes, CtxMain, []string{"main"})
	var all []*model.LintError
	all = append(all, engine.Errors()...)
	all = append(all, engine.Infos()...)
	return all
}
