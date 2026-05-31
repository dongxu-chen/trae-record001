package policy

import (
	"encoding/json"
	"os"
	"sync"
	"time"

	"github.com/google/uuid"
	"go.uber.org/zap"
)

type ActionType string

const (
	ActionMoveToDisk  ActionType = "move_to_disk"
	ActionDrop        ActionType = "drop"
	ActionFreeze      ActionType = "freeze"
	ActionOptimize    ActionType = "optimize"
	ActionArchive     ActionType = "archive"
)

type TTLPolicy struct {
	ID              string     `json:"id"`
	Name            string     `json:"name"`
	Database        string     `json:"database"`
	Table           string     `json:"table"`
	Description     string     `json:"description"`
	Enabled         bool       `json:"enabled"`
	Rules           []TTLRule  `json:"rules"`
	CreatedAt       time.Time  `json:"created_at"`
	UpdatedAt       time.Time  `json:"updated_at"`
}

type TTLRule struct {
	ID              string     `json:"id"`
	AgeDays         int        `json:"age_days"`
	Action          ActionType `json:"action"`
	TargetDisk      string     `json:"target_disk,omitempty"`
	TargetPolicy    string     `json:"target_policy,omitempty"`
	Description     string     `json:"description,omitempty"`
	Priority        int        `json:"priority"`
}

type Store struct {
	mu      sync.RWMutex
	policies map[string]*TTLPolicy
	filePath string
	logger   *zap.Logger
}

func NewStore(filePath string, logger *zap.Logger) *Store {
	s := &Store{
		policies: make(map[string]*TTLPolicy),
		filePath: filePath,
		logger:   logger,
	}
	if err := s.load(); err != nil {
		logger.Warn("failed to load policies, starting fresh", zap.Error(err))
	}
	return s
}

func (s *Store) load() error {
	data, err := os.ReadFile(s.filePath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	var policies []*TTLPolicy
	if err := json.Unmarshal(data, &policies); err != nil {
		return err
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, p := range policies {
		s.policies[p.ID] = p
	}
	s.logger.Info("loaded policies", zap.Int("count", len(policies)))
	return nil
}

func (s *Store) save() error {
	s.mu.RLock()
	policies := make([]*TTLPolicy, 0, len(s.policies))
	for _, p := range s.policies {
		policies = append(policies, p)
	}
	s.mu.RUnlock()
	data, err := json.MarshalIndent(policies, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(s.filePath, data, 0644)
}

func (s *Store) Create(policy *TTLPolicy) (*TTLPolicy, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	policy.ID = uuid.New().String()
	policy.CreatedAt = time.Now()
	policy.UpdatedAt = time.Now()
	for i := range policy.Rules {
		if policy.Rules[i].ID == "" {
			policy.Rules[i].ID = uuid.New().String()
		}
	}
	s.policies[policy.ID] = policy
	if err := s.save(); err != nil {
		delete(s.policies, policy.ID)
		return nil, err
	}
	s.logger.Info("created policy", zap.String("id", policy.ID), zap.String("name", policy.Name))
	return policy, nil
}

func (s *Store) Update(id string, policy *TTLPolicy) (*TTLPolicy, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	existing, ok := s.policies[id]
	if !ok {
		return nil, ErrPolicyNotFound
	}
	policy.ID = id
	policy.CreatedAt = existing.CreatedAt
	policy.UpdatedAt = time.Now()
	for i := range policy.Rules {
		if policy.Rules[i].ID == "" {
			policy.Rules[i].ID = uuid.New().String()
		}
	}
	s.policies[id] = policy
	if err := s.save(); err != nil {
		s.policies[id] = existing
		return nil, err
	}
	s.logger.Info("updated policy", zap.String("id", id))
	return policy, nil
}

func (s *Store) Delete(id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	existing, ok := s.policies[id]
	if !ok {
		return ErrPolicyNotFound
	}
	delete(s.policies, id)
	if err := s.save(); err != nil {
		s.policies[id] = existing
		return err
	}
	s.logger.Info("deleted policy", zap.String("id", id))
	return nil
}

func (s *Store) Get(id string) (*TTLPolicy, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	p, ok := s.policies[id]
	if !ok {
		return nil, ErrPolicyNotFound
	}
	return p, nil
}

func (s *Store) List() ([]*TTLPolicy, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	result := make([]*TTLPolicy, 0, len(s.policies))
	for _, p := range s.policies {
		result = append(result, p)
	}
	return result, nil
}

func (s *Store) GetByTable(database, table string) ([]*TTLPolicy, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	var result []*TTLPolicy
	for _, p := range s.policies {
		if p.Database == database && p.Table == table && p.Enabled {
			result = append(result, p)
		}
	}
	return result, nil
}

func (s *Store) GetActivePolicies() ([]*TTLPolicy, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	var result []*TTLPolicy
	for _, p := range s.policies {
		if p.Enabled {
			result = append(result, p)
		}
	}
	return result, nil
}
