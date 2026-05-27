package services

import (
	"context"
	"fmt"
	"math/rand"
	"net"
	"regexp"
	"ssl-monitor/config"
	"ssl-monitor/models"
	"ssl-monitor/storage"
	"strings"
	"time"

	"go.uber.org/zap"
	"gorm.io/gorm"
)

type DNSService struct {
	resolver *net.Resolver
}

func NewDNSService() *DNSService {
	dnsServers := config.Cfg.DNS.DNSServers
	if len(dnsServers) == 0 {
		dnsServers = []string{"8.8.8.8:53", "1.1.1.1:53"}
	}

	resolver := &net.Resolver{
		PreferGo: true,
		Dial: func(ctx context.Context, network, address string) (net.Conn, error) {
			server := dnsServers[rand.Intn(len(dnsServers))]
			d := net.Dialer{
				Timeout: time.Duration(config.Cfg.DNS.TimeoutSeconds) * time.Second,
			}
			return d.DialContext(ctx, network, server)
		},
	}

	return &DNSService{
		resolver: resolver,
	}
}

type DNSResult struct {
	Domain     string
	RecordType string
	Records    []*models.DNSRecord
	Error      error
}

func (s *DNSService) ScanDomain(domainName string) (*DNSResult, error) {
	result := &DNSResult{
		Domain: domainName,
	}

	var mxRecords []*models.DNSRecord
	var cnameRecords []*models.DNSRecord
	var aRecords []*models.DNSRecord
	var subdomainRecords []*models.SubdomainRecord

	if config.Cfg.DNS.AutoDiscoverMX {
		mx, err := s.LookupMX(domainName)
		if err != nil {
			config.Logger.Debug("MX记录查询失败", zap.String("domain", domainName), zap.Error(err))
		} else {
			mxRecords = append(mxRecords, mx...)
		}
	}

	if config.Cfg.DNS.AutoDiscoverSubdomains {
		cname, a, err := s.LookupCommonSubdomains(domainName)
		if err != nil {
			config.Logger.Debug("子域名查询失败", zap.String("domain", domainName), zap.Error(err))
		} else {
			cnameRecords = append(cnameRecords, cname...)
			aRecords = append(aRecords, a...)
		}
	}

	result.Records = append(result.Records, mxRecords...)
	result.Records = append(result.Records, cnameRecords...)
	result.Records = append(result.Records, aRecords...)

	subdomainRecords = s.extractSubdomains(domainName, result.Records)

	s.saveDNSRecords(result.Records)
	s.saveSubdomainRecords(subdomainRecords)

	return result, nil
}

func (s *DNSService) LookupMX(domainName string) ([]*models.DNSRecord, error) {
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(config.Cfg.DNS.TimeoutSeconds)*time.Second)
	defer cancel()

	mxRecords, err := s.resolver.LookupMX(ctx, domainName)
	if err != nil {
		return nil, err
	}

	var records []*models.DNSRecord
	scannedAt := time.Now()

	for _, mx := range mxRecords {
		host := strings.TrimSuffix(mx.Host, ".")
		records = append(records, &models.DNSRecord{
			Domain:     domainName,
			RecordType: "MX",
			Value:      host,
			Priority:   int(mx.Pref),
			Server:     s.getCurrentDNSServer(),
			ScannedAt:  scannedAt,
		})

		subdomain := strings.TrimSuffix(mx.Host, ".")
		if subdomain != domainName && strings.HasSuffix(subdomain, domainName) {
			s.checkAndAddSubdomain(domainName, subdomain, "MX", host)
		}
	}

	return records, nil
}

func (s *DNSService) LookupCommonSubdomains(domainName string) ([]*models.DNSRecord, []*models.DNSRecord, error) {
	commonPrefixes := []string{
		"www", "mail", "smtp", "pop", "pop3", "imap", "ftp", "ssh",
		"blog", "shop", "store", "api", "app", "dev", "test", "staging",
		"admin", "panel", "cpanel", "webmail", "ssl", "secure", "vpn",
		"remote", "portal", "login", "auth", "sso", "oauth",
		"cdn", "static", "assets", "img", "images", "media",
		"m", "mobile", "wap", "api", "graphql", "rest",
		"status", "health", "metrics", "monitor",
		"docs", "help", "support", "kb",
		"ns1", "ns2", "ns3", "dns1", "dns2",
	}

	var cnameRecords []*models.DNSRecord
	var aRecords []*models.DNSRecord
	scannedAt := time.Now()

	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(config.Cfg.DNS.TimeoutSeconds)*time.Second)
	defer cancel()

	for _, prefix := range commonPrefixes {
		subdomain := fmt.Sprintf("%s.%s", prefix, domainName)

		cname, err := s.resolver.LookupCNAME(ctx, subdomain)
		if err == nil {
			cname = strings.TrimSuffix(cname, ".")
			cnameRecords = append(cnameRecords, &models.DNSRecord{
				Domain:     subdomain,
				RecordType: "CNAME",
				Value:      cname,
				Server:     s.getCurrentDNSServer(),
				ScannedAt:  scannedAt,
			})

			s.checkAndAddSubdomain(domainName, subdomain, "CNAME", cname)

			targetDomain := s.extractDomainFromHost(cname)
			if targetDomain != "" && targetDomain != domainName && strings.HasSuffix(targetDomain, domainName) {
				s.checkAndAddSubdomain(domainName, targetDomain, "CNAME-target", cname)
			}
		}

		addrs, err := s.resolver.LookupHost(ctx, subdomain)
		if err == nil {
			for _, addr := range addrs {
				aRecords = append(aRecords, &models.DNSRecord{
					Domain:     subdomain,
					RecordType: "A",
					Value:      addr,
					Server:     s.getCurrentDNSServer(),
					ScannedAt:  scannedAt,
				})

				s.checkAndAddSubdomain(domainName, subdomain, "A", addr)
			}
		}

		time.Sleep(10 * time.Millisecond)
	}

	return cnameRecords, aRecords, nil
}

