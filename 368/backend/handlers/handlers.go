package handlers

import (
	"encoding/csv"
	"io"
	"net/http"
	"strconv"
	"strings"
	"ssl-monitor/models"
	"ssl-monitor/services"
	"ssl-monitor/storage"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type DomainHandler struct {
	sslSvc          *services.SSLCertService
	alertSvc        *services.AlertService
	ruleSvc         *services.RuleLibraryService
	dnsSvc          *services.DNSService
	certAnalysisSvc *services.CertAnalysisService
}

func NewDomainHandler(sslSvc *services.SSLCertService, alertSvc *services.AlertService, ruleSvc *services.RuleLibraryService, dnsSvc *services.DNSService, certAnalysisSvc *services.CertAnalysisService) *DomainHandler {
	return &DomainHandler{
		sslSvc:          sslSvc,
		alertSvc:        alertSvc,
		ruleSvc:         ruleSvc,
		dnsSvc:          dnsSvc,
		certAnalysisSvc: certAnalysisSvc,
	}
}

type Response struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

func (h *DomainHandler) GetDomains(c *gin.Context) {
	db := storage.GetDB()
	var domains []models.Domain

	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("page_size", "20"))
	keyword := c.Query("keyword")
	tag := c.Query("tag")

	query := db.Model(&models.Domain{})
	if keyword != "" {
		query = query.Where("domain_name LIKE ? OR remark LIKE ?", "%"+keyword+"%", "%"+keyword+"%")
	}
	if tag != "" {
		query = query.Where("tag = ?", tag)
	}

	var total int64
	query.Count(&total)

	offset := (page - 1) * pageSize
	query.Offset(offset).Limit(pageSize).Order("created_at DESC").Find(&domains)

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data: gin.H{
			"total":     total,
			"page":      page,
			"page_size": pageSize,
			"domains":   domains,
		},
	})
}

func (h *DomainHandler) CreateDomain(c *gin.Context) {
	var domain models.Domain
	if err := c.ShouldBindJSON(&domain); err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: err.Error()})
		return
	}

	domain.DomainName = strings.TrimSpace(domain.DomainName)
	domain.DomainName = strings.TrimPrefix(domain.DomainName, "https://")
	domain.DomainName = strings.TrimPrefix(domain.DomainName, "http://")
	domain.DomainName = strings.Split(domain.DomainName, "/")[0]

	if domain.Port == 0 {
		domain.Port = 443
	}

	db := storage.GetDB()
	var existing models.Domain
	if err := db.Where("domain_name = ?", domain.DomainName).First(&existing).Error; err == nil {
		c.JSON(http.StatusConflict, Response{Code: 409, Message: "域名已存在"})
		return
	}

	if err := db.Create(&domain).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "创建失败: " + err.Error()})
		return
	}

	go h.sslSvc.CheckDomain(domain.DomainName, domain.Port)

	c.JSON(http.StatusCreated, Response{
		Code:    0,
		Message: "创建成功",
		Data:    domain,
	})
}

func (h *DomainHandler) UpdateDomain(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))

	db := storage.GetDB()
	var domain models.Domain
	if err := db.First(&domain, id).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{Code: 404, Message: "域名不存在"})
		return
	}

	var input map[string]interface{}
	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: err.Error()})
		return
	}

	if err := db.Model(&domain).Updates(input).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "更新失败"})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "更新成功",
		Data:    domain,
	})
}

func (h *DomainHandler) DeleteDomain(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))

	db := storage.GetDB()
	if err := db.Delete(&models.Domain{}, id).Error; err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "删除失败"})
		return
	}

	c.JSON(http.StatusOK, Response{Code: 0, Message: "删除成功"})
}

