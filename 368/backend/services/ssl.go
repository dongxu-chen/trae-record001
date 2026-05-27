package services

import (
	"crypto/dsa"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/tls"
	"crypto/x509"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math/rand"
	"net"
	"ssl-monitor/config"
	"ssl-monitor/models"
	"ssl-monitor/storage"
	"strings"
	"sync"
	"time"

	"go.uber.org/zap"
	"gorm.io/gorm"
)

type SSLCertService struct {
	ruleSvc        *RuleLibraryService
	dnsSvc         *DNSService
	certAnalysisSvc *CertAnalysisService
}

func NewSSLCertService(ruleSvc *RuleLibraryService, dnsSvc *DNSService, certAnalysisSvc *CertAnalysisService) *SSLCertService {
	return &SSLCertService{
		ruleSvc:         ruleSvc,
		dnsSvc:          dnsSvc,
		certAnalysisSvc: certAnalysisSvc,
	}
}

type CertResult struct {
	Domain              string
	Port                int
	CertRecord          *models.CertRecord
	Error               error
	AlgoStrength        *models.AlgoStrengthResult
	SignatureStrength   *models.AlgoStrengthResult
	CertChainInfo       *models.CertChainInfo
	CTLogResult         *models.CTLogResult
}

type scanTask struct {
	domain   models.Domain
	result   chan *CertResult
	retryCount int
}

func (s *SSLCertService) CheckDomain(domainName string, port int) *CertResult {
	result := &CertResult{
		Domain: domainName,
		Port:   port,
	}

	db := storage.GetDB()
	var domain models.Domain
	if err := db.Where("domain_name = ?", domainName).First(&domain).Error; err != nil {
		result.Error = fmt.Errorf("域名 %s 不存在", domainName)
		return result
	}

	certRecord, certChainInfo, ctLogResult, err := s.fetchCertInfoWithRetry(domainName, port)
	if err != nil {
		certRecord = &models.CertRecord{
			DomainID:      domain.ID,
			Domain:        domainName,
			Port:          port,
			Status:        "error",
			ErrorMsg:      err.Error(),
			LastCheckedAt: time.Now(),
		}
		result.CertRecord = certRecord
		result.Error = err
	} else {
		certRecord.DomainID = domain.ID
		result.CertRecord = certRecord
		result.CertChainInfo = certChainInfo
		result.CTLogResult = ctLogResult

		if s.ruleSvc != nil {
			result.AlgoStrength = &s.ruleSvc.CheckPublicKeyAlgorithm(certRecord.PublicKeyAlgo, certRecord.PublicKeyBits)
			result.SignatureStrength = &s.ruleSvc.CheckSignatureAlgorithm(certRecord.SignatureAlgo)
		}

		if s.dnsSvc != nil && config.Cfg.DNS.AutoDiscoverSubdomains {
			s.dnsSvc.DiscoverSubdomainsFromCert(domainName, certRecord.SANs)
		}
	}

	s.saveCertRecord(certRecord)

	return result
}

func (s *SSLCertService) CheckAllDomains() []*CertResult {
	db := storage.GetDB()
	var domains []models.Domain
	if err := db.Where("enabled = ?", true).Find(&domains).Error; err != nil {
		config.Logger.Error("查询域名列表失败", zap.Error(err))
		return nil
	}

	maxConcurrent := config.Cfg.Scan.MaxConcurrent
	if maxConcurrent <= 0 {
		maxConcurrent = 5
	}
	if maxConcurrent > len(domains) {
		maxConcurrent = len(domains)
	}

	config.Logger.Info("开始SSL证书扫描",
		zap.Int("total_domains", len(domains)),
		zap.Int("max_concurrent", maxConcurrent))

	taskChan := make(chan scanTask, len(domains))
	resultChan := make(chan *CertResult, len(domains))

	var wg sync.WaitGroup
	for i := 0; i < maxConcurrent; i++ {
		wg.Add(1)
		go s.worker(i, taskChan, resultChan, &wg)
	}

	for _, domain := range domains {
		taskChan <- scanTask{
			domain:     domain,
			result:     nil,
			retryCount: 0,
		}
	}
	close(taskChan)

	go func() {
		wg.Wait()
		close(resultChan)
	}()

	var results []*CertResult
	for result := range resultChan {
		results = append(results, result)

		if result.Error != nil {
			config.Logger.Warn("SSL证书检查失败",
				zap.String("domain", result.Domain),
				zap.Error(result.Error))
		}
	}

	config.Logger.Info("SSL证书扫描完成",
		zap.Int("scanned", len(results)),
		zap.Int("total", len(domains)))

	return results
}

