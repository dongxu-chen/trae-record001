package ldap

import (
	"crypto/tls"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/go-ldap/ldap/v3"
)

type LDAPConfig struct {
	Host         string
	Port         int
	UseSSL       bool
	BindDN       string
	BindPassword string
	BaseDN       string
	UserFilter   string
	EmailAttr    string
	NameAttr     string
	DeptAttr     string
}

type UserInfo struct {
	Username string
	Email    string
	Name     string
	Dept     string
	DN       string
}

type LDAPClient struct {
	config     LDAPConfig
	conn       *ldap.Conn
	connMutex  sync.RWMutex
	lastActive time.Time
}

func NewLDAPClient(config LDAPConfig) *LDAPClient {
	return &LDAPClient{
		config: config,
	}
}

func (c *LDAPClient) connect() error {
	c.connMutex.Lock()
	defer c.connMutex.Unlock()

	if c.conn != nil && time.Since(c.lastActive) < 30*time.Minute {
		return nil
	}

	if c.conn != nil {
		c.conn.Close()
		c.conn = nil
	}

	var err error
	if c.config.UseSSL {
		c.conn, err = ldap.DialTLS("tcp", fmt.Sprintf("%s:%d", c.config.Host, c.config.Port),
			&tls.Config{InsecureSkipVerify: true})
	} else {
		c.conn, err = ldap.Dial("tcp", fmt.Sprintf("%s:%d", c.config.Host, c.config.Port))
	}

	if err != nil {
		return fmt.Errorf("failed to connect to LDAP: %v", err)
	}

	err = c.conn.Bind(c.config.BindDN, c.config.BindPassword)
	if err != nil {
		c.conn.Close()
		c.conn = nil
		return fmt.Errorf("failed to bind to LDAP: %v", err)
	}

	c.lastActive = time.Now()
	log.Println("LDAP connection established")
	return nil
}

func (c *LDAPClient) ensureConnection() error {
	c.connMutex.RLock()
	connected := c.conn != nil && time.Since(c.lastActive) < 30*time.Minute
	c.connMutex.RUnlock()

	if !connected {
		return c.connect()
	}
	return nil
}

func (c *LDAPClient) SearchUser(username string) (*UserInfo, error) {
	if err := c.ensureConnection(); err != nil {
		return nil, err
	}

	c.connMutex.RLock()
	defer c.connMutex.RUnlock()

	filter := fmt.Sprintf(c.config.UserFilter, username)
	attributes := []string{c.config.EmailAttr, c.config.NameAttr, c.config.DeptAttr}

	searchRequest := ldap.NewSearchRequest(
		c.config.BaseDN,
		ldap.ScopeWholeSubtree,
		ldap.NeverDerefAliases,
		0,
		0,
		false,
		filter,
		attributes,
		nil,
	)

	result, err := c.conn.Search(searchRequest)
	if err != nil {
		return nil, fmt.Errorf("LDAP search failed: %v", err)
	}

	if len(result.Entries) == 0 {
		return nil, fmt.Errorf("user not found: %s", username)
	}

	entry := result.Entries[0]
	user := &UserInfo{
		Username: username,
		DN:       entry.DN,
		Email:    entry.GetAttributeValue(c.config.EmailAttr),
		Name:     entry.GetAttributeValue(c.config.NameAttr),
		Dept:     entry.GetAttributeValue(c.config.DeptAttr),
	}

	c.lastActive = time.Now()
	return user, nil
}

func (c *LDAPClient) GetUserEmail(username string) (string, error) {
	user, err := c.SearchUser(username)
	if err != nil {
		return "", err
	}
	return user.Email, nil
}

func (c *LDAPClient) GetUserName(username string) (string, error) {
	user, err := c.SearchUser(username)
	if err != nil {
		return "", err
	}
	return user.Name, nil
}

func (c *LDAPClient) SearchUsersByDept(dept string) ([]*UserInfo, error) {
	if err := c.ensureConnection(); err != nil {
		return nil, err
	}

	c.connMutex.RLock()
	defer c.connMutex.RUnlock()

	filter := fmt.Sprintf("(%s=%s)", c.config.DeptAttr, dept)
	attributes := []string{"cn", c.config.EmailAttr, c.config.NameAttr, c.config.DeptAttr}

	searchRequest := ldap.NewSearchRequest(
		c.config.BaseDN,
		ldap.ScopeWholeSubtree,
		ldap.NeverDerefAliases,
		0,
		0,
		false,
		filter,
		attributes,
		nil,
	)

	result, err := c.conn.Search(searchRequest)
	if err != nil {
		return nil, fmt.Errorf("LDAP search failed: %v", err)
	}

	users := make([]*UserInfo, 0, len(result.Entries))
	for _, entry := range result.Entries {
		users = append(users, &UserInfo{
			Username: entry.GetAttributeValue("cn"),
			DN:       entry.DN,
			Email:    entry.GetAttributeValue(c.config.EmailAttr),
			Name:     entry.GetAttributeValue(c.config.NameAttr),
			Dept:     entry.GetAttributeValue(c.config.DeptAttr),
		})
	}

	c.lastActive = time.Now()
	return users, nil
}

func (c *LDAPClient) GetResponsibleEmails(operator string) []string {
	emails := make([]string, 0)

	user, err := c.SearchUser(operator)
	if err != nil {
		log.Printf("Failed to find user %s in LDAP: %v", operator, err)
		return emails
	}

	if user.Email != "" {
		emails = append(emails, user.Email)
	}

	if user.Dept != "" {
		deptUsers, err := c.SearchUsersByDept(user.Dept)
		if err == nil {
			for _, u := range deptUsers {
				if u.Email != "" && u.Username != operator {
					emails = append(emails, u.Email)
				}
			}
		}
	}

	return emails
}

func (c *LDAPClient) Close() {
	c.connMutex.Lock()
	defer c.connMutex.Unlock()
	if c.conn != nil {
		c.conn.Close()
		c.conn = nil
	}
}