func (s *DNSService) extractSubdomains(parentDomain string, records []*models.DNSRecord) []*models.SubdomainRecord {
	var subdomains []*models.SubdomainRecord
	seen := make(map[string]bool)

	for _, record := range records {
		subdomain := record.Domain

		if subdomain == parentDomain || seen[subdomain] {
			continue
		}

		if !strings.HasSuffix(subdomain, "."+parentDomain) && subdomain != parentDomain {
			continue
		}

		seen[subdomain] = true

		subdomains = append(subdomains, &models.SubdomainRecord{
			ParentDomain: parentDomain,
			Subdomain:    subdomain,
			Source:       record.Server,
			RecordType:   record.RecordType,
			RecordValue:  record.Value,
			DiscoveredAt: time.Now(),
		})
	}

	return subdomains
}

func (s *DNSService) checkAndAddSubdomain(parentDomain, subdomain, recordType, recordValue string) {
	if !config.Cfg.DNS.AutoDiscoverSubdomains {
		return
	}

	subdomain = strings.TrimSuffix(subdomain, ".")

	if !strings.HasSuffix(subdomain, parentDomain) || subdomain == parentDomain {
		return
	}

	db := storage.GetDB()
	var existing models.SubdomainRecord
	if err := db.Where("subdomain = ?", subdomain).First(&existing).Error; err == nil {
		return
	}

	var existingDomain models.Domain
	if err := db.Where("domain_name = ?", subdomain).First(&existingDomain).Error; err == nil {
		monitored := true
		db.Model(&existing).Update("monitored", monitored)
		return
	}

	record := &models.SubdomainRecord{
		ParentDomain: parentDomain,
		Subdomain:    subdomain,
		Source:       "DNS",
		RecordType:   recordType,
		RecordValue:  recordValue,
		AutoAdded:    false,
		Monitored:    false,
		DiscoveredAt: time.Now(),
	}

	db.Create(record)

	if config.Cfg.DNS.AutoAddSubdomains {
		domain := &models.Domain{
			DomainName: subdomain,
			Port:       443,
			Tag:        config.Cfg.DNS.SubdomainTags,
			Remark:     fmt.Sprintf("自动发现自: %s (%s)", parentDomain, recordType),
			Enabled:    true,
		}

		if err := db.Where("domain_name = ?", subdomain).FirstOrCreate(domain).Error; err == nil {
			record.Monitored = true
			record.AutoAdded = true
			db.Save(record)
			config.Logger.Info("自动添加子域名监控",
				zap.String("parent", parentDomain),
				zap.String("subdomain", subdomain))
		}
	}
}

func (s *DNSService) saveDNSRecords(records []*models.DNSRecord) {
	if len(records) == 0 {
		return
	}

	db := storage.GetDB()
	for _, record := range records {
		db.Create(record)
	}
}

func (s *DNSService) saveSubdomainRecords(records []*models.SubdomainRecord) {
	if len(records) == 0 {
		return
	}

	db := storage.GetDB()
	for _, record := range records {
		var existing models.SubdomainRecord
		if err := db.Where("subdomain = ?", record.Subdomain).First(&existing).Error; err == gorm.ErrRecordNotFound {
			db.Create(record)
		}
	}
}

func (s *DNSService) extractDomainFromHost(host string) string {
	host = strings.TrimSuffix(host, ".")

	if net.ParseIP(host) != nil {
		return ""
	}

	parts := strings.Split(host, ".")
	if len(parts) >= 2 {
		return strings.Join(parts[len(parts)-2:], ".")
	}

	return host
}

func (s *DNSService) getCurrentDNSServer() string {
	servers := config.Cfg.DNS.DNSServers
	if len(servers) > 0 {
		return servers[rand.Intn(len(servers))]
	}
	return "default"
}

func (s *DNSService) GetDNSRecords(domain string, page, pageSize int) ([]models.DNSRecord, int64, error) {
	db := storage.GetDB()
	var records []models.DNSRecord
	var total int64

	query := db.Model(&models.DNSRecord{})
	if domain != "" {
		query = query.Where("domain = ?", domain)
	}

	query.Count(&total)

	offset := (page - 1) * pageSize
	err := query.Order("scanned_at DESC, record_type").
		Offset(offset).Limit(pageSize).
		Find(&records).Error

	return records, total, err
}

