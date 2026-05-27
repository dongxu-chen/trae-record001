package services

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"ssl-monitor/config"
	"ssl-monitor/models"
	"ssl-monitor/storage"
	"strings"
	"time"

	"go.uber.org/zap"
	"gorm.io/gorm"
)

type RuleLibraryService struct {
	version string
	rules   map[string]models.AlgorithmRule
}

func NewRuleLibraryService() *RuleLibraryService {
	svc := &RuleLibraryService{
		rules: make(map[string]models.AlgorithmRule),
	}

	svc.initDefaultRules()
	svc.loadFromDB()

	if config.Cfg.RuleLibrary.AutoUpdate {
		go svc.UpdateRules()
	}

	return svc
}

func (s *RuleLibraryService) initDefaultRules() {
	defaultRules := []models.AlgorithmRule{
		{RuleType: "signature", Algorithm: "MD2-RSA", Status: "insecure", MinBits: 0, Description: "MD2哈希算法已被攻破，不安全", Reference: "RFC 6149", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "signature", Algorithm: "MD5-RSA", Status: "insecure", MinBits: 0, Description: "MD5哈希算法已被攻破，不安全", Reference: "RFC 6151", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "signature", Algorithm: "SHA1-RSA", Status: "weak", MinBits: 0, Description: "SHA1哈希算法已被认为不安全，不建议使用", Reference: "NIST SP 800-131A", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "signature", Algorithm: "SHA1-DSA", Status: "weak", MinBits: 0, Description: "SHA1哈希算法已被认为不安全", Reference: "NIST SP 800-131A", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "signature", Algorithm: "SHA1-ECDSA", Status: "weak", MinBits: 0, Description: "SHA1哈希算法已被认为不安全", Reference: "NIST SP 800-131A", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "signature", Algorithm: "DSA-SHA1", Status: "weak", MinBits: 0, Description: "DSA算法已不推荐使用", Reference: "NIST SP 800-131A", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "signature", Algorithm: "DSA-SHA256", Status: "acceptable", MinBits: 2048, Description: "DSA算法已不推荐使用", Reference: "NIST SP 800-131A", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "signature", Algorithm: "SHA256-RSA", Status: "secure", MinBits: 2048, Description: "SHA256 with RSA，安全", Reference: "NIST SP 800-131A", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "signature", Algorithm: "SHA384-RSA", Status: "secure", MinBits: 2048, Description: "SHA384 with RSA，安全", Reference: "NIST SP 800-131A", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "signature", Algorithm: "SHA512-RSA", Status: "secure", MinBits: 2048, Description: "SHA512 with RSA，安全", Reference: "NIST SP 800-131A", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "signature", Algorithm: "ECDSA-SHA1", Status: "weak", MinBits: 0, Description: "SHA1哈希算法已被认为不安全", Reference: "NIST SP 800-131A", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "signature", Algorithm: "ECDSA-SHA256", Status: "secure", MinBits: 256, Description: "ECDSA with SHA256，安全", Reference: "NIST SP 800-131A", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "signature", Algorithm: "ECDSA-SHA384", Status: "secure", MinBits: 384, Description: "ECDSA with SHA384，安全", Reference: "NIST SP 800-131A", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "signature", Algorithm: "ECDSA-SHA512", Status: "secure", MinBits: 521, Description: "ECDSA with SHA512，安全", Reference: "NIST SP 800-131A", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "public_key", Algorithm: "RSA", Status: "secure", MinBits: 2048, Description: "RSA 2048位及以上，安全", Reference: "NIST SP 800-131A", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "public_key", Algorithm: "DSA", Status: "weak", MinBits: 2048, Description: "DSA算法已不推荐使用", Reference: "NIST SP 800-131A", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "public_key", Algorithm: "ECDSA (P-224)", Status: "acceptable", MinBits: 224, Description: "P-224曲线，建议使用P-256及以上", Reference: "NIST SP 800-186", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "public_key", Algorithm: "ECDSA (P-256)", Status: "secure", MinBits: 256, Description: "P-256曲线，安全", Reference: "NIST SP 800-186", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "public_key", Algorithm: "ECDSA (P-384)", Status: "secure", MinBits: 384, Description: "P-384曲线，安全", Reference: "NIST SP 800-186", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "public_key", Algorithm: "ECDSA (P-521)", Status: "secure", MinBits: 521, Description: "P-521曲线，安全", Reference: "NIST SP 800-186", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "public_key", Algorithm: "Ed25519", Status: "secure", MinBits: 256, Description: "Ed25519，安全", Reference: "RFC 8032", Source: "default", UpdatedAt: time.Now()},
		{RuleType: "public_key", Algorithm: "Ed448", Status: "secure", MinBits: 448, Description: "Ed448，安全", Reference: "RFC 8032", Source: "default", UpdatedAt: time.Now()},
	}

	db := storage.GetDB()
	for _, rule := range defaultRules {
		var existing models.AlgorithmRule
		if err := db.Where("algorithm = ? AND source = ?", rule.Algorithm, "default").First(&existing).Error; err == gorm.ErrRecordNotFound {
			rule.Version = "v1.0.0"
			db.Create(&rule)
		}
	}

	s.version = "v1.0.0"
}

