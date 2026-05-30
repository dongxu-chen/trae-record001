package security

import (
	"nginx-lint/internal/model"
	"strings"
)

type SecurityChecker struct {
	errors      []*model.LintError
	sslServers  map[string]*sslConfig
	hasServer   bool
	hasHTTPS    bool
	inServer    bool
	currentSSL  *sslConfig
	serverNames []string
}

type sslConfig struct {
	hasCert      bool
	hasCertKey   bool
	protocols    []string
	ciphers      string
	preferServer bool
	pos          model.Position
}

func NewSecurityChecker() *SecurityChecker {
	return &SecurityChecker{
		errors:     []*model.LintError{},
		sslServers: make(map[string]*sslConfig),
	}
}

func (sc *SecurityChecker) Errors() []*model.LintError {
	return sc.errors
}

func (sc *SecurityChecker) Check(nodes []*model.Node) {
	sc.checkNodes(nodes, "")
	sc.checkGlobalSecurity()
}

func (sc *SecurityChecker) checkNodes(nodes []*model.Node, blockName string) {
	for _, node := range nodes {
		if node.Type == model.NodeComment {
			continue
		}

		switch node.Directive {
		case "server":
			if node.Type == model.NodeBlock {
				sc.hasServer = true
				sc.inServer = true
				sc.currentSSL = &sslConfig{pos: node.Pos}
				sc.serverNames = nil
				sc.checkNodes(node.Children, "server")
				sc.finalizeServerSSL()
				sc.inServer = false
				continue
			}
		case "location":
			if node.Type == model.NodeBlock {
				sc.checkLocationSecurity(node)
				sc.checkNodes(node.Children, "location")
				continue
			}
		case "server_name":
			sc.serverNames = append(sc.serverNames, node.Arguments...)
		case "listen":
			sc.checkListenSecurity(node)
		case "ssl_certificate":
			if sc.currentSSL != nil {
				sc.currentSSL.hasCert = true
			}
		case "ssl_certificate_key":
			if sc.currentSSL != nil {
				sc.currentSSL.hasCertKey = true
			}
		case "ssl_protocols":
			if sc.currentSSL != nil {
				sc.currentSSL.protocols = node.Arguments
			}
			sc.checkSSLProtocols(node)
		case "ssl_ciphers":
			if sc.currentSSL != nil {
				sc.currentSSL.ciphers = strings.Join(node.Arguments, " ")
			}
			sc.checkSSLCiphers(node)
		case "ssl_prefer_server_ciphers":
			if sc.currentSSL != nil {
				sc.currentSSL.preferServer = len(node.Arguments) > 0 && node.Arguments[0] == "on"
			}
		case "root":
			sc.checkRootSecurity(node)
		case "autoindex":
			sc.checkAutoindexSecurity(node)
		case "access_log":
			sc.checkAccessLogSecurity(node)
		case "auth_basic":
			sc.checkAuthBasicSecurity(node)
		case "allow", "deny":
			sc.checkAccessControl(node)
		case "proxy_pass":
			sc.checkProxyPassSecurity(node)
		case "resolver":
			sc.checkResolverSecurity(node)
		}

		if node.Type == model.NodeBlock && node.Directive != "server" && node.Directive != "location" {
			sc.checkNodes(node.Children, blockName)
		}
	}
}

func (sc *SecurityChecker) checkListenSecurity(node *model.Node) {
	for _, arg := range node.Arguments {
		if strings.Contains(arg, "443") || strings.HasSuffix(arg, ":443") {
			sc.hasHTTPS = true
		}
		if strings.Contains(arg, "ssl") {
			sc.hasHTTPS = true
		}
	}
}

func (sc *SecurityChecker) checkSSLProtocols(node *model.Node) {
	weakProtocols := map[string]bool{
		"SSLv2": true, "SSLv3": true, "TLSv1": true, "TLSv1.1": true,
	}
	for _, arg := range node.Arguments {
		if weakProtocols[arg] {
			sc.addError(node.Pos, "SEC_WEAK_SSL_PROTOCOL",
				"使用了不安全的SSL协议: "+arg,
				"禁用弱协议，仅保留 TLSv1.2 TLSv1.3。修复命令:\n  sed -i 's/\\b"+arg+"\\b//' "+node.Pos.File)
		}
	}

	hasTLS12 := false
	hasTLS13 := false
	for _, arg := range node.Arguments {
		if arg == "TLSv1.2" {
			hasTLS12 = true
		}
		if arg == "TLSv1.3" {
			hasTLS13 = true
		}
	}
	if !hasTLS12 && !hasTLS13 {
		sc.addWarning(node.Pos, "SEC_NO_MODERN_TLS",
			"未启用TLSv1.2或TLSv1.3",
			"添加 ssl_protocols TLSv1.2 TLSv1.3;")
	}
}

