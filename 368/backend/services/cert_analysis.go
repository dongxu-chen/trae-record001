package services

import (
	"bytes"
	"crypto/sha256"
	"crypto/x509"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"ssl-monitor/config"
	"ssl-monitor/models"
	"ssl-monitor/storage"
	"strings"
	"time"

	"go.uber.org/zap"
)

type CertAnalysisService struct {
	alertSvc *AlertService
}

func NewCertAnalysisService(alertSvc *AlertService) *CertAnalysisService {
	return &CertAnalysisService{
		alertSvc: alertSvc,
	}
}

func (s *CertAnalysisService) CheckCertChain(certs []*x509.Certificate, domain string) *models.CertChainInfo {
	result := &models.CertChainInfo{
		ChainLength:  len(certs),
		Complete:     false,
	}

	if len(certs) == 0 {
		result.Errors = append(result.Errors, "未获取到证书链")
		return result
	}

	for i, cert := range certs {
		if i == 0 {
			continue
		}
		if cert.IsCA {
			result.Intermediates = append(result.Intermediates, cert.Subject.CommonName)
		}
	}

	if len(certs) >= 2 {
		lastCert := certs[len(certs)-1]
		if lastCert.IsCA && bytes.Equal(lastCert.RawIssuer, lastCert.RawSubject) {
			result.RootCA = lastCert.Subject.CommonName
		}
	}

	rootPool := x509.NewCertPool()
	for _, cert := range certs[1:] {
		rootPool.AddCert(cert)
	}

	leafCert := certs[0]
	opts := x509.VerifyOptions{
		Roots:         rootPool,
		Intermediates: rootPool,
		DNSName:       domain,
	}

	if _, err := leafCert.Verify(opts); err != nil {
		result.Errors = append(result.Errors, fmt.Sprintf("证书链验证失败: %v", err))

		errStr := err.Error()
		if strings.Contains(errStr, "certificate signed by unknown authority") ||
		   strings.Contains(errStr, "unable to find valid certification path") {
			result.MissingCerts = append(result.MissingCerts, "中间证书或根证书缺失")
		}
		if strings.Contains(errStr, "certificate has expired") {
			result.MissingCerts = append(result.MissingCerts, "证书链中存在过期证书")
		}
		if strings.Contains(errStr, "certificate is not standards compliant") {
			result.Errors = append(result.Errors, "证书不符合标准")
		}
	} else {
		result.Complete = true
	}

	return result
}

func (s *CertAnalysisService) CheckCertChainAndAlert(certs []*x509.Certificate, domain string, domainID uint) *models.CertChainInfo {
	result := s.CheckCertChain(certs, domain)

	if !result.Complete && s.alertSvc != nil {
		alertContent := fmt.Sprintf(
			"域名 %s 证书链不完整: %s",
			domain,
			strings.Join(result.MissingCerts, ", "),
		)
		go s.alertSvc.SendCertIssueAlert(
			domain,
			domainID,
			alertContent,
			"warning",
		)
	}

	return result
}

var ctLogServers = []struct {
	Name     string
	Operator string
	URL      string
}{
	{
		Name:     "Google Argon2025",
		Operator: "Google",
		URL:      "https://ct.googleapis.com/logs/argon2025/",
	},
	{
		Name:     "Google Xenon2025",
		Operator: "Google",
		URL:      "https://ct.googleapis.com/logs/xenon2025/",
	},
	{
		Name:     "Let's Encrypt Oak2025",
		Operator: "Let's Encrypt",
		URL:      "https://oak.ct.letsencrypt.org/2025/",
	},
	{
		Name:     "Cloudflare Nimbus2025",
		Operator: "Cloudflare",
		URL:      "https://ct.cloudflare.com/logs/nimbus2025/",
	},
	{
		Name:     "DigiCert Yeti2025",
		Operator: "DigiCert",
		URL:      "https://yeti2025.ct.digicert.com/log/",
	},
	{
		Name:     "Sectigo Sabre",
		Operator: "Sectigo",
		URL:      "https://sabre.ct.comodo.com/",
	},
}