func (s *SSLCertService) worker(id int, tasks <-chan scanTask, results chan<- *CertResult, wg *sync.WaitGroup) {
	defer wg.Done()

	config.Logger.Debug("SSL扫描worker启动", zap.Int("worker_id", id))

	for task := range tasks {
		config.Logger.Debug("worker处理任务",
			zap.Int("worker_id", id),
			zap.String("domain", task.domain.DomainName))

		result := s.CheckDomain(task.domain.DomainName, task.domain.Port)
		results <- result

		s.randomDelay()
	}

	config.Logger.Debug("SSL扫描worker退出", zap.Int("worker_id", id))
}

func (s *SSLCertService) fetchCertInfoWithRetry(domainName string, port int) (*models.CertRecord, *models.CertChainInfo, *models.CTLogResult, error) {
	maxRetries := config.Cfg.Scan.RetryCount
	if maxRetries < 0 {
		maxRetries = 0
	}

	var lastErr error
	for attempt := 0; attempt <= maxRetries; attempt++ {
		record, chainInfo, ctResult, err := s.fetchCertInfo(domainName, port)
		if err == nil {
			return record, chainInfo, ctResult, nil
		}

		lastErr = err

		if attempt < maxRetries {
			retryDelay := config.Cfg.Scan.RetryDelayMs
			if retryDelay <= 0 {
				retryDelay = 500
			}
			config.Logger.Debug("SSL连接重试",
				zap.String("domain", domainName),
				zap.Int("attempt", attempt+1),
				zap.Int("max_retries", maxRetries),
				zap.Error(err))

			time.Sleep(time.Duration(retryDelay) * time.Millisecond)
		}
	}

	return nil, nil, nil, fmt.Errorf("经过%d次重试后仍然失败: %w", maxRetries+1, lastErr)
}

func (s *SSLCertService) fetchCertInfo(domainName string, port int) (*models.CertRecord, *models.CertChainInfo, *models.CTLogResult, error) {
	addr := fmt.Sprintf("%s:%d", domainName, port)

	timeout := config.Cfg.Scan.TimeoutSeconds
	if timeout <= 0 {
		timeout = 15
	}

	dialer := &net.Dialer{
		Timeout: time.Duration(timeout) * time.Second,
	}

	conn, err := tls.DialWithDialer(dialer, "tcp", addr, &tls.Config{
		InsecureSkipVerify: true,
		ServerName:         domainName,
	})
	if err != nil {
		return nil, nil, nil, fmt.Errorf("连接失败: %w", err)
	}
	defer conn.Close()

	certs := conn.ConnectionState().PeerCertificates
	if len(certs) == 0 {
		return nil, nil, nil, fmt.Errorf("未获取到证书")
	}

	leafCert := certs[0]

	var certChainInfo *models.CertChainInfo
	if s.certAnalysisSvc != nil {
		var domainID uint
		db := storage.GetDB()
		var d models.Domain
		if err := db.Where("domain_name = ?", domainName).First(&d).Error; err == nil {
			domainID = d.ID
		}
		certChainInfo = s.certAnalysisSvc.CheckCertChainAndAlert(certs, domainName, domainID)
	}

	var ctLogResult *models.CTLogResult
	if s.certAnalysisSvc != nil {
		ctLogResult = s.certAnalysisSvc.CheckCTLog(leafCert, domainName)
	}

	daysLeft := int(time.Until(leafCert.NotAfter).Hours() / 24)
	status := s.calculateStatus(daysLeft)

	signatureAlgo := s.getSignatureAlgorithm(leafCert.SignatureAlgorithm)
	publicKeyAlgo, publicKeyBits := s.getPublicKeyInfo(leafCert)

	var sans []string
	sans = append(sans, leafCert.DNSNames...)
	sans = append(sans, leafCert.EmailAddresses...)
	for _, ip := range leafCert.IPAddresses {
		sans = append(sans, ip.String())
	}

	fingerprint := sha256.Sum256(leafCert.Raw)

	certRecord := &models.CertRecord{
		Domain:        domainName,
		Port:          port,
		Subject:       leafCert.Subject.CommonName,
		Issuer:        leafCert.Issuer.CommonName,
		NotBefore:     leafCert.NotBefore,
		NotAfter:      leafCert.NotAfter,
		SignatureAlgo: signatureAlgo,
		PublicKeyAlgo: publicKeyAlgo,
		PublicKeyBits: publicKeyBits,
		SerialNumber:  leafCert.SerialNumber.String(),
		Fingerprint:   hex.EncodeToString(fingerprint[:]),
		SANs:          strings.Join(sans, ", "),
		DaysLeft:      daysLeft,
		Status:        status,
		Version:       leafCert.Version,
		LastCheckedAt: time.Now(),
	}

	if certChainInfo != nil {
		certRecord.CertChainComplete = certChainInfo.Complete
		certRecord.MissingCerts = strings.Join(certChainInfo.MissingCerts, "; ")
		certRecord.ChainLength = certChainInfo.ChainLength
		certRecord.RootCA = certChainInfo.RootCA
	}

	if ctLogResult != nil {
		certRecord.CTLogged = ctLogResult.Logged
		certRecord.CTLogCount = ctLogResult.LogCount
		ctLogsJSON, _ := json.Marshal(ctLogResult.Entries)
		certRecord.CTLogs = string(ctLogsJSON)
	}

	return certRecord, certChainInfo, ctLogResult, nil
}