func (s *RuleLibraryService) loadFromDB() {
	db := storage.GetDB()
	var rules []models.AlgorithmRule
	if err := db.Find(&rules).Error; err != nil {
		config.Logger.Error("加载规则库失败", zap.Error(err))
		return
	}

	for _, rule := range rules {
		s.rules[rule.Algorithm] = rule
	}

	config.Logger.Info("规则库加载完成", zap.Int("count", len(rules)))
}

func (s *RuleLibraryService) UpdateRules() (models.RuleUpdateLog, error) {
	log := models.RuleUpdateLog{
		Status:    "success",
		Source:    config.Cfg.RuleLibrary.SourceURL,
		UpdatedAt: time.Now(),
	}

	if !config.Cfg.RuleLibrary.Enabled {
		log.Status = "skipped"
		log.ErrorMsg = "规则库更新未启用"
		s.saveUpdateLog(log)
		return log, nil
	}

	newVersion := fmt.Sprintf("v1.%d", time.Now().Unix())

	var rulesFromSource []models.AlgorithmRule
	var err error

	if config.Cfg.RuleLibrary.SourceURL != "" {
		rulesFromSource, err = s.fetchFromURL()
		if err != nil {
			config.Logger.Warn("从远程获取规则失败，使用本地规则", zap.Error(err))
		}
	}

	if config.Cfg.RuleLibrary.LocalFile != "" {
		localRules, err := s.loadFromLocalFile()
		if err == nil {
			rulesFromSource = append(rulesFromSource, localRules...)
		}
	}

	db := storage.GetDB()
	tx := db.Begin()

	for _, rule := range rulesFromSource {
		rule.Version = newVersion
		rule.Source = "remote"
		rule.UpdatedAt = time.Now()

		var existing models.AlgorithmRule
		if err := tx.Where("algorithm = ?", rule.Algorithm).First(&existing).Error; err == nil {
			if existing.Description != rule.Description || existing.Status != rule.Status || existing.MinBits != rule.MinBits {
				existing.Description = rule.Description
				existing.Status = rule.Status
				existing.MinBits = rule.MinBits
				existing.Reference = rule.Reference
				existing.Version = newVersion
				existing.UpdatedAt = time.Now()
				tx.Save(&existing)
				log.UpdatedRules++
			}
			s.rules[rule.Algorithm] = existing
		} else {
			tx.Create(&rule)
			log.AddedRules++
			s.rules[rule.Algorithm] = rule
		}
	}

	var allRules []models.AlgorithmRule
	tx.Find(&allRules)
	log.TotalRules = len(allRules)

	if err := tx.Commit().Error; err != nil {
		tx.Rollback()
		log.Status = "failed"
		log.ErrorMsg = err.Error()
		s.saveUpdateLog(log)
		return log, err
	}

	s.version = newVersion
	s.saveUpdateLog(log)

	config.Logger.Info("规则库更新完成",
		zap.String("version", newVersion),
		zap.Int("added", log.AddedRules),
		zap.Int("updated", log.UpdatedRules),
		zap.Int("total", log.TotalRules))

	return log, nil
}