func (sc *SecurityChecker) checkSSLCiphers(node *model.Node) {
	if len(node.Arguments) == 0 {
		return
	}
	ciphers := node.Arguments[0]
	weakCiphers := []string{"RC4", "DES", "3DES", "MD5", "NULL", "EXPORT", "aNULL", "eNULL"}
	for _, weak := range weakCiphers {
		if strings.Contains(strings.ToUpper(ciphers), weak) {
			sc.addError(node.Pos, "SEC_WEAK_CIPHER",
				"SSL加密套件包含不安全算法: "+weak,
				"移除弱加密套件，使用 ssl_ciphers HIGH:!aNULL:!MD5:!RC4:!DES")
		}
	}
}

func (sc *SecurityChecker) finalizeServerSSL() {
	if sc.currentSSL == nil {
		return
	}
	ssl := sc.currentSSL

	if ssl.hasCert && !ssl.hasCertKey {
		sc.addError(ssl.pos, "SEC_SSL_MISSING_KEY",
			"配置了ssl_certificate但缺少ssl_certificate_key",
			"添加 ssl_certificate_key 指令指定私钥文件路径")
	}
	if ssl.hasCertKey && !ssl.hasCert {
		sc.addError(ssl.pos, "SEC_SSL_MISSING_CERT",
			"配置了ssl_certificate_key但缺少ssl_certificate",
			"添加 ssl_certificate 指令指定证书文件路径")
	}

	if ssl.hasCert && ssl.hasCertKey {
		if len(ssl.protocols) == 0 {
			sc.addWarning(ssl.pos, "SEC_NO_SSL_PROTOCOLS",
				"SSL已启用但未指定ssl_protocols",
				"添加 ssl_protocols TLSv1.2 TLSv1.3;")
		}
		if ssl.ciphers == "" {
			sc.addWarning(ssl.pos, "SEC_NO_SSL_CIPHERS",
				"SSL已启用但未指定ssl_ciphers",
				"添加 ssl_ciphers HIGH:!aNULL:!MD5;")
		}
		if !ssl.preferServer {
			sc.addWarning(ssl.pos, "SEC_NO_PREFER_SERVER_CIPHERS",
				"建议启用ssl_prefer_server_ciphers",
				"添加 ssl_prefer_server_ciphers on;")
		}
	}
}

func (sc *SecurityChecker) checkLocationSecurity(node *model.Node) {
	if len(node.Arguments) == 0 {
		return
	}
	path := node.Arguments[0]

	sensitivePaths := map[string]string{
		"/.git":     "Git仓库目录暴露风险",
		"/.svn":     "SVN仓库目录暴露风险",
		"/.env":     "环境变量文件暴露风险",
		"/.htaccess": "Apache配置文件暴露风险",
		"/.htpasswd": "密码文件暴露风险",
		"/wp-admin":  "WordPress管理后台暴露",
		"/phpmyadmin": "phpMyAdmin暴露风险",
		"/admin":     "管理后台路径暴露",
		"/config":    "配置目录暴露风险",
	}

	for sensitivePath, risk := range sensitivePaths {
		if strings.HasPrefix(path, sensitivePath) || path == sensitivePath {
			hasAuth := false
			for _, child := range node.Children {
				if child.Directive == "auth_basic" && len(child.Arguments) > 0 && child.Arguments[0] != "off" {
					hasAuth = true
				}
				if child.Directive == "deny" && len(child.Arguments) > 0 && child.Arguments[0] == "all" {
					hasAuth = true
				}
			}
			if !hasAuth {
				sc.addWarning(node.Pos, "SEC_SENSITIVE_PATH",
					risk+": "+path,
					"对该路径添加访问控制: auth_basic 或 deny all")
			}
		}
	}

	for _, arg := range node.Arguments {
		if strings.Contains(arg, "..") {
			sc.addError(node.Pos, "SEC_PATH_TRAVERSAL",
				"location路径包含目录遍历字符: "+arg,
				"移除路径中的'..'，使用绝对路径")
		}
	}
}