func (s *CertAnalysisService) CheckCTLog(cert *x509.Certificate, domain string) *models.CTLogResult {
	result := &models.CTLogResult{
		Logged:   false,
		LogCount: 0,
	}

	certHash := sha256.Sum256(cert.Raw)
	certHashHex := hex.EncodeToString(certHash[:])

	config.Logger.Debug("开始CT日志检查",
		zap.String("domain", domain),
		zap.String("cert_hash", certHashHex[:16]+"..."),
	)

	for _, logServer := range ctLogServers {
		found, err := s.queryCTLogServer(logServer.URL, certHashHex, cert)
		if err != nil {
			result.Errors = append(result.Errors,
				fmt.Sprintf("%s: %v", logServer.Name, err),
			)
			continue
		}

		if found {
			result.Logged = true
			result.LogCount++
			result.Entries = append(result.Entries, models.CTLogEntry{
				LogOperator: logServer.Operator,
				LogName:     logServer.Name,
				Timestamp:   time.Now(),
				EntryHash:   certHashHex,
			})
		}
	}

	if !result.Logged {
		result.Unlogged = true
		config.Logger.Warn("证书未在CT日志中发现",
			zap.String("domain", domain),
			zap.String("serial_number", cert.SerialNumber.String()),
		)

		if s.alertSvc != nil {
			alertContent := fmt.Sprintf(
				"域名 %s 的证书未在公开的证书透明度日志中发现，可能存在安全风险",
				domain,
			)
			var domainID uint
			db := storage.GetDB()
			var d models.Domain
			if err := db.Where("domain_name = ?", domain).First(&d).Error; err == nil {
				domainID = d.ID
			}

			go s.alertSvc.SendCertIssueAlert(
				domain,
				domainID,
				alertContent,
				"warning",
			)
		}
	}

	config.Logger.Debug("CT日志检查完成",
		zap.String("domain", domain),
		zap.Bool("logged", result.Logged),
		zap.Int("log_count", result.LogCount),
	)

	return result
}