func (s *RuleLibraryService) fetchFromURL() ([]models.AlgorithmRule, error) {
	client := &http.Client{
		Timeout: time.Duration(config.Cfg.Scan.TimeoutSeconds) * time.Second,
	}

	resp, err := client.Get(config.Cfg.RuleLibrary.SourceURL)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var rawData []map[string]interface{}
	if err := json.Unmarshal(body, &rawData); err != nil {
		return nil, err
	}

	var rules []models.AlgorithmRule
	for _, item := range rawData {
		algo, _ := item["algorithm"].(string)
		status, _ := item["status"].(string)
		ruleType, _ := item["type"].(string)
		description, _ := item["description"].(string)
		reference, _ := item["reference"].(string)

		if algo == "" {
			continue
		}

		minBits := 0
		if mb, ok := item["min_bits"].(float64); ok {
			minBits = int(mb)
		}

		rules = append(rules, models.AlgorithmRule{
			Algorithm:   algo,
			Status:      status,
			RuleType:    ruleType,
			MinBits:     minBits,
			Description: description,
			Reference:   reference,
		})
	}

	return rules, nil
}

func (s *RuleLibraryService) loadFromLocalFile() ([]models.AlgorithmRule, error) {
	filePath := config.Cfg.RuleLibrary.LocalFile
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return nil, err
	}

	body, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}

	var rules []models.AlgorithmRule
	if err := json.Unmarshal(body, &rules); err != nil {
		return nil, err
	}

	for i := range rules {
		rules[i].Source = "local"
	}

	return rules, nil
}

func (s *RuleLibraryService) CheckAlgorithmStrength(algo string, bits int) models.AlgoStrengthResult {
	algo = strings.TrimSpace(algo)
	result := models.AlgoStrengthResult{
		Algorithm:   algo,
		Bits:        bits,
		Status:      "unknown",
		Description: "未找到对应规则，建议人工审核",
		Score:       0,
	}

	rule, exists := s.rules[algo]
	if !exists {
		for ruleAlgo, rule := range s.rules {
			if strings.HasPrefix(algo, ruleAlgo) || strings.Contains(algo, ruleAlgo) {
				exists = true
				break
			}
			_ = rule
		}
	}

	if exists {
		result.Status = rule.Status
		result.Description = rule.Description

		switch rule.Status {
		case "secure":
			result.Score = 100
			if bits > 0 && rule.MinBits > 0 && bits < rule.MinBits {
				result.Status = "weak"
				result.Score = 50
				result.Description = fmt.Sprintf("密钥位数不足(%d位)，建议至少%d位。%s", bits, rule.MinBits, rule.Description)
			}
		case "acceptable":
			result.Score = 70
			if bits > 0 && rule.MinBits > 0 && bits < rule.MinBits {
				result.Status = "weak"
				result.Score = 40
			}
		case "weak":
			result.Score = 30
		case "insecure":
			result.Score = 0
		}
	}

	return result
}

func (s *RuleLibraryService) CheckSignatureAlgorithm(algo string) models.AlgoStrengthResult {
	return s.CheckAlgorithmStrength(algo, 0)
}

func (s *RuleLibraryService) CheckPublicKeyAlgorithm(algo string, bits int) models.AlgoStrengthResult {
	return s.CheckAlgorithmStrength(algo, bits)
}

func (s *RuleLibraryService) GetAllRules() ([]models.AlgorithmRule, error) {
	db := storage.GetDB()
	var rules []models.AlgorithmRule
	err := db.Order("rule_type, status, algorithm").Find(&rules).Error
	return rules, err
}

