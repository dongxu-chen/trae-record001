package auth

import (
	"cloud-tag-compliance/internal/config"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/google/uuid"
)

type Role struct {
	ID          string   `yaml:"id" json:"id"`
	Name        string   `yaml:"name" json:"name"`
	Permissions []string `yaml:"permissions" json:"permissions"`
	AccountIDs  []string `yaml:"accountIds" json:"accountIds"`
}

type TrustLink struct {
	FromRoleID string    `yaml:"fromRoleId" json:"fromRoleId"`
	ToRoleID   string    `yaml:"toRoleId" json:"toRoleId"`
	ValidFrom  time.Time `yaml:"validFrom" json:"validFrom"`
	ValidUntil time.Time `yaml:"validUntil" json:"validUntil"`
	Conditions string    `yaml:"conditions" json:"conditions"`
}

type TrustChain struct {
	ID        string      `yaml:"id" json:"id"`
	Name      string      `yaml:"name" json:"name"`
	Links     []TrustLink `yaml:"links" json:"links"`
	CreatedAt time.Time   `yaml:"createdAt" json:"createdAt"`
}

type Session struct {
	ID           string    `json:"id"`
	UserID       string    `json:"userId"`
	UserName     string    `json:"userName"`
	CurrentRole  string    `json:"currentRole"`
	AccountID    string    `json:"accountId"`
	AccountName  string    `json:"accountName"`
	TrustedRoles []string  `json:"trustedRoles"`
	CreatedAt    time.Time `json:"createdAt"`
	ExpiresAt    time.Time `json:"expiresAt"`
	Token        string    `json:"token"`
}

type TrustManager struct {
	roles       map[string]Role
	trustChains map[string]TrustChain
	sessions    map[string]*Session
	accounts    map[string]config.AccountConfig
	mu          sync.RWMutex
}

func NewTrustManager(cfg *config.Config) *TrustManager {
	tm := &TrustManager{
		roles:       make(map[string]Role),
		trustChains: make(map[string]TrustChain),
		sessions:    make(map[string]*Session),
		accounts:    make(map[string]config.AccountConfig),
	}

	for _, acc := range cfg.Accounts {
		tm.accounts[acc.ID] = acc
	}

	tm.initDefaultRoles()
	tm.initDefaultTrustChains()

	return tm
}

func (tm *TrustManager) initDefaultRoles() {
	tm.roles["role-admin"] = Role{
		ID:          "role-admin",
		Name:        "系统管理员",
		Permissions: []string{"*"},
		AccountIDs:  []string{"account-prod-001", "account-dev-001"},
	}

	tm.roles["role-prod-viewer"] = Role{
		ID:          "role-prod-viewer",
		Name:        "生产环境查看者",
		Permissions: []string{"resources:read", "compliance:read"},
		AccountIDs:  []string{"account-prod-001"},
	}

	tm.roles["role-prod-operator"] = Role{
		ID:          "role-prod-operator",
		Name:        "生产环境运维",
		Permissions: []string{"resources:read", "resources:write", "compliance:read", "compliance:write"},
		AccountIDs:  []string{"account-prod-001"},
	}

	tm.roles["role-dev-admin"] = Role{
		ID:          "role-dev-admin",
		Name:        "开发环境管理员",
		Permissions: []string{"*"},
		AccountIDs:  []string{"account-dev-001"},
	}

	tm.roles["role-auditor"] = Role{
		ID:          "role-auditor",
		Name:        "合规审计员",
		Permissions: []string{"resources:read", "compliance:read", "rules:read"},
		AccountIDs:  []string{"account-prod-001", "account-dev-001"},
	}
}

func (tm *TrustManager) initDefaultTrustChains() {
	now := time.Now()
	oneYearLater := now.AddDate(1, 0, 0)

	tm.trustChains["chain-dev-to-prod"] = TrustChain{
		ID:   "chain-dev-to-prod",
		Name: "开发环境到生产环境信任链",
		Links: []TrustLink{
			{
				FromRoleID: "role-dev-admin",
				ToRoleID:   "role-prod-viewer",
				ValidFrom:  now,
				ValidUntil: oneYearLater,
				Conditions: "mfa_required",
			},
		},
		CreatedAt: now,
	}

	tm.trustChains["chain-audit"] = TrustChain{
		ID:   "chain-audit",
		Name: "审计员跨账号信任链",
		Links: []TrustLink{
			{
				FromRoleID: "role-auditor",
				ToRoleID:   "role-prod-viewer",
				ValidFrom:  now,
				ValidUntil: oneYearLater,
				Conditions: "audit_purpose",
			},
			{
				FromRoleID: "role-auditor",
				ToRoleID:   "role-dev-admin",
				ValidFrom:  now,
				ValidUntil: oneYearLater,
				Conditions: "audit_purpose",
			},
		},
		CreatedAt: now,
	}

	tm.trustChains["chain-admin"] = TrustChain{
		ID:   "chain-admin",
		Name: "管理员全权限信任链",
		Links: []TrustLink{
			{
				FromRoleID: "role-admin",
				ToRoleID:   "role-prod-operator",
				ValidFrom:  now,
				ValidUntil: oneYearLater,
				Conditions: "",
			},
			{
				FromRoleID: "role-admin",
				ToRoleID:   "role-dev-admin",
				ValidFrom:  now,
				ValidUntil: oneYearLater,
				Conditions: "",
			},
		},
		CreatedAt: now,
	}
}