func (h *DomainHandler) ImportDomains(c *gin.Context) {
	file, header, err := c.Request.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: "请上传CSV文件"})
		return
	}
	defer file.Close()

	if !strings.HasSuffix(strings.ToLower(header.Filename), ".csv") {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: "只支持CSV格式文件"})
		return
	}

	reader := csv.NewReader(file)
	reader.FieldsPerRecord = -1

	var domains []models.Domain
	lineNum := 0

	for {
		lineNum++
		record, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}

		if lineNum == 1 && len(record) > 0 {
			firstField := strings.ToLower(strings.TrimSpace(record[0]))
			if firstField == "domain" || firstField == "域名" {
				continue
			}
		}

		if len(record) == 0 {
			continue
		}

		domainName := strings.TrimSpace(record[0])
		domainName = strings.TrimPrefix(domainName, "https://")
		domainName = strings.TrimPrefix(domainName, "http://")
		domainName = strings.Split(domainName, "/")[0]

		if domainName == "" {
			continue
		}

		port := 443
		if len(record) > 1 {
			if p, err := strconv.Atoi(strings.TrimSpace(record[1])); err == nil && p > 0 {
				port = p
			}
		}

		remark := ""
		if len(record) > 2 {
			remark = strings.TrimSpace(record[2])
		}

		tag := ""
		if len(record) > 3 {
			tag = strings.TrimSpace(record[3])
		}

		domains = append(domains, models.Domain{
			DomainName: domainName,
			Port:       port,
			Remark:     remark,
			Tag:        tag,
			Enabled:    true,
		})
	}

	db := storage.GetDB()
	var successCount, failCount int
	var failedDomains []string

	for _, d := range domains {
		var existing models.Domain
		if err := db.Where("domain_name = ?", d.DomainName).First(&existing).Error; err == nil {
			failCount++
			failedDomains = append(failedDomains, d.DomainName+" (已存在)")
			continue
		}

		if err := db.Create(&d).Error; err != nil {
			failCount++
			failedDomains = append(failedDomains, d.DomainName+" ("+err.Error()+")")
			continue
		}
		successCount++
	}

	go func() {
		for _, d := range domains {
			var existing models.Domain
			if err := db.Where("domain_name = ?", d.DomainName).First(&existing).Error; err == nil {
				h.sslSvc.CheckDomain(d.DomainName, d.Port)
			}
		}
	}()

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "导入完成",
		Data: gin.H{
			"success_count":   successCount,
			"fail_count":      failCount,
			"failed_domains":  failedDomains,
			"total_processed": len(domains),
		},
	})
}

func (h *DomainHandler) BatchCreateDomains(c *gin.Context) {
	var input struct {
		Domains []string `json:"domains" binding:"required"`
		Tag     string   `json:"tag"`
		Port    int      `json:"port"`
	}

	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: err.Error()})
		return
	}

	if input.Port == 0 {
		input.Port = 443
	}

	db := storage.GetDB()
	var successCount, failCount int
	var failedDomains []string

	for _, domainName := range input.Domains {
		domainName = strings.TrimSpace(domainName)
		domainName = strings.TrimPrefix(domainName, "https://")
		domainName = strings.TrimPrefix(domainName, "http://")
		domainName = strings.Split(domainName, "/")[0]

		if domainName == "" {
			continue
		}

		var existing models.Domain
		if err := db.Where("domain_name = ?", domainName).First(&existing).Error; err == nil {
			failCount++
			failedDomains = append(failedDomains, domainName+" (已存在)")
			continue
		}

		domain := models.Domain{
			DomainName: domainName,
			Port:       input.Port,
			Tag:        input.Tag,
			Enabled:    true,
		}

		if err := db.Create(&domain).Error; err != nil {
			failCount++
			failedDomains = append(failedDomains, domainName+" ("+err.Error()+")")
			continue
		}
		successCount++
	}

	go func() {
		for _, domainName := range input.Domains {
			domainName = strings.TrimSpace(domainName)
			domainName = strings.TrimPrefix(domainName, "https://")
			domainName = strings.TrimPrefix(domainName, "http://")
			domainName = strings.Split(domainName, "/")[0]
			if domainName != "" {
				h.sslSvc.CheckDomain(domainName, input.Port)
			}
		}
	}()

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "批量导入完成",
		Data: gin.H{
			"success_count":  successCount,
			"fail_count":     failCount,
			"failed_domains": failedDomains,
		},
	})
}

func (h *DomainHandler) CheckDomain(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))

	db := storage.GetDB()
	var domain models.Domain
	if err := db.First(&domain, id).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{Code: 404, Message: "域名不存在"})
		return
	}

	result := h.sslSvc.CheckDomain(domain.DomainName, domain.Port)
	if result.Error != nil {
		c.JSON(http.StatusOK, Response{
			Code:    0,
			Message: "检查完成(有错误)",
			Data:    result.CertRecord,
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "检查成功",
		Data:    result.CertRecord,
	})
}