func (s *CertAnalysisService) queryCTLogServer(baseURL, certHash string, cert *x509.Certificate) (bool, error) {
	client := &http.Client{
		Timeout: 5 * time.Second,
	}

	sthURL := baseURL + "ct/v1/get-sth"
	resp, err := client.Get(sthURL)
	if err != nil {
		return false, fmt.Errorf("连接CT日志服务器失败: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return false, fmt.Errorf("CT日志服务器返回状态码: %d", resp.StatusCode)
	}

	return s.checkSCTs(cert)
}

func (s *CertAnalysisService) checkSCTs(cert *x509.Certificate) bool {
	for _, ext := range cert.Extensions {
		if ext.Id.String() == "1.3.6.1.4.1.11129.2.4.2" {
			return true
		}
	}

	for _, ext := range cert.ExtraExtensions {
		if ext.Id.String() == "1.3.6.1.4.1.11129.2.4.2" {
			return true
		}
	}

	return false
}

func (s *CertAnalysisService) CompareCerts(oldCert, newCert *models.CertRecord) *models.CertCompareResult {
	result := &models.CertCompareResult{
		Domain:         newCert.Domain,
		OldCertID:      oldCert.ID,
		NewCertID:      newCert.ID,
		OldFingerprint: oldCert.Fingerprint,
		NewFingerprint: newCert.Fingerprint,
		ComparedAt:     time.Now(),
	}

	fieldsToCompare := []struct {
		Name      string
		OldVal    interface{}
		NewVal    interface{}
		Important bool
	}{
		{
			Name:      "subject",
			OldVal:    oldCert.Subject,
			NewVal:    newCert.Subject,
			Important: false,
		},
		{
			Name:      "issuer",
			OldVal:    oldCert.Issuer,
			NewVal:    newCert.Issuer,
			Important: true,
		},
		{
			Name:      "not_before",
			OldVal:    oldCert.NotBefore.Format("2006-01-02"),
			NewVal:    newCert.NotBefore.Format("2006-01-02"),
			Important: false,
		},
		{
			Name:      "not_after",
			OldVal:    oldCert.NotAfter.Format("2006-01-02"),
			NewVal:    newCert.NotAfter.Format("2006-01-02"),
			Important: false,
		},
		{
			Name:      "signature_algo",
			OldVal:    oldCert.SignatureAlgo,
			NewVal:    newCert.SignatureAlgo,
			Important: true,
		},
		{
			Name:      "public_key_algo",
			OldVal:    oldCert.PublicKeyAlgo,
			NewVal:    newCert.PublicKeyAlgo,
			Important: true,
		},
		{
			Name:      "public_key_bits",
			OldVal:    oldCert.PublicKeyBits,
			NewVal:    newCert.PublicKeyBits,
			Important: true,
		},
		{
			Name:      "serial_number",
			OldVal:    oldCert.SerialNumber,
			NewVal:    newCert.SerialNumber,
			Important: false,
		},
		{
			Name:      "fingerprint",
			OldVal:    oldCert.Fingerprint,
			NewVal:    newCert.Fingerprint,
			Important: false,
		},
		{
			Name:      "sans",
			OldVal:    oldCert.SANs,
			NewVal:    newCert.SANs,
			Important: false,
		},
		{
			Name:      "version",
			OldVal:    oldCert.Version,
			NewVal:    newCert.Version,
			Important: false,
		},
		{
			Name:      "cert_chain_complete",
			OldVal:    oldCert.CertChainComplete,
			NewVal:    newCert.CertChainComplete,
			Important: true,
		},
		{
			Name:      "ct_logged",
			OldVal:    oldCert.CTLogged,
			NewVal:    newCert.CTLogged,
			Important: true,
		},
	}

	for _, field := range fieldsToCompare {
		diff := s.compareField(field.Name, field.OldVal, field.NewVal, field.Important)
		if diff != nil {
			result.Diffs = append(result.Diffs, *diff)
			result.DiffCount++
			if field.Important {
				result.ImportantDiffs = append(result.ImportantDiffs, *diff)
			}
		}
	}

	if oldCert.Issuer != newCert.Issuer {
		result.IsIssuerChanged = true
	}

	if oldCert.SignatureAlgo != newCert.SignatureAlgo ||
	   oldCert.PublicKeyAlgo != newCert.PublicKeyAlgo ||
	   oldCert.PublicKeyBits != newCert.PublicKeyBits {
		result.IsAlgoChanged = true
	}

	if oldCert.Fingerprint != newCert.Fingerprint &&
	   oldCert.Issuer == newCert.Issuer &&
	   oldCert.Subject == newCert.Subject {
		result.IsRenewal = true
	}

	return result
}

func (s *CertAnalysisService) compareField(name string, oldVal, newVal interface{}, important bool) *models.CertDiff {
	oldStr := fmt.Sprintf("%v", oldVal)
	newStr := fmt.Sprintf("%v", newVal)

	if oldStr == newStr {
		return nil
	}

	changeType := "modified"
	if oldStr == "" {
		changeType = "added"
	} else if newStr == "" {
		changeType = "removed"
	}

	if name == "sans" {
		oldSans := strings.Split(oldStr, ", ")
		newSans := strings.Split(newStr, ", ")

		added, removed := s.compareStringSlices(oldSans, newSans)
		if len(added) > 0 || len(removed) > 0 {
			return &models.CertDiff{
				Field:      name,
				OldValue:   oldVal,
				NewValue:   newVal,
				ChangeType: changeType,
			}
		}
		return nil
	}

	return &models.CertDiff{
		Field:      name,
		OldValue:   oldVal,
		NewValue:   newVal,
		ChangeType: changeType,
	}
}

func (s *CertAnalysisService) compareStringSlices(old, new []string) (added, removed []string) {
	oldMap := make(map[string]bool)
	newMap := make(map[string]bool)

	for _, s := range old {
		oldMap[strings.TrimSpace(s)] = true
	}
	for _, s := range new {
		newMap[strings.TrimSpace(s)] = true
	}

	for _, s := range new {
		s = strings.TrimSpace(s)
		if !oldMap[s] {
			added = append(added, s)
		}
	}

	for _, s := range old {
		s = strings.TrimSpace(s)
		if !newMap[s] {
			removed = append(removed, s)
		}
	}

	return added, removed
}

func (s *CertAnalysisService) CompareWithPrevious(domainID uint) (*models.CertCompareResult, error) {
	db := storage.GetDB()

	var records []models.CertRecord
	err := db.Where("domain_id = ?", domainID).
		Order("created_at DESC").
		Limit(2).
		Find(&records).Error

	if err != nil {
		return nil, fmt.Errorf("查询证书记录失败: %w", err)
	}

	if len(records) < 2 {
		return nil, fmt.Errorf("证书记录不足，无法对比")
	}

	return s.CompareCerts(&records[1], &records[0]), nil
}

func (s *CertAnalysisService) GetAllCertChanges(domainID uint, limit int) ([]models.CertCompareResult, error) {
	db := storage.GetDB()

	var records []models.CertRecord
	err := db.Where("domain_id = ?", domainID).
		Order("created_at DESC").
		Limit(limit + 1).
		Find(&records).Error

	if err != nil {
		return nil, fmt.Errorf("查询证书记录失败: %w", err)
	}

	var results []models.CertCompareResult
	for i := len(records) - 1; i > 0; i-- {
		if i+1 < len(records) {
			result := s.CompareCerts(&records[i], &records[i-1])
			results = append(results, *result)
		}
	}

	return results, nil
}

func (s *CertAnalysisService) GetUnloggedCerts() ([]models.CertRecord, error) {
	db := storage.GetDB()
	var records []models.CertRecord

	subQuery := db.Model(&models.CertRecord{}).
		Select("MAX(last_checked_at)").
		Where("domain_id = cert_records.domain_id").
		Table("cert_records")

	err := db.Preload("Domain").
		Where("last_checked_at = (?) AND ct_logged = ?", subQuery, false).
		Where("status != ?", "error").
		Find(&records).Error

	return records, err
}

func (s *CertAnalysisService) GetIncompleteChainCerts() ([]models.CertRecord, error) {
	db := storage.GetDB()
	var records []models.CertRecord

	subQuery := db.Model(&models.CertRecord{}).
		Select("MAX(last_checked_at)").
		Where("domain_id = cert_records.domain_id").
		Table("cert_records")

	err := db.Preload("Domain").
		Where("last_checked_at = (?) AND cert_chain_complete = ?", subQuery, false).
		Where("status != ?", "error").
		Find(&records).Error

	return records, err
}

type CTLogMonitorConfig struct {
	Enabled    bool `mapstructure:"enabled"`
	AutoAlert  bool `mapstructure:"auto_alert"`
	AutoCheck  bool `mapstructure:"auto_check"`
}

type CertChainConfig struct {
	Enabled    bool `mapstructure:"enabled"`
	AutoAlert  bool `mapstructure:"auto_alert"`
}