func (tm *TrustManager) CreateSession(userID, userName, initialRole string) (*Session, error) {
	tm.mu.Lock()
	defer tm.mu.Unlock()

	role, exists := tm.roles[initialRole]
	if !exists {
		return nil, errors.New("invalid role")
	}

	trustedRoles := tm.getTrustedRoles(initialRole)

	var defaultAccountID string
	var defaultAccountName string
	if len(role.AccountIDs) > 0 {
		defaultAccountID = role.AccountIDs[0]
		if acc, ok := tm.accounts[defaultAccountID]; ok {
			defaultAccountName = acc.Name
		}
	}

	sessionID := uuid.New().String()
	token := generateToken(sessionID, userID, time.Now().String())

	session := &Session{
		ID:           sessionID,
		UserID:       userID,
		UserName:     userName,
		CurrentRole:  initialRole,
		AccountID:    defaultAccountID,
		AccountName:  defaultAccountName,
		TrustedRoles: trustedRoles,
		CreatedAt:    time.Now(),
		ExpiresAt:    time.Now().Add(8 * time.Hour),
		Token:        token,
	}

	tm.sessions[sessionID] = session

	return session, nil
}

func (tm *TrustManager) SwitchRole(sessionID, targetRoleID string) (*Session, error) {
	tm.mu.Lock()
	defer tm.mu.Unlock()

	session, exists := tm.sessions[sessionID]
	if !exists {
		return nil, errors.New("session not found")
	}

	if time.Now().After(session.ExpiresAt) {
		return nil, errors.New("session expired")
	}

	isTrusted := false
	for _, r := range session.TrustedRoles {
		if r == targetRoleID {
			isTrusted = true
			break
		}
	}
	if session.CurrentRole == targetRoleID {
		isTrusted = true
	}

	if !isTrusted {
		return nil, errors.New("role not trusted")
	}

	targetRole, exists := tm.roles[targetRoleID]
	if !exists {
		return nil, errors.New("target role not found")
	}

	var newAccountID string
	var newAccountName string
	if len(targetRole.AccountIDs) > 0 {
		newAccountID = targetRole.AccountIDs[0]
		if acc, ok := tm.accounts[newAccountID]; ok {
			newAccountName = acc.Name
		}
	}

	session.CurrentRole = targetRoleID
	session.AccountID = newAccountID
	session.AccountName = newAccountName
	session.TrustedRoles = tm.getTrustedRoles(targetRoleID)
	session.ExpiresAt = time.Now().Add(8 * time.Hour)

	return session, nil
}

func (tm *TrustManager) SwitchAccount(sessionID, accountID string) (*Session, error) {
	tm.mu.Lock()
	defer tm.mu.Unlock()

	session, exists := tm.sessions[sessionID]
	if !exists {
		return nil, errors.New("session not found")
	}

	if time.Now().After(session.ExpiresAt) {
		return nil, errors.New("session expired")
	}

	currentRole, exists := tm.roles[session.CurrentRole]
	if !exists {
		return nil, errors.New("current role not found")
	}

	accountAllowed := false
	for _, accID := range currentRole.AccountIDs {
		if accID == accountID {
			accountAllowed = true
			break
		}
	}

	if !accountAllowed {
		return nil, errors.New("account not allowed for current role")
	}

	account, exists := tm.accounts[accountID]
	if !exists {
		return nil, errors.New("account not found")
	}

	session.AccountID = accountID
	session.AccountName = account.Name
	session.ExpiresAt = time.Now().Add(8 * time.Hour)

	return session, nil
}