func (h *DomainHandler) GetCertRecords(c *gin.Context) {
	db := storage.GetDB()
	var records []models.CertRecord

	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("page_size", "20"))
	status := c.Query("status")
	domainID := c.Query("domain_id")

	query := db.Model(&models.CertRecord{})
	if status != "" {
		query = query.Where("status = ?", status)
	}
	if domainID != "" {
		query = query.Where("domain_id = ?", domainID)
	}

	var total int64
	query.Count(&total)

	subQuery := db.Model(&models.CertRecord{}).
		Select("MAX(last_checked_at)").
		Where("domain_id = cert_records.domain_id").
		Table("cert_records")

	offset := (page - 1) * pageSize
	query.Where("last_checked_at = (?)", subQuery).
		Offset(offset).Limit(pageSize).
		Order("status DESC, days_left ASC").
		Find(&records)

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data: gin.H{
			"total":   total,
			"page":    page,
			"page_size": pageSize,
			"records": records,
		},
	})
}

func (h *DomainHandler) GetCertHistory(c *gin.Context) {
	domainID, _ := strconv.Atoi(c.Param("domain_id"))
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "30"))

	records, err := h.sslSvc.GetCertHistory(uint(domainID), limit)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "查询失败"})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data:    records,
	})
}

func (h *DomainHandler) GetReport(c *gin.Context) {
	report, err := h.sslSvc.GenerateReport()
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "生成报告失败"})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data:    report,
	})
}

func (h *DomainHandler) GetAlertLogs(c *gin.Context) {
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("page_size", "20"))

	logs, total, err := h.alertSvc.GetAlertLogs(page, pageSize)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "查询失败"})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data: gin.H{
			"total":   total,
			"page":    page,
			"page_size": pageSize,
			"logs":    logs,
		},
	})
}

func (h *DomainHandler) SendTestAlert(c *gin.Context) {
	var input struct {
		Domain string `json:"domain" binding:"required"`
	}

	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: err.Error()})
		return
	}

	if err := h.alertSvc.SendCustomAlert(input.Domain, "测试告警消息", "info"); err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: err.Error()})
		return
	}

	c.JSON(http.StatusOK, Response{Code: 0, Message: "测试告警已发送"})
}

func (h *DomainHandler) GetTags(c *gin.Context) {
	db := storage.GetDB()
	var tags []string

	db.Model(&models.Domain{}).
		Where("tag != ''").
		Distinct("tag").
		Pluck("tag", &tags)

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data:    tags,
	})
}

func (h *DomainHandler) ExportReport(c *gin.Context) {
	db := storage.GetDB()
	var records []models.CertRecord

	subQuery := db.Model(&models.CertRecord{}).
		Select("MAX(last_checked_at)").
		Where("domain_id = cert_records.domain_id").
		Table("cert_records")

	db.Where("last_checked_at = (?)", subQuery).
		Order("status DESC, days_left ASC").
		Find(&records)

	c.Header("Content-Type", "text/csv; charset=utf-8")
	c.Header("Content-Disposition", "attachment; filename=ssl_report.csv")

	c.Writer.Write([]byte("\xEF\xBB\xBF"))

	c.Writer.Write([]byte("域名,端口,主题,签发机构,有效期开始,有效期结束,剩余天数,状态,加密算法,密钥位数,签名算法,指纹,证书链完整,CT备案,CT日志数,缺失证书,根CA,错误信息,检查时间\n"))

	for _, r := range records {
		line := strings.Join([]string{
			r.Domain,
			strconv.Itoa(r.Port),
			r.Subject,
			r.Issuer,
			r.NotBefore.Format("2006-01-02 15:04:05"),
			r.NotAfter.Format("2006-01-02 15:04:05"),
			strconv.Itoa(r.DaysLeft),
			r.Status,
			r.PublicKeyAlgo,
			strconv.Itoa(r.PublicKeyBits),
			r.SignatureAlgo,
			r.Fingerprint,
			strconv.FormatBool(r.CertChainComplete),
			strconv.FormatBool(r.CTLogged),
			strconv.Itoa(r.CTLogCount),
			r.MissingCerts,
			r.RootCA,
			r.ErrorMsg,
			r.LastCheckedAt.Format("2006-01-02 15:04:05"),
		}, ",")
		c.Writer.Write([]byte(line + "\n"))
	}
}

func (h *DomainHandler) GetDomainWithCert(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))

	db := storage.GetDB()
	var domain models.Domain
	if err := db.First(&domain, id).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{Code: 404, Message: "域名不存在"})
		return
	}

	record, err := h.sslSvc.GetLatestCertRecord(uint(id))
	if err != nil && err != gorm.ErrRecordNotFound {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "查询失败"})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data: gin.H{
			"domain": domain,
			"cert":   record,
		},
	})
}

