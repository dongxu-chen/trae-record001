package config

import (
	"encoding/json"
	"sync"

	"github.com/traffic-mirror/control-plane/internal/model"
	"github.com/traffic-mirror/control-plane/pkg/types"
	"gorm.io/gorm"
)

type Manager struct {
	mu               sync.RWMutex
	db               *gorm.DB
	config           types.MirrorConfig
	protoSchemas     map[int64]*types.ProtoSchema
}

func NewManager(db *gorm.DB) *Manager {
	m := &Manager{
		db: db,
		config: types.MirrorConfig{
			SamplingRate:    0.1,
			SamplingHashKey: "x-request-id",
			HeaderRules:     make([]types.HeaderRule, 0),
			TestCluster:     "test_service",
			Enabled:         true,
			ProtoContentTypes: []string{
				"application/grpc",
				"application/grpc+proto",
				"application/x-protobuf",
				"application/protobuf",
			},
			ColorEnabled:     false,
			ColorHeader:      "x-traffic-color",
			ColorValue:       "mirrored",
			AnomalyEnabled:   true,
			AnomalyThreshold: 0.0,
		},
		protoSchemas: make(map[int64]*types.ProtoSchema),
	}
	m.loadFromDB()
	return m
}

func (m *Manager) loadFromDB() {
	var rules []model.HeaderRule
	if err := m.db.Find(&rules).Error; err == nil {
		for _, r := range rules {
			m.config.HeaderRules = append(m.config.HeaderRules, types.HeaderRule{
				ID:        r.ID,
				Name:      r.Name,
				Value:     r.Value,
				Operation: r.Operation,
				Match:     r.Match,
				Override:  r.Override,
				Priority:  r.Priority,
				Enabled:   r.Enabled,
			})
		}
	}

	var schemas []model.ProtoSchema
	if err := m.db.Find(&schemas).Error; err == nil {
		for _, s := range schemas {
			m.protoSchemas[s.ID] = &types.ProtoSchema{
				ID:             s.ID,
				MessageType:    s.MessageType,
				ProtoFileName:  s.ProtoFileName,
				FileDescriptor: s.FileDescriptor,
				PackageName:    s.PackageName,
				ServiceName:    s.ServiceName,
				MethodName:     s.MethodName,
				Description:    s.Description,
				Enabled:        s.Enabled,
			}
		}
	}
}

func (m *Manager) GetConfig() types.MirrorConfig {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.config
}

func (m *Manager) GetConfigJSON() string {
	m.mu.RLock()
	defer m.mu.RUnlock()
	cfg := m.config
	rules := make([]types.HeaderRule, 0)
	for _, r := range cfg.HeaderRules {
		if r.Enabled {
			rules = append(rules, r)
		}
	}
	cfg.HeaderRules = rules
	data, _ := json.Marshal(cfg)
	return string(data)
}

func (m *Manager) UpdateSamplingRate(rate float64) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if rate < 0 {
		rate = 0
	}
	if rate > 1 {
		rate = 1
	}
	m.config.SamplingRate = rate
	return nil
}

func (m *Manager) UpdateSamplingHashKey(hashKey string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.config.SamplingHashKey = hashKey
	return nil
}

func (m *Manager) UpdateTestCluster(cluster string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.config.TestCluster = cluster
	return nil
}

func (m *Manager) SetEnabled(enabled bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.config.Enabled = enabled
}

func (m *Manager) AddHeaderRule(rule types.HeaderRule) (types.HeaderRule, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	dbRule := model.HeaderRule{
		Name:      rule.Name,
		Value:     rule.Value,
		Operation: rule.Operation,
		Match:     rule.Match,
		Override:  rule.Override,
		Priority:  rule.Priority,
		Enabled:   rule.Enabled,
	}

	if err := m.db.Create(&dbRule).Error; err != nil {
		return rule, err
	}

	rule.ID = dbRule.ID
	m.config.HeaderRules = append(m.config.HeaderRules, rule)
	return rule, nil
}

func (m *Manager) UpdateHeaderRule(id int64, rule types.HeaderRule) (types.HeaderRule, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	dbRule := model.HeaderRule{
		ID:        id,
		Name:      rule.Name,
		Value:     rule.Value,
		Operation: rule.Operation,
		Match:     rule.Match,
		Override:  rule.Override,
		Priority:  rule.Priority,
		Enabled:   rule.Enabled,
	}

	if err := m.db.Save(&dbRule).Error; err != nil {
		return rule, err
	}

	rule.ID = id
	for i, r := range m.config.HeaderRules {
		if r.ID == id {
			m.config.HeaderRules[i] = rule
			break
		}
	}
	return rule, nil
}

func (m *Manager) DeleteHeaderRule(id int64) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if err := m.db.Delete(&model.HeaderRule{}, id).Error; err != nil {
		return err
	}

	for i, r := range m.config.HeaderRules {
		if r.ID == id {
			m.config.HeaderRules = append(m.config.HeaderRules[:i], m.config.HeaderRules[i+1:]...)
			break
		}
	}
	return nil
}