func (sc *SecurityChecker) checkRootSecurity(node *model.Node) {
	if len(node.Arguments) == 0 {
		return
	}
	root := node.Arguments[0]
	dangerousRoots := []string{"/", "/etc", "/var", "/tmp", "/root", "/home"}
	for _, dangerous := range dangerousRoots {
		if root == dangerous || root == dangerous+"/" {
			sc.addError(node.Pos, "SEC_DANGEROUS_ROOT",
				"root指向系统敏感目录: "+root,
				"将root指向Web专用目录，如 /var/www/html 或 /usr/share/nginx/html")
		}
	}
}

func (sc *SecurityChecker) checkAutoindexSecurity(node *model.Node) {
	if len(node.Arguments) > 0 && node.Arguments[0] == "on" {
		sc.addWarning(node.Pos, "SEC_AUTOINDEX_ON",
			"autoindex已启用，可能暴露目录结构",
			"除非必要，关闭autoindex: autoindex off;")
	}
}

func (sc *SecurityChecker) checkAccessLogSecurity(node *model.Node) {
	for _, arg := range node.Arguments {
		if arg == "off" {
			sc.addWarning(node.Pos, "SEC_ACCESS_LOG_OFF",
				"access_log已关闭，可能导致安全事件无法追踪",
				"启用访问日志: access_log /var/log/nginx/access.log;")
		}
	}
}

func (sc *SecurityChecker) checkAuthBasicSecurity(node *model.Node) {
	if len(node.Arguments) > 0 && node.Arguments[0] == "off" {
		return
	}
}

func (sc *SecurityChecker) checkAccessControl(node *model.Node) {
	if len(node.Arguments) == 0 {
		return
	}
	arg := node.Arguments[0]
	if arg == "all" && node.Directive == "allow" {
		sc.addWarning(node.Pos, "SEC_ALLOW_ALL",
			"allow all 允许所有访问，可能过于宽松",
			"限制为特定IP段: allow 192.168.0.0/24;")
	}
}

func (sc *SecurityChecker) checkProxyPassSecurity(node *model.Node) {
	if len(node.Arguments) == 0 {
		return
	}
	target := node.Arguments[0]
	if strings.HasPrefix(target, "http://") && !strings.Contains(target, "127.0.0.1") && !strings.Contains(target, "localhost") {
		sc.addWarning(node.Pos, "SEC_PROXY_HTTP",
			"proxy_pass使用明文HTTP连接后端: "+target,
			"考虑使用https://连接后端，或确保在内网环境中")
	}
}

func (sc *SecurityChecker) checkResolverSecurity(node *model.Node) {
	if len(node.Arguments) == 0 {
		return
	}
	for _, arg := range node.Arguments {
		if arg == "8.8.8.8" || arg == "8.8.4.4" {
			sc.addWarning(node.Pos, "SEC_PUBLIC_DNS",
				"使用公共DNS可能存在DNS劫持风险: "+arg,
				"考虑使用内网DNS服务器")
		}
	}
}

func (sc *SecurityChecker) checkGlobalSecurity() {
	if sc.hasServer && !sc.hasHTTPS {
		sc.addWarning(model.Position{}, "SEC_NO_HTTPS",
			"检测到server配置但未启用HTTPS",
			"配置SSL证书并启用443端口监听")
	}
}

func (sc *SecurityChecker) addError(pos model.Position, ruleID, msg, suggestion string) {
	sc.errors = append(sc.errors, &model.LintError{
		Pos:        pos,
		Severity:   model.SeverityError,
		RuleID:     ruleID,
		Message:    msg,
		Suggestion: suggestion,
	})
}

func (sc *SecurityChecker) addWarning(pos model.Position, ruleID, msg, suggestion string) {
	sc.errors = append(sc.errors, &model.LintError{
		Pos:        pos,
		Severity:   model.SeverityWarning,
		RuleID:     ruleID,
		Message:    msg,
		Suggestion: suggestion,
	})
}

func CheckSecurity(nodes []*model.Node) []*model.LintError {
	checker := NewSecurityChecker()
	checker.Check(nodes)
	return checker.Errors()
}