func (h *DomainHandler) ToggleDomain(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))

	db := storage.GetDB()
	var domain models.Domain
	if err := db.First(&domain, id).Error; err != nil {
		c.JSON(http.StatusNotFound, Response{Code: 404, Message: "域名不存在"})
		return
	}

	domain.Enabled = !domain.Enabled
	db.Save(&domain)

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "更新成功",
		Data:    domain,
	})
}

func (h *DomainHandler) GetDashboard(c *gin.Context) {
	db := storage.GetDB()

	var totalDomains int64
	var validCerts, warningCerts, criticalCerts, expiredCerts, errorCerts int64

	db.Model(&models.Domain{}).Where("enabled = ?", true).Count(&totalDomains)

	subQuery := db.Model(&models.CertRecord{}).
		Select("MAX(last_checked_at)").
		Where("domain_id = cert_records.domain_id").
		Table("cert_records")

	var records []models.CertRecord
	db.Where("last_checked_at = (?)", subQuery).Find(&records)

	for _, r := range records {
		switch r.Status {
		case "valid":
			validCerts++
		case "warning":
			warningCerts++
		case "critical":
			criticalCerts++
		case "expired":
			expiredCerts++
		case "error":
			errorCerts++
		}
	}

	var recentAlerts []models.AlertLog
	db.Order("created_at DESC").Limit(10).Find(&recentAlerts)

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data: gin.H{
			"total_domains":   totalDomains,
			"valid_certs":     validCerts,
			"warning_certs":   warningCerts,
			"critical_certs":  criticalCerts,
			"expired_certs":   expiredCerts,
			"error_certs":     errorCerts,
			"recent_alerts":   recentAlerts,
		},
	})
}

func (h *DomainHandler) GetDNSRecords(c *gin.Context) {
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("page_size", "20"))
	domain := c.Query("domain")

	records, total, err := h.dnsSvc.GetDNSRecords(domain, page, pageSize)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "查询失败: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data: gin.H{
			"total":   total,
			"page":    page,
			"page_size": pageSize,
			"records": records,
		},
	})
}

func (h *DomainHandler) GetSubdomains(c *gin.Context) {
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("page_size", "20"))
	parentDomain := c.Query("parent_domain")

	records, total, err := h.dnsSvc.GetSubdomainRecords(parentDomain, page, pageSize)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "查询失败: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data: gin.H{
			"total":   total,
			"page":    page,
			"page_size": pageSize,
			"records": records,
		},
	})
}

func (h *DomainHandler) ScanDNS(c *gin.Context) {
	var input struct {
		Domain string `json:"domain"`
	}

	if err := c.ShouldBindJSON(&input); err == nil && input.Domain != "" {
		go func() {
			h.dnsSvc.ScanDomain(input.Domain)
		}()
	} else {
		go h.dnsSvc.ScanAllDomains()
	}

	c.JSON(http.StatusOK, Response{Code: 0, Message: "DNS扫描已启动"})
}

func (h *DomainHandler) PromoteSubdomain(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))

	domain, err := h.dnsSvc.PromoteSubdomain(uint(id))
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "提升失败: " + err.Error()})
		return
	}

	go h.sslSvc.CheckDomain(domain.DomainName, domain.Port)

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "提升成功，已开始监控",
		Data:    domain,
	})
}

func (h *DomainHandler) DeleteSubdomainRecord(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))

	if err := h.dnsSvc.DeleteSubdomainRecord(uint(id)); err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "删除失败: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, Response{Code: 0, Message: "删除成功"})
}

func (h *DomainHandler) GetDNSStats(c *gin.Context) {
	stats, err := h.dnsSvc.GetDNSStats()
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "查询失败: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data:    stats,
	})
}

func (h *DomainHandler) GetRules(c *gin.Context) {
	ruleType := c.Query("type")

	var rules []models.AlgorithmRule
	var err error

	if ruleType != "" {
		rules, err = h.ruleSvc.GetRulesByType(ruleType)
	} else {
		rules, err = h.ruleSvc.GetAllRules()
	}

	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "查询失败: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data:    rules,
	})
}

func (h *DomainHandler) UpdateRules(c *gin.Context) {
	log, err := h.ruleSvc.UpdateRules()
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: "更新失败: " + err.Error(),
			Data:    log,
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "更新成功",
		Data:    log,
	})
}