func (m *Manager) GetHeaderRules() []types.HeaderRule {
	m.mu.RLock()
	defer m.mu.RUnlock()
	rules := make([]types.HeaderRule, len(m.config.HeaderRules))
	copy(rules, m.config.HeaderRules)
	return rules
}

func (m *Manager) GetHeaderRule(id int64) (types.HeaderRule, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	for _, r := range m.config.HeaderRules {
		if r.ID == id {
			return r, true
		}
	}
	return types.HeaderRule{}, false
}

func (m *Manager) SetControlPlane(addr string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.config.ControlPlane = addr
}

func (m *Manager) AddProtoSchema(schema types.ProtoSchema) (types.ProtoSchema, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	dbSchema := model.ProtoSchema{
		MessageType:    schema.MessageType,
		ProtoFileName:  schema.ProtoFileName,
		FileDescriptor: schema.FileDescriptor,
		PackageName:    schema.PackageName,
		ServiceName:    schema.ServiceName,
		MethodName:     schema.MethodName,
		Description:    schema.Description,
		Enabled:        schema.Enabled,
	}

	if err := m.db.Create(&dbSchema).Error; err != nil {
		return schema, err
	}

	schema.ID = dbSchema.ID
	m.protoSchemas[schema.ID] = &types.ProtoSchema{
		ID:             schema.ID,
		MessageType:    schema.MessageType,
		ProtoFileName:  schema.ProtoFileName,
		FileDescriptor: schema.FileDescriptor,
		PackageName:    schema.PackageName,
		ServiceName:    schema.ServiceName,
		MethodName:     schema.MethodName,
		Description:    schema.Description,
		Enabled:        schema.Enabled,
	}
	return schema, nil
}

func (m *Manager) UpdateProtoSchema(id int64, schema types.ProtoSchema) (types.ProtoSchema, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	dbSchema := model.ProtoSchema{
		ID:             id,
		MessageType:    schema.MessageType,
		ProtoFileName:  schema.ProtoFileName,
		FileDescriptor: schema.FileDescriptor,
		PackageName:    schema.PackageName,
		ServiceName:    schema.ServiceName,
		MethodName:     schema.MethodName,
		Description:    schema.Description,
		Enabled:        schema.Enabled,
	}

	if err := m.db.Save(&dbSchema).Error; err != nil {
		return schema, err
	}

	schema.ID = id
	if existing, ok := m.protoSchemas[id]; ok {
		existing.MessageType = schema.MessageType
		existing.ProtoFileName = schema.ProtoFileName
		existing.FileDescriptor = schema.FileDescriptor
		existing.PackageName = schema.PackageName
		existing.ServiceName = schema.ServiceName
		existing.MethodName = schema.MethodName
		existing.Description = schema.Description
		existing.Enabled = schema.Enabled
	}
	return schema, nil
}

func (m *Manager) DeleteProtoSchema(id int64) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if err := m.db.Delete(&model.ProtoSchema{}, id).Error; err != nil {
		return err
	}

	delete(m.protoSchemas, id)
	return nil
}

func (m *Manager) GetProtoSchemas() []types.ProtoSchema {
	m.mu.RLock()
	defer m.mu.RUnlock()
	schemas := make([]types.ProtoSchema, 0, len(m.protoSchemas))
	for _, s := range m.protoSchemas {
		schemas = append(schemas, *s)
	}
	return schemas
}

func (m *Manager) GetProtoSchema(id int64) (types.ProtoSchema, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if s, ok := m.protoSchemas[id]; ok {
		return *s, true
	}
	return types.ProtoSchema{}, false
}

func (m *Manager) GetProtoSchemaByMessageType(messageType string) (types.ProtoSchema, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	for _, s := range m.protoSchemas {
		if s.MessageType == messageType && s.Enabled {
			return *s, true
		}
	}
	return types.ProtoSchema{}, false
}

func (m *Manager) GetProtoSchemaCount() int64 {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return int64(len(m.protoSchemas))
}

func (m *Manager) GetColorConfig() (bool, string, string) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.config.ColorEnabled, m.config.ColorHeader, m.config.ColorValue
}

func (m *Manager) UpdateColorConfig(enabled bool, header, value string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.config.ColorEnabled = enabled
	if header != "" {
		m.config.ColorHeader = header
	}
	if value != "" {
		m.config.ColorValue = value
	}
	return nil
}

func (m *Manager) GetAnomalyConfig() (bool, float64) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.config.AnomalyEnabled, m.config.AnomalyThreshold
}

func (m *Manager) UpdateAnomalyConfig(enabled bool, threshold float64) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.config.AnomalyEnabled = enabled
	if threshold >= 0 {
		m.config.AnomalyThreshold = threshold
	}
	return nil
}

func (m *Manager) DB() *gorm.DB {
	return m.db
}