func (s *SSLCertService) calculateStatus(daysLeft int) string {
	if daysLeft < 0 {
		return "expired"
	}
	if daysLeft <= config.Cfg.Cron.WarningDays {
		return "critical"
	}
	if daysLeft <= config.Cfg.Cron.CheckExpiredDays {
		return "warning"
	}
	return "valid"
}

func (s *SSLCertService) getSignatureAlgorithm(algo x509.SignatureAlgorithm) string {
	algoMap := map[x509.SignatureAlgorithm]string{
		x509.MD2WithRSA:      "MD2-RSA",
		x509.MD5WithRSA:      "MD5-RSA",
		x509.SHA1WithRSA:     "SHA1-RSA",
		x509.SHA256WithRSA:   "SHA256-RSA",
		x509.SHA384WithRSA:   "SHA384-RSA",
		x509.SHA512WithRSA:   "SHA512-RSA",
		x509.DSAWithSHA1:     "DSA-SHA1",
		x509.DSAWithSHA256:   "DSA-SHA256",
		x509.ECDSAWithSHA1:   "ECDSA-SHA1",
		x509.ECDSAWithSHA256: "ECDSA-SHA256",
		x509.ECDSAWithSHA384: "ECDSA-SHA384",
		x509.ECDSAWithSHA512: "ECDSA-SHA512",
	}
	if name, ok := algoMap[algo]; ok {
		return name
	}
	return fmt.Sprintf("Unknown(%d)", algo)
}

func (s *SSLCertService) getPublicKeyInfo(cert *x509.Certificate) (string, int) {
	switch pub := cert.PublicKey.(type) {
	case *rsa.PublicKey:
		return "RSA", pub.N.BitLen()
	case *ecdsa.PublicKey:
		curve := pub.Curve
		switch curve {
		case elliptic.P224():
			return "ECDSA (P-224)", 224
		case elliptic.P256():
			return "ECDSA (P-256)", 256
		case elliptic.P384():
			return "ECDSA (P-384)", 384
		case elliptic.P521():
			return "ECDSA (P-521)", 521
		default:
			return "ECDSA (Unknown)", 0
		}
	case *dsa.PublicKey:
		return "DSA", pub.P.BitLen()
	default:
		return "Unknown", 0
	}
}

func (s *SSLCertService) randomDelay() {
	if !config.Cfg.Scan.RandomizeDelay {
		return
	}

	minDelay := config.Cfg.Scan.MinDelayMs
	maxDelay := config.Cfg.Scan.MaxDelayMs

	if minDelay <= 0 {
		minDelay = 100
	}
	if maxDelay <= minDelay {
		maxDelay = minDelay + 100
	}

	jitter := 0
	if config.Cfg.Scan.JitterPercent > 0 {
		baseDelay := (minDelay + maxDelay) / 2
		jitterRange := baseDelay * config.Cfg.Scan.JitterPercent / 100
		if jitterRange > 0 {
			jitter = rand.Intn(jitterRange*2) - jitterRange
		}
	}

	delay := minDelay
	if maxDelay > minDelay {
		delay = minDelay + rand.Intn(maxDelay-minDelay)
	}
	delay += jitter

	if delay < 0 {
		delay = 0
	}

	config.Logger.Debug("随机延时", zap.Int("delay_ms", delay))
	time.Sleep(time.Duration(delay) * time.Millisecond)
}