func (h *DomainHandler) GetRuleUpdateLogs(c *gin.Context) {
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("page_size", "20"))

	logs, total, err := h.ruleSvc.GetUpdateLogs(page, pageSize)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "查询失败: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data: gin.H{
			"total":   total,
			"page":    page,
			"page_size": pageSize,
			"logs":    logs,
		},
	})
}

func (h *DomainHandler) AddRule(c *gin.Context) {
	var rule models.AlgorithmRule
	if err := c.ShouldBindJSON(&rule); err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: err.Error()})
		return
	}

	if err := h.ruleSvc.AddCustomRule(rule); err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "添加失败: " + err.Error()})
		return
	}

	c.JSON(http.StatusCreated, Response{
		Code:    0,
		Message: "添加成功",
		Data:    rule,
	})
}

func (h *DomainHandler) UpdateRule(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))

	var updates map[string]interface{}
	if err := c.ShouldBindJSON(&updates); err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: err.Error()})
		return
	}

	if err := h.ruleSvc.UpdateCustomRule(uint(id), updates); err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "更新失败: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, Response{Code: 0, Message: "更新成功"})
}

func (h *DomainHandler) DeleteRule(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))

	if err := h.ruleSvc.DeleteCustomRule(uint(id)); err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "删除失败: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, Response{Code: 0, Message: "删除成功"})
}

func (h *DomainHandler) GetRuleVersion(c *gin.Context) {
	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data: gin.H{
			"version": h.ruleSvc.GetVersion(),
		},
	})
}

func (h *DomainHandler) ExportRules(c *gin.Context) {
	data, err := h.ruleSvc.ExportRules()
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "导出失败: " + err.Error()})
		return
	}

	c.Header("Content-Type", "application/json; charset=utf-8")
	c.Header("Content-Disposition", "attachment; filename=algorithm_rules.json")
	c.Writer.Write(data)
}

func (h *DomainHandler) ImportRules(c *gin.Context) {
	file, _, err := c.Request.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: "请上传JSON文件"})
		return
	}
	defer file.Close()

	data, err := io.ReadAll(file)
	if err != nil {
		c.JSON(http.StatusBadRequest, Response{Code: 400, Message: "读取文件失败"})
		return
	}

	count, err := h.ruleSvc.ImportRules(data)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "导入失败: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "导入成功",
		Data: gin.H{
			"count": count,
		},
	})
}

func (h *DomainHandler) GetScanConfig(c *gin.Context) {
	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data:    h.sslSvc.GetScanConfig(),
	})
}

func (h *DomainHandler) GetCertChainInfo(c *gin.Context) {
	domainID, _ := strconv.Atoi(c.Param("domain_id"))

	db := storage.GetDB()
	var record models.CertRecord
	err := db.Where("domain_id = ?", domainID).
		Order("last_checked_at DESC").
		First(&record).Error

	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: "查询失败"})
		return
	}

	chainInfo := &models.CertChainInfo{
		Complete:     record.CertChainComplete,
		ChainLength:  record.ChainLength,
		RootCA:       record.RootCA,
		MissingCerts: strings.Split(record.MissingCerts, "; "),
	}

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data:    chainInfo,
	})
}

func (h *DomainHandler) CompareCertWithPrevious(c *gin.Context) {
	domainID, _ := strconv.Atoi(c.Param("domain_id"))

	result, err := h.certAnalysisSvc.CompareWithPrevious(uint(domainID))
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: err.Error()})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data:    result,
	})
}

func (h *DomainHandler) GetCertChanges(c *gin.Context) {
	domainID, _ := strconv.Atoi(c.Param("domain_id"))
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "10"))

	results, err := h.certAnalysisSvc.GetAllCertChanges(uint(domainID), limit)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: err.Error()})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data:    results,
	})
}

func (h *DomainHandler) GetUnloggedCerts(c *gin.Context) {
	records, err := h.certAnalysisSvc.GetUnloggedCerts()
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: err.Error()})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data: gin.H{
			"count":   len(records),
			"records": records,
		},
	})
}

func (h *DomainHandler) GetIncompleteChainCerts(c *gin.Context) {
	records, err := h.certAnalysisSvc.GetIncompleteChainCerts()
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{Code: 500, Message: err.Error()})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "success",
		Data: gin.H{
			"count":   len(records),
			"records": records,
		},
	})
}
