package compliance

import (
	"context"
	"math"
	"regexp"
	"strings"
	"sync"
	"time"
	"unicode"

	"github.com/sirupsen/logrus"
	"gorm.io/gorm"

	"github.com/keymgmt/service/backend/internal/models"
)

type ComplianceService struct {
	db        *gorm.DB
	log       *logrus.Logger
	mu        sync.Mutex
	isRunning bool
}

type PasswordStrength struct {
	Score       int      `json:"score"`
	Label       string   `json:"label"`
	Length      int      `json:"length"`
	HasUpper    bool     `json:"has_upper"`
	HasLower    bool     `json:"has_lower"`
	HasNumber   bool     `json:"has_number"`
	HasSpecial  bool     `json:"has_special"`
	CommonPattern bool   `json:"has_common_pattern"`
	Findings    []string `json:"findings"`
}

type ComplianceReport struct {
	TotalSecrets      int                  `json:"total_secrets"`
	PassedCount       int                  `json:"passed_count"`
	FailedCount       int                  `json:"failed_count"`
	AverageScore      float64              `json:"average_score"`
	CheckResults      []CheckResult        `json:"check_results"`
	GeneratedAt       time.Time            `json:"generated_at"`
}

type CheckResult struct {
	SecretID        string   `json:"secret_id"`
	SecretName      string   `json:"secret_name"`
	SecretType      string   `json:"secret_type"`
	OverallScore    int      `json:"overall_score"`
	Status          string   `json:"status"`
	StrengthScore   int      `json:"strength_score"`
	ExpiryStatus    string   `json:"expiry_status"`
	RotationStatus  string   `json:"rotation_status"`
	Findings        []string `json:"findings"`
	Recommendations []string `json:"recommendations"`
	CheckedAt       time.Time `json:"checked_at"`
}

type ComplianceConfig struct {
	MinPasswordLength      int
	MinPasswordScore       int
	MaxRotationDays        int
	ExpiryWarningDays      int
	EnableCommonChecks     bool
	AutoRotateWeakSecrets  bool
}

func DefaultConfig() ComplianceConfig {
	return ComplianceConfig{
		MinPasswordLength:     12,
		MinPasswordScore:      70,
		MaxRotationDays:       90,
		ExpiryWarningDays:     14,
		EnableCommonChecks:    true,
		AutoRotateWeakSecrets: false,
	}
}

func NewComplianceService(db *gorm.DB, log *logrus.Logger) *ComplianceService {
	return &ComplianceService{
		db:  db,
		log: log,
	}
}

func (cs *ComplianceService) CheckPasswordStrength(password string) PasswordStrength {
	result := PasswordStrength{
		Length:     len(password),
		Findings:   []string{},
	}

	for _, c := range password {
		switch {
		case unicode.IsUpper(c):
			result.HasUpper = true
		case unicode.IsLower(c):
			result.HasLower = true
		case unicode.IsNumber(c):
			result.HasNumber = true
		case unicode.IsSymbol(c) || unicode.IsPunct(c):
			result.HasSpecial = true
		}
	}

	score := 0

	if len(password) >= 8 {
		score += 10
	}
	if len(password) >= 12 {
		score += 10
	}
	if len(password) >= 16 {
		score += 10
	}

	if result.HasUpper {
		score += 15
	} else {
		result.Findings = append(result.Findings, "缺少大写字母")
	}

	if result.HasLower {
		score += 10
	} else {
		result.Findings = append(result.Findings, "缺少小写字母")
	}

	if result.HasNumber {
		score += 15
	} else {
		result.Findings = append(result.Findings, "缺少数字")
	}

	if result.HasSpecial {
		score += 20
	} else {
		result.Findings = append(result.Findings, "缺少特殊字符")
	}

	entropy := calculateEntropy(password)
	if entropy >= 60 {
		score += 20
	} else if entropy >= 40 {
		score += 10
	}

	commonPatterns := []string{
		"password", "123456", "qwerty", "admin", "secret",
		"welcome", "monkey", "dragon", "master", "iloveyou",
	}
	lowerPassword := strings.ToLower(password)
	for _, pattern := range commonPatterns {
		if strings.Contains(lowerPassword, pattern) {
			result.CommonPattern = true
			result.Findings = append(result.Findings, "包含常见密码模式")
			score -= 20
			break
		}
	}

	if match, _ := regexp.MatchString(`(.)\1{2,}`, password); match {
		result.Findings = append(result.Findings, "包含重复字符序列")
		score -= 10
	}

	if match, _ := regexp.MatchString(`0123|1234|2345|3456|4567|5678|6789|7890`, password); match {
		result.Findings = append(result.Findings, "包含连续数字序列")
		score -= 10
	}

	if score < 0 {
		score = 0
	}
	if score > 100 {
		score = 100
	}

	result.Score = score

	switch {
	case score >= 90:
		result.Label = "非常强"
	case score >= 70:
		result.Label = "强"
	case score >= 50:
		result.Label = "中等"
	case score >= 30:
		result.Label = "弱"
	default:
		result.Label = "非常弱"
	}

	return result
}