func (s *RuleLibraryService) GetRulesByType(ruleType string) ([]models.AlgorithmRule, error) {
	db := storage.GetDB()
	var rules []models.AlgorithmRule
	err := db.Where("rule_type = ?", ruleType).Order("status, algorithm").Find(&rules).Error
	return rules, err
}

func (s *RuleLibraryService) GetUpdateLogs(page, pageSize int) ([]models.RuleUpdateLog, int64, error) {
	db := storage.GetDB()
	var logs []models.RuleUpdateLog
	var total int64

	offset := (page - 1) * pageSize

	db.Model(&models.RuleUpdateLog{}).Count(&total)
	err := db.Order("updated_at DESC").Offset(offset).Limit(pageSize).Find(&logs).Error

	return logs, total, err
}

func (s *RuleLibraryService) saveUpdateLog(log models.RuleUpdateLog) {
	db := storage.GetDB()
	db.Create(&log)
}

func (s *RuleLibraryService) GetVersion() string {
	return s.version
}

func (s *RuleLibraryService) AddCustomRule(rule models.AlgorithmRule) error {
	db := storage.GetDB()
	rule.Source = "custom"
	rule.Version = fmt.Sprintf("custom-%d", time.Now().Unix())
	rule.UpdatedAt = time.Now()

	if err := db.Create(&rule).Error; err != nil {
		return err
	}

	s.rules[rule.Algorithm] = rule
	return nil
}

func (s *RuleLibraryService) UpdateCustomRule(id uint, updates map[string]interface{}) error {
	db := storage.GetDB()
	var rule models.AlgorithmRule
	if err := db.First(&rule, id).Error; err != nil {
		return err
	}

	if rule.Source != "custom" {
		return fmt.Errorf("只能修改自定义规则")
	}

	updates["updated_at"] = time.Now()
	if err := db.Model(&rule).Updates(updates).Error; err != nil {
		return err
	}

	db.First(&rule, id)
	s.rules[rule.Algorithm] = rule
	return nil
}

func (s *RuleLibraryService) DeleteCustomRule(id uint) error {
	db := storage.GetDB()
	var rule models.AlgorithmRule
	if err := db.First(&rule, id).Error; err != nil {
		return err
	}

	if rule.Source != "custom" {
		return fmt.Errorf("只能删除自定义规则")
	}

	if err := db.Delete(&rule).Error; err != nil {
		return err
	}

	delete(s.rules, rule.Algorithm)
	return nil
}

func (s *RuleLibraryService) ExportRules() ([]byte, error) {
	rules, err := s.GetAllRules()
	if err != nil {
		return nil, err
	}

	return json.MarshalIndent(rules, "", "  ")
}

func (s *RuleLibraryService) ImportRules(data []byte) (int, error) {
	var rules []models.AlgorithmRule
	if err := json.Unmarshal(data, &rules); err != nil {
		return 0, err
	}

	db := storage.GetDB()
	tx := db.Begin()
	count := 0

	for _, rule := range rules {
		rule.Source = "imported"
		rule.Version = fmt.Sprintf("imported-%d", time.Now().Unix())
		rule.UpdatedAt = time.Now()

		var existing models.AlgorithmRule
		if err := tx.Where("algorithm = ?", rule.Algorithm).First(&existing).Error; err == nil {
			existing.Description = rule.Description
			existing.Status = rule.Status
			existing.MinBits = rule.MinBits
			existing.RuleType = rule.RuleType
			existing.Reference = rule.Reference
			existing.UpdatedAt = time.Now()
			tx.Save(&existing)
		} else {
			tx.Create(&rule)
		}
		count++
		s.rules[rule.Algorithm] = rule
	}

	if err := tx.Commit().Error; err != nil {
		tx.Rollback()
		return 0, err
	}

	return count, nil
}

func (s *RuleLibraryService) SaveToLocalFile() error {
	data, err := s.ExportRules()
	if err != nil {
		return err
	}

	dir := filepath.Dir(config.Cfg.RuleLibrary.LocalFile)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}

	return os.WriteFile(config.Cfg.RuleLibrary.LocalFile, data, 0644)
}