func (s *DNSService) GetSubdomainRecords(parentDomain string, page, pageSize int) ([]models.SubdomainRecord, int64, error) {
	db := storage.GetDB()
	var records []models.SubdomainRecord
	var total int64

	query := db.Model(&models.SubdomainRecord{})
	if parentDomain != "" {
		query = query.Where("parent_domain = ?", parentDomain)
	}

	query.Count(&total)

	offset := (page - 1) * pageSize
	err := query.Order("discovered_at DESC, subdomain").
		Offset(offset).Limit(pageSize).
		Find(&records).Error

	return records, total, err
}

func (s *DNSService) PromoteSubdomain(id uint) (*models.Domain, error) {
	db := storage.GetDB()
	var subdomain models.SubdomainRecord
	if err := db.First(&subdomain, id).Error; err != nil {
		return nil, err
	}

	var existingDomain models.Domain
	if err := db.Where("domain_name = ?", subdomain.Subdomain).First(&existingDomain).Error; err == nil {
		subdomain.Monitored = true
		db.Save(&subdomain)
		return &existingDomain, nil
	}

	domain := &models.Domain{
		DomainName: subdomain.Subdomain,
		Port:       443,
		Tag:        config.Cfg.DNS.SubdomainTags,
		Remark:     fmt.Sprintf("从DNS发现提升: %s (%s)", subdomain.ParentDomain, subdomain.RecordType),
		Enabled:    true,
	}

	if err := db.Create(domain).Error; err != nil {
		return nil, err
	}

	subdomain.Monitored = true
	db.Save(&subdomain)

	config.Logger.Info("子域名提升为监控域名",
		zap.String("subdomain", subdomain.Subdomain),
		zap.String("parent", subdomain.ParentDomain))

	return domain, nil
}

func (s *DNSService) DiscoverSubdomainsFromCert(domainName string, sans string) {
	if sans == "" {
		return
	}

	sanList := strings.Split(sans, ", ")
	for _, san := range sanList {
		san = strings.TrimSpace(san)
		san = s.extractDomainFromHost(san)

		if san == "" || san == domainName {
			continue
		}

		if strings.HasSuffix(san, domainName) || strings.HasSuffix(domainName, san) {
			parent := domainName
			if len(san) > len(domainName) {
				s.checkAndAddSubdomain(parent, san, "SAN", san)
			}
		}
	}
}

func (s *DNSService) ScanAllDomains() {
	db := storage.GetDB()
	var domains []models.Domain
	if err := db.Where("enabled = ?", true).Find(&domains).Error; err != nil {
		config.Logger.Error("查询域名列表失败", zap.Error(err))
		return
	}

	config.Logger.Info("开始DNS扫描", zap.Int("count", len(domains)))

	for _, domain := range domains {
		s.randomDelay()
		config.Logger.Debug("扫描DNS记录", zap.String("domain", domain.DomainName))

		_, err := s.ScanDomain(domain.DomainName)
		if err != nil {
			config.Logger.Debug("DNS扫描失败",
				zap.String("domain", domain.DomainName),
				zap.Error(err))
		}
	}

	config.Logger.Info("DNS扫描完成")
}

func (s *DNSService) randomDelay() {
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
		jitter = rand.Intn(jitterRange*2) - jitterRange
	}

	delay := minDelay + rand.Intn(maxDelay-minDelay) + jitter
	if delay < 0 {
		delay = 0
	}

	time.Sleep(time.Duration(delay) * time.Millisecond)
}

func (s *DNSService) DeleteSubdomainRecord(id uint) error {
	db := storage.GetDB()
	return db.Delete(&models.SubdomainRecord{}, id).Error
}

func (s *DNSService) DeleteDNSRecord(id uint) error {
	db := storage.GetDB()
	return db.Delete(&models.DNSRecord{}, id).Error
}

func (s *DNSService) GetDNSStats() (map[string]interface{}, error) {
	db := storage.GetDB()

	var totalRecords int64
	db.Model(&models.DNSRecord{}).Count(&totalRecords)

	var totalSubdomains int64
	db.Model(&models.SubdomainRecord{}).Count(&totalSubdomains)

	var monitoredSubdomains int64
	db.Model(&models.SubdomainRecord{}).Where("monitored = ?", true).Count(&monitoredSubdomains)

	var autoAdded int64
	db.Model(&models.SubdomainRecord{}).Where("auto_added = ?", true).Count(&autoAdded)

	var recordTypes []struct {
		RecordType string `json:"record_type"`
		Count      int64  `json:"count"`
	}
	db.Model(&models.DNSRecord{}).Select("record_type, COUNT(*) as count").Group("record_type").Scan(&recordTypes)

	return map[string]interface{}{
		"total_records":     totalRecords,
		"total_subdomains":  totalSubdomains,
		"monitored":         monitoredSubdomains,
		"auto_added":        autoAdded,
		"record_types":      recordTypes,
	}, nil
}

func isValidDomain(domain string) bool {
	domainRegex := regexp.MustCompile(`^(?i)[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*$`)
	return domainRegex.MatchString(domain)
}