func (tm *TrustManager) getTrustedRoles(roleID string) []string {
	trusted := make(map[string]bool)
	visited := make(map[string]bool)

	var dfs func(currentRole string)
	dfs = func(currentRole string) {
		if visited[currentRole] {
			return
		}
		visited[currentRole] = true

		for _, chain := range tm.trustChains {
			for _, link := range chain.Links {
				if link.FromRoleID == currentRole {
					if time.Now().After(link.ValidFrom) && time.Now().Before(link.ValidUntil) {
						if !trusted[link.ToRoleID] {
							trusted[link.ToRoleID] = true
							dfs(link.ToRoleID)
						}
					}
				}
			}
		}
	}

	dfs(roleID)

	result := make([]string, 0, len(trusted))
	for r := range trusted {
		result = append(result, r)
	}
	return result
}

func (tm *TrustManager) GetSession(sessionID string) (*Session, error) {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	session, exists := tm.sessions[sessionID]
	if !exists {
		return nil, errors.New("session not found")
	}

	if time.Now().After(session.ExpiresAt) {
		return nil, errors.New("session expired")
	}

	return session, nil
}

func (tm *TrustManager) GetRoles() []Role {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	roles := make([]Role, 0, len(tm.roles))
	for _, r := range tm.roles {
		roles = append(roles, r)
	}
	return roles
}

func (tm *TrustManager) GetTrustChains() []TrustChain {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	chains := make([]TrustChain, 0, len(tm.trustChains))
	for _, c := range tm.trustChains {
		chains = append(chains, c)
	}
	return chains
}

func (tm *TrustManager) GetAvailableAccounts(sessionID string) ([]config.AccountConfig, error) {
	session, err := tm.GetSession(sessionID)
	if err != nil {
		return nil, err
	}

	role, exists := tm.roles[session.CurrentRole]
	if !exists {
		return nil, errors.New("role not found")
	}

	accounts := make([]config.AccountConfig, 0, len(role.AccountIDs))
	for _, accID := range role.AccountIDs {
		if acc, ok := tm.accounts[accID]; ok {
			accounts = append(accounts, acc)
		}
	}
	return accounts, nil
}

func (tm *TrustManager) GetAvailableRoles(sessionID string) ([]Role, error) {
	session, err := tm.GetSession(sessionID)
	if err != nil {
		return nil, err
	}

	allRoles := make([]Role, 0)
	if role, ok := tm.roles[session.CurrentRole]; ok {
		allRoles = append(allRoles, role)
	}

	for _, roleID := range session.TrustedRoles {
		if role, ok := tm.roles[roleID]; ok {
			allRoles = append(allRoles, role)
		}
	}

	return allRoles, nil
}

func generateToken(parts ...string) string {
	h := sha256.New()
	for _, p := range parts {
		h.Write([]byte(p))
	}
	return hex.EncodeToString(h.Sum(nil))[:32]
}

func (tm *TrustManager) ValidateToken(token string) (*Session, error) {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	for _, session := range tm.sessions {
		if session.Token == token {
			if time.Now().After(session.ExpiresAt) {
				return nil, errors.New("session expired")
			}
			return session, nil
		}
	}
	return nil, errors.New("invalid token")
}

func (tm *TrustManager) GetAccountRoleMatrix() map[string][]string {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	matrix := make(map[string][]string)
	for roleID, role := range tm.roles {
		for _, accID := range role.AccountIDs {
			matrix[accID] = append(matrix[accID], roleID)
		}
	}
	return matrix
}

func (tm *TrustManager) SeamlessSwitch(sessionID, targetAccountID string) (*Session, error) {
	tm.mu.Lock()
	defer tm.mu.Unlock()

	session, exists := tm.sessions[sessionID]
	if !exists {
		return nil, errors.New("session not found")
	}

	if time.Now().After(session.ExpiresAt) {
		return nil, errors.New("session expired")
	}

	if session.AccountID == targetAccountID {
		return session, nil
	}

	currentRole, exists := tm.roles[session.CurrentRole]
	if exists {
		for _, accID := range currentRole.AccountIDs {
			if accID == targetAccountID {
				account := tm.accounts[targetAccountID]
				session.AccountID = targetAccountID
				session.AccountName = account.Name
				session.ExpiresAt = time.Now().Add(8 * time.Hour)
				return session, nil
			}
		}
	}

	for _, trustedRoleID := range session.TrustedRoles {
		role, exists := tm.roles[trustedRoleID]
		if !exists {
			continue
		}
		for _, accID := range role.AccountIDs {
			if accID == targetAccountID {
				account := tm.accounts[targetAccountID]
				session.CurrentRole = trustedRoleID
				session.AccountID = targetAccountID
				session.AccountName = account.Name
				session.TrustedRoles = tm.getTrustedRoles(trustedRoleID)
				session.ExpiresAt = time.Now().Add(8 * time.Hour)
				return session, nil
			}
		}
	}

	return nil, fmt.Errorf("no trust path found to account %s", targetAccountID)
}
