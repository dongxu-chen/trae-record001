package session

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"cross-cloud-lb/pkg/model"
	"fmt"
	"hash/fnv"
	"net/http"
	"sync"
	"time"

	"github.com/google/uuid"
	"go.uber.org/zap"
)

type SessionManager interface {
	GetClusterIDForSession(gatewayID string) (string, bool)
	SetClusterForSession(gatewayID, clusterID string)
	InjectGatewayIDHeader(req *http.Request, clusterID string) string
	ExtractGatewayID(req *http.Request) string
	GetOrCreateSession(req *http.Request) (gatewayID string, isNew bool)
	ValidateGatewayID(gatewayID string) bool
	ClearExpiredSessions()
}

type SessionManagerImpl struct {
	config    model.SessionAffinityConfig
	sessions  map[string]*sessionState
	mu        sync.RWMutex
	logger    *zap.Logger
	secret    []byte
	gatewayID string
}

type sessionState struct {
	gatewayID    string
	clusterID    string
	lastAccessed time.Time
	createdAt    time.Time
}

const (
	HeaderGatewayID    = "X-Gateway-ID"
	HeaderGatewayRoute = "X-Gateway-Route"
)

func NewSessionManager(config model.SessionAffinityConfig, logger *zap.Logger, secret []byte) *SessionManagerImpl {
	gatewayID := generateGatewayInstanceID()
	logger.Info("Session manager initialized",
		zap.String("gateway_instance_id", gatewayID),
		zap.Bool("enabled", config.Enabled))

	sm := &SessionManagerImpl{
		config:    config,
		sessions:  make(map[string]*sessionState),
		logger:    logger,
		secret:    secret,
		gatewayID: gatewayID,
	}

	if config.Enabled {
		go sm.startCleanupLoop()
	}

	return sm
}

func (sm *SessionManagerImpl) GetClusterIDForSession(gatewayID string) (string, bool) {
	if !sm.config.Enabled || gatewayID == "" {
		return "", false
	}

	sm.mu.RLock()
	defer sm.mu.RUnlock()

	state, exists := sm.sessions[gatewayID]
	if !exists {
		return "", false
	}

	if time.Since(state.lastAccessed) > sm.config.TTL {
		return "", false
	}

	state.lastAccessed = time.Now()
	return state.clusterID, true
}

func (sm *SessionManagerImpl) SetClusterForSession(gatewayID, clusterID string) {
	if !sm.config.Enabled || gatewayID == "" {
		return
	}

	sm.mu.Lock()
	defer sm.mu.Unlock()

	now := time.Now()
	sm.sessions[gatewayID] = &sessionState{
		gatewayID:    gatewayID,
		clusterID:    clusterID,
		lastAccessed: now,
		createdAt:    now,
	}

	sm.logger.Debug("Session mapping created/updated",
		zap.String("gateway_id", gatewayID),
		zap.String("target_cluster", clusterID))
}

func (sm *SessionManagerImpl) InjectGatewayIDHeader(req *http.Request, clusterID string) string {
	if !sm.config.Enabled {
		return ""
	}

	gatewayID := sm.ExtractGatewayID(req)
	if gatewayID == "" {
		gatewayID = sm.generateGatewayID()
	}

	req.Header.Set(HeaderGatewayID, gatewayID)
	req.Header.Set(HeaderGatewayRoute, clusterID)

	sm.SetClusterForSession(gatewayID, clusterID)

	sm.logger.Debug("Injected gateway ID headers",
		zap.String("gateway_id", gatewayID),
		zap.String("target_cluster", clusterID))

	return gatewayID
}

func (sm *SessionManagerImpl) ExtractGatewayID(req *http.Request) string {
	if !sm.config.Enabled {
		return ""
	}

	gatewayID := req.Header.Get(HeaderGatewayID)
	if gatewayID != "" && sm.ValidateGatewayID(gatewayID) {
		return gatewayID
	}

	return ""
}

func (sm *SessionManagerImpl) GetOrCreateSession(req *http.Request) (gatewayID string, isNew bool) {
	if !sm.config.Enabled {
		return "", false
	}

	gatewayID = sm.ExtractGatewayID(req)
	if gatewayID != "" {
		return gatewayID, false
	}

	gatewayID = sm.generateGatewayID()
	req.Header.Set(HeaderGatewayID, gatewayID)

	return gatewayID, true
}

func (sm *SessionManagerImpl) ValidateGatewayID(gatewayID string) bool {
	if gatewayID == "" {
		return false
	}

	for i := len(gatewayID) - 1; i >= 0; i-- {
		if gatewayID[i] == '.' {
			idPart := gatewayID[:i]
			signature := gatewayID[i+1:]

			expectedMAC := hmac.New(sha256.New, sm.secret)
			expectedMAC.Write([]byte(idPart))
			expectedSignature := base64.URLEncoding.EncodeToString(expectedMAC.Sum(nil))

			return hmac.Equal([]byte(signature), []byte(expectedSignature))
		}
	}

	return false
}

func (sm *SessionManagerImpl) ClearExpiredSessions() {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	now := time.Now()
	expiredCount := 0

	for gatewayID, state := range sm.sessions {
		if now.Sub(state.lastAccessed) > sm.config.TTL {
			delete(sm.sessions, gatewayID)
			expiredCount++
		}
	}

	if expiredCount > 0 {
		sm.logger.Debug("Cleared expired sessions", zap.Int("count", expiredCount))
	}
}

func (sm *SessionManagerImpl) startCleanupLoop() {
	cleanupInterval := sm.config.TTL / 2
	if cleanupInterval < time.Minute {
		cleanupInterval = time.Minute
	}

	ticker := time.NewTicker(cleanupInterval)
	defer ticker.Stop()

	for range ticker.C {
		sm.ClearExpiredSessions()
	}
}

func (sm *SessionManagerImpl) generateGatewayID() string {
	h := fnv.New64a()
	h.Write([]byte(sm.gatewayID))
	h.Write([]byte(time.Now().String()))
	h.Write([]byte(uuid.New().String()))
	hash := h.Sum64()

	idPart := fmt.Sprintf("%s-%d", sm.gatewayID, hash)

	mac := hmac.New(sha256.New, sm.secret)
	mac.Write([]byte(idPart))
	signature := base64.URLEncoding.EncodeToString(mac.Sum(nil))

	return fmt.Sprintf("%s.%s", idPart, signature)
}

func generateGatewayInstanceID() string {
	return uuid.New().String()[:8]
}

func (sm *SessionManagerImpl) GetGatewayInstanceID() string {
	return sm.gatewayID
}

func (sm *SessionManagerImpl) GetSessionCount() int {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	return len(sm.sessions)
}

func (sm *SessionManagerImpl) RouteByHeader(req *http.Request, healthyClusters []string) (string, bool) {
	if !sm.config.Enabled {
		return "", false
	}

	gatewayID := sm.ExtractGatewayID(req)
	if gatewayID == "" {
		return "", false
	}

	clusterID, exists := sm.GetClusterIDForSession(gatewayID)
	if !exists {
		return "", false
	}

	for _, healthy := range healthyClusters {
		if healthy == clusterID {
			return clusterID, true
		}
	}

	sm.logger.Warn("Session target cluster is unhealthy, route will be rebalanced",
		zap.String("gateway_id", gatewayID),
		zap.String("original_cluster", clusterID))

	return "", false
}