func calculateEntropy(s string) float64 {
	freq := make(map[rune]int)
	for _, c := range s {
		freq[c]++
	}

	entropy := 0.0
	n := len(s)
	for _, count := range freq {
		p := float64(count) / float64(n)
		entropy -= p * math.Log2(p)
	}

	return entropy * float64(n)
}

func (cs *ComplianceService) CheckSecret(ctx context.Context, secretID string, secretValue string, config ComplianceConfig) (*CheckResult, error) {
	var secret models.Secret
	if err := cs.db.Where("id = ? OR name = ?", secretID, secretID).First(&secret).Error; err != nil {
		return nil, err
	}

	strength := cs.CheckPasswordStrength(secretValue)
	result := &CheckResult{
		SecretID:      secret.ID.String(),
		SecretName:    secret.Name,
		SecretType:    secret.Type,
		StrengthScore: strength.Score,
		Findings:      strength.Findings,
		CheckedAt:     time.Now(),
	}

	overallScore := strength.Score

	if secret.ExpiresAt != nil {
		daysUntilExpiry := time.Until(*secret.ExpiresAt).Hours() / 24
		if daysUntilExpiry < 0 {
			result.ExpiryStatus = "已过期"
			result.Findings = append(result.Findings, "密钥已过期")
			overallScore -= 30
		} else if daysUntilExpiry < float64(config.ExpiryWarningDays) {
			result.ExpiryStatus = "即将过期"
			result.Findings = append(result.Findings, "密钥即将过期")
			overallScore -= 10
		} else {
			result.ExpiryStatus = "正常"
		}
	} else {
		result.ExpiryStatus = "未设置过期"
		result.Findings = append(result.Findings, "未设置过期时间")
		overallScore -= 5
	}

	daysSinceRotation := time.Since(secret.UpdatedAt).Hours() / 24
	if daysSinceRotation > float64(config.MaxRotationDays) {
		result.RotationStatus = "需要轮转"
		result.Findings = append(result.Findings, "密钥超过最大轮转周期")
		overallScore -= 20
	} else if daysSinceRotation > float64(config.MaxRotationDays)*0.7 {
		result.RotationStatus = "建议轮转"
		result.RotationStatus = "建议轮转"
		overallScore -= 5
	} else {
		result.RotationStatus = "正常"
	}

	if overallScore < 0 {
		overallScore = 0
	}
	if overallScore > 100 {
		overallScore = 100
	}
	result.OverallScore = overallScore

	if overallScore >= config.MinPasswordScore {
		result.Status = "通过"
	} else {
		result.Status = "失败"
	}

	result.Recommendations = cs.generateRecommendations(result, config)

	checkRecord := &models.ComplianceCheck{
		SecretID:        secret.ID,
		CheckType:       "full",
		Status:          result.Status,
		Score:           result.OverallScore,
		Findings:        strings.Join(result.Findings, "; "),
		Recommendations: strings.Join(result.Recommendations, "; "),
		CheckedAt:       result.CheckedAt,
		CheckedBy:       "system",
	}
	cs.db.Create(checkRecord)

	return result, nil
}