func (s *SSLCertService) saveCertRecord(record *models.CertRecord) {
	db := storage.GetDB()
	var existing models.CertRecord
	err := db.Where("domain_id = ?", record.DomainID).Order("created_at DESC").First(&existing).Error

	if err == gorm.ErrRecordNotFound {
		db.Create(record)
	} else {
		existing.Subject = record.Subject
		existing.Issuer = record.Issuer
		existing.NotBefore = record.NotBefore
		existing.NotAfter = record.NotAfter
		existing.SignatureAlgo = record.SignatureAlgo
		existing.PublicKeyAlgo = record.PublicKeyAlgo
		existing.PublicKeyBits = record.PublicKeyBits
		existing.SerialNumber = record.SerialNumber
		existing.Fingerprint = record.Fingerprint
		existing.SANs = record.SANs
		existing.DaysLeft = record.DaysLeft
		existing.Status = record.Status
		existing.Version = record.Version
		existing.ErrorMsg = record.ErrorMsg
		existing.LastCheckedAt = record.LastCheckedAt
		existing.CertChainComplete = record.CertChainComplete
		existing.MissingCerts = record.MissingCerts
		existing.ChainLength = record.ChainLength
		existing.RootCA = record.RootCA
		existing.CTLogged = record.CTLogged
		existing.CTLogCount = record.CTLogCount
		existing.CTLogs = record.CTLogs
		db.Save(&existing)
	}
}

func (s *SSLCertService) GetLatestCertRecord(domainID uint) (*models.CertRecord, error) {
	db := storage.GetDB()
	var record models.CertRecord
	err := db.Where("domain_id = ?", domainID).Order("last_checked_at DESC").First(&record).Error
	if err != nil {
		return nil, err
	}
	return &record, nil
}

func (s *SSLCertService) GetAllLatestCertRecords() ([]models.CertRecord, error) {
	db := storage.GetDB()
	var records []models.CertRecord

	subQuery := db.Model(&models.CertRecord{}).
		Select("MAX(last_checked_at)").
		Where("domain_id = cert_records.domain_id").
		Table("cert_records")

	err := db.Preload("Domain").
		Where("last_checked_at = (?)", subQuery).
		Order("status DESC, days_left ASC").
		Find(&records).Error

	return records, err
}

func (s *SSLCertService) GenerateReport() (*models.ReportData, error) {
	db := storage.GetDB()
	var report models.ReportData

	db.Model(&models.Domain{}).Where("enabled = ?", true).Count(&report.TotalDomains)

	var records []models.CertRecord
	subQuery := db.Model(&models.CertRecord{}).
		Select("MAX(last_checked_at)").
		Where("domain_id = cert_records.domain_id").
		Table("cert_records")

	db.Where("last_checked_at = (?)", subQuery).Find(&records)

	for _, r := range records {
		switch r.Status {
		case "valid":
			report.ValidCerts++
		case "warning", "critical":
			report.ExpiringSoon++
		case "expired":
			report.Expired++
		case "error":
			report.FailedChecks++
		}
	}

	var latestRecord models.CertRecord
	db.Order("last_checked_at DESC").First(&latestRecord)
	report.LastScanTime = latestRecord.LastCheckedAt

	return &report, nil
}

func (s *SSLCertService) GetCertHistory(domainID uint, limit int) ([]models.CertRecord, error) {
	db := storage.GetDB()
	var records []models.CertRecord
	err := db.Where("domain_id = ?", domainID).
		Order("created_at DESC").
		Limit(limit).
		Find(&records).Error
	return records, err
}

func (s *SSLCertService) CheckAlgorithmStrength(algo string, bits int) models.AlgoStrengthResult {
	if s.ruleSvc != nil {
		return s.ruleSvc.CheckAlgorithmStrength(algo, bits)
	}
	return models.AlgoStrengthResult{
		Algorithm:   algo,
		Bits:        bits,
		Status:      "unknown",
		Description: "规则库未初始化",
		Score:       0,
	}
}

func (s *SSLCertService) GetScanConfig() map[string]interface{} {
	return map[string]interface{}{
		"max_concurrent":   config.Cfg.Scan.MaxConcurrent,
		"min_delay_ms":     config.Cfg.Scan.MinDelayMs,
		"max_delay_ms":     config.Cfg.Scan.MaxDelayMs,
		"timeout_seconds":  config.Cfg.Scan.TimeoutSeconds,
		"retry_count":      config.Cfg.Scan.RetryCount,
		"randomize_delay":  config.Cfg.Scan.RandomizeDelay,
		"jitter_percent":   config.Cfg.Scan.JitterPercent,
	}
}
