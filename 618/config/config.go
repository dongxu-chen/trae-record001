package config

import (
	"os"
	"strconv"
)

type Config struct {
	ServerPort   string
	NacosHost    string
	NacosPort    uint64
	NacosUser    string
	NacosPassword string
	DBPath       string
	SMTPHost     string
	SMTPPort     int
	SMTPUser     string
	SMTPPassword string
	SMTPFrom     string
	NotifyEmails []string
	LDAPEnabled  bool
	LDAPHost     string
	LDAPPort     int
	LDAPUseSSL   bool
	LDAPBindDN   string
	LDAPBindPass string
	LDAPBaseDN   string
	LDAPUserFilter string
	LDAPEmailAttr string
	LDAPNameAttr  string
	LDAPDeptAttr  string
}

func Load() *Config {
	return &Config{
		ServerPort:     getEnv("SERVER_PORT", "8080"),
		NacosHost:      getEnv("NACOS_HOST", "localhost"),
		NacosPort:      parseUint64(getEnv("NACOS_PORT", "8848")),
		NacosUser:      getEnv("NACOS_USER", "nacos"),
		NacosPassword:  getEnv("NACOS_PASSWORD", "nacos"),
		DBPath:         getEnv("DB_PATH", "nacos_audit.db"),
		SMTPHost:       getEnv("SMTP_HOST", "smtp.example.com"),
		SMTPPort:       parseInt(getEnv("SMTP_PORT", "587")),
		SMTPUser:       getEnv("SMTP_USER", "user@example.com"),
		SMTPPassword:   getEnv("SMTP_PASSWORD", "password"),
		SMTPFrom:       getEnv("SMTP_FROM", "audit@example.com"),
		NotifyEmails:   parseEmails(getEnv("NOTIFY_EMAILS", "admin@example.com")),
		LDAPEnabled:    getEnvBool("LDAP_ENABLED", false),
		LDAPHost:       getEnv("LDAP_HOST", "ldap.example.com"),
		LDAPPort:       parseInt(getEnv("LDAP_PORT", "389")),
		LDAPUseSSL:     getEnvBool("LDAP_USE_SSL", false),
		LDAPBindDN:     getEnv("LDAP_BIND_DN", "cn=admin,dc=example,dc=com"),
		LDAPBindPass:   getEnv("LDAP_BIND_PASS", "admin"),
		LDAPBaseDN:     getEnv("LDAP_BASE_DN", "dc=example,dc=com"),
		LDAPUserFilter: getEnv("LDAP_USER_FILTER", "(cn=%s)"),
		LDAPEmailAttr:  getEnv("LDAP_EMAIL_ATTR", "mail"),
		LDAPNameAttr:   getEnv("LDAP_NAME_ATTR", "displayName"),
		LDAPDeptAttr:   getEnv("LDAP_DEPT_ATTR", "department"),
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvBool(key string, defaultValue bool) bool {
	if value := os.Getenv(key); value != "" {
		return value == "true" || value == "1" || value == "yes"
	}
	return defaultValue
}

func parseUint64(s string) uint64 {
	if val, err := strconv.ParseUint(s, 10, 64); err == nil {
		return val
	}
	return 0
}

func parseInt(s string) int {
	if val, err := strconv.Atoi(s); err == nil {
		return val
	}
	return 0
}

func parseEmails(s string) []string {
	if s == "" {
		return []string{}
	}
	var result []string
	var current string
	for _, c := range s {
		if c == ',' {
			if current != "" {
				result = append(result, current)
				current = ""
			}
		} else {
			current += string(c)
		}
	}
	if current != "" {
		result = append(result, current)
	}
	return result
}