func (cs *ComplianceService) generateRecommendations(result *CheckResult, config ComplianceConfig) []string {
	var recommendations []string

	if result.StrengthScore < config.MinPasswordScore {
		recommendations = append(recommendations, "建议增强密钥强度，使用更长更复杂的密码")
	}

	if result.ExpiryStatus == "已过期" || result.ExpiryStatus == "即将过期" {
		recommendations = append(recommendations, "请立即更新过期或即将过期的密钥")
	}

	if result.RotationStatus == "需要轮转" || result.RotationStatus == "建议轮转" {
		recommendations = append(recommendations, "建议执行密钥轮转操作")
	}

	if len(result.Findings) > 0 {
		for _, finding := range result.Findings {
			if strings.Contains(finding, "缺少大写") {
				recommendations = append(recommendations, "添加大写字母以增强安全性")
			}
			if strings.Contains(finding, "缺少数字") {
				recommendations = append(recommendations, "添加数字以增强安全性")
			}
			if strings.Contains(finding, "缺少特殊字符") {
				recommendations = append(recommendations, "添加特殊字符以增强安全性")
			}
			if strings.Contains(finding, "常见密码模式") {
				recommendations = append(recommendations, "避免使用常见密码模式")
			}
		}
	}

	if len(recommendations) == 0 {
		recommendations = append(recommendations, "密钥符合安全要求，继续保持")
	}

	return recommendations
}

func (cs *ComplianceService) RunFullScan(ctx context.Context, config ComplianceConfig) (*ComplianceReport, error) {
	cs.mu.Lock()
	if cs.isRunning {
		cs.mu.Unlock()
		return nil, nil
	}
	cs.isRunning = true
	cs.mu.Unlock()

	defer func() {
		cs.mu.Lock()
		cs.isRunning = false
		cs.mu.Unlock()
	}()

	var secrets []models.Secret
	if err := cs.db.Find(&secrets).Error; err != nil {
		return nil, err
	}

	report := &ComplianceReport{
		TotalSecrets: len(secrets),
		CheckResults: make([]CheckResult, 0),
		GeneratedAt:  time.Now(),
	}

	totalScore := 0

	for _, secret := range secrets {
		var decryptedValue string
		if len(secret.EncryptedValue) > 0 {
			decryptedValue = string(secret.EncryptedValue)
		}

		result, err := cs.CheckSecret(ctx, secret.ID.String(), decryptedValue, config)
		if err != nil {
			cs.log.Warnf("Failed to check secret %s: %v", secret.Name, err)
			continue
		}

		report.CheckResults = append(report.CheckResults, *result)
		totalScore += result.OverallScore

		if result.Status == "通过" {
			report.PassedCount++
		} else {
			report.FailedCount++
		}
	}

	if len(report.CheckResults) > 0 {
		report.AverageScore = float64(totalScore) / float64(len(report.CheckResults))
	}

	cs.log.Infof("Compliance scan completed: %d secrets, passed: %d, failed: %d, avg score: %.2f",
		report.TotalSecrets, report.PassedCount, report.FailedCount, report.AverageScore)

	return report, nil
}

func (cs *ComplianceService) GetCheckHistory(ctx context.Context, secretID string, limit, offset int) ([]models.ComplianceCheck, int64, error) {
	var checks []models.ComplianceCheck
	var total int64

	query := cs.db.Model(&models.ComplianceCheck{})
	if secretID != "" {
		query = query.Where("secret_id = ?", secretID)
	}

	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	if err := query.Order("checked_at DESC").Limit(limit).Offset(offset).Find(&checks).Error; err != nil {
		return nil, 0, err
	}

	return checks, total, nil
}

func (cs *ComplianceService) StartPeriodicCheck(ctx context.Context, interval time.Duration, config ComplianceConfig) {
	go func() {
		ticker := time.NewTicker(interval)
		defer ticker.Stop()

		cs.log.Infof("Periodic compliance check started, interval: %v", interval)

		for {
			select {
			case <-ticker.C:
				cs.log.Info("Running periodic compliance check")
				_, err := cs.RunFullScan(ctx, config)
				if err != nil {
					cs.log.Errorf("Periodic compliance check failed: %v", err)
				}
			case <-ctx.Done():
				cs.log.Info("Periodic compliance check stopped")
				return
			}
		}
	}()
}
