package services

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"ssl-monitor/config"
	"ssl-monitor/models"
	"ssl-monitor/storage"
	"strings"
	"time"

	"go.uber.org/zap"
	"gopkg.in/gomail.v2"
)

type AlertService struct{}

func NewAlertService() *AlertService {
	return &AlertService{}
}

type DingTalkMessage struct {
	MsgType string               `json:"msgtype"`
	Text    *DingTalkTextContent `json:"text,omitempty"`
	Markdown *DingTalkMarkdownContent `json:"markdown,omitempty"`
}

type DingTalkTextContent struct {
	Content string `json:"content"`
}

type DingTalkMarkdownContent struct {
	Title string `json:"title"`
	Text  string `json:"text"`
}

type WeComMessage struct {
	MsgType string            `json:"msgtype"`
	Text    *WeComTextContent `json:"text,omitempty"`
	Markdown *WeComMarkdownContent `json:"markdown,omitempty"`
}

type WeComTextContent struct {
	Content string `json:"content"`
}

type WeComMarkdownContent struct {
	Content string `json:"content"`
}

func (s *AlertService) SendAlertsForResults(results []*CertResult) {
	for _, result := range results {
		if result.CertRecord == nil {
			continue
		}

		record := result.CertRecord
		if record.Status == "warning" || record.Status == "critical" || record.Status == "expired" || record.Status == "error" {
			s.sendAlert(record)
		}
	}
}

func (s *AlertService) sendAlert(record *models.CertRecord) {
	if config.Cfg.Alert.DingTalk.Enabled {
		go s.sendDingTalkAlert(record)
	}
	if config.Cfg.Alert.Email.Enabled {
		go s.sendEmailAlert(record)
	}
	if config.Cfg.Alert.WeCom.Enabled {
		go s.sendWeComAlert(record)
	}

	s.saveAlertLog(record)
}

func (s *AlertService) sendDingTalkAlert(record *models.CertRecord) {
	webhook := config.Cfg.Alert.DingTalk.Webhook
	secret := config.Cfg.Alert.DingTalk.Secret

	timestamp := fmt.Sprintf("%d", time.Now().UnixMilli())
	sign := s.generateDingTalkSign(timestamp, secret)

	fullURL := fmt.Sprintf("%s&timestamp=%s&sign=%s", webhook, timestamp, sign)

	level := s.getAlertLevel(record.Status)
	title := fmt.Sprintf("【SSL证书%s告警】", s.getAlertLevelText(level))

	content := fmt.Sprintf("## %s\n\n", title)
	content += fmt.Sprintf("**域名**: %s\n\n", record.Domain)
	content += fmt.Sprintf("**端口**: %d\n\n", record.Port)
	content += fmt.Sprintf("**签发机构**: %s\n\n", record.Issuer)
	content += fmt.Sprintf("**有效期至**: %s\n\n", record.NotAfter.Format("2006-01-02 15:04:05"))
	content += fmt.Sprintf("**剩余天数**: %d天\n\n", record.DaysLeft)
	content += fmt.Sprintf("**加密算法**: %s (%d位)\n\n", record.PublicKeyAlgo, record.PublicKeyBits)
	content += fmt.Sprintf("**签名算法**: %s\n\n", record.SignatureAlgo)
	content += fmt.Sprintf("**告警级别**: %s\n\n", s.getAlertLevelText(level))
	content += fmt.Sprintf("**检查时间**: %s\n", time.Now().Format("2006-01-02 15:04:05"))

	if record.ErrorMsg != "" {
		content += fmt.Sprintf("**错误信息**: %s\n", record.ErrorMsg)
	}

	msg := DingTalkMessage{
		MsgType: "markdown",
		Markdown: &DingTalkMarkdownContent{
			Title: title,
			Text:  content,
		},
	}

	body, _ := json.Marshal(msg)

	resp, err := http.Post(fullURL, "application/json", bytes.NewReader(body))
	if err != nil {
		config.Logger.Error("发送钉钉告警失败", zap.Error(err))
		return
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	config.Logger.Info("钉钉告警发送完成", zap.String("response", string(respBody)))
}

func (s *AlertService) sendEmailAlert(record *models.CertRecord) {
	emailConfig := config.Cfg.Alert.Email

	level := s.getAlertLevel(record.Status)
	subject := fmt.Sprintf("【SSL证书%s告警】%s", s.getAlertLevelText(level), record.Domain)

	body := fmt.Sprintf(`
		<h2>SSL证书告警通知</h2>
		<table border="1" cellpadding="8" cellspacing="0">
			<tr><td><strong>域名</strong></td><td>%s</td></tr>
			<tr><td><strong>端口</strong></td><td>%d</td></tr>
			<tr><td><strong>签发机构</strong></td><td>%s</td></tr>
			<tr><td><strong>证书主题</strong></td><td>%s</td></tr>
			<tr><td><strong>有效期开始</strong></td><td>%s</td></tr>
			<tr><td><strong>有效期至</strong></td><td>%s</td></tr>
			<tr><td><strong>剩余天数</strong></td><td>%d天</td></tr>
			<tr><td><strong>加密算法</strong></td><td>%s (%d位)</td></tr>
			<tr><td><strong>签名算法</strong></td><td>%s</td></tr>
			<tr><td><strong>告警级别</strong></td><td>%s</td></tr>
			<tr><td><strong>检查时间</strong></td><td>%s</td></tr>
		</table>
	`, record.Domain, record.Port, record.Issuer, record.Subject,
		record.NotBefore.Format("2006-01-02 15:04:05"),
		record.NotAfter.Format("2006-01-02 15:04:05"),
		record.DaysLeft, record.PublicKeyAlgo, record.PublicKeyBits,
		record.SignatureAlgo, s.getAlertLevelText(level),
		time.Now().Format("2006-01-02 15:04:05"))

	if record.ErrorMsg != "" {
		body += fmt.Sprintf("<p><strong>错误信息:</strong> %s</p>", record.ErrorMsg)
	}

	m := gomail.NewMessage()
	m.SetHeader("From", emailConfig.From)
	m.SetHeader("To", emailConfig.To)
	m.SetHeader("Subject", subject)
	m.SetBody("text/html", body)

	d := gomail.NewDialer(emailConfig.Host, emailConfig.Port, emailConfig.Username, emailConfig.Password)

	if err := d.DialAndSend(m); err != nil {
		config.Logger.Error("发送邮件告警失败", zap.Error(err))
		return
	}

	config.Logger.Info("邮件告警发送完成", zap.String("domain", record.Domain))
}

func (s *AlertService) sendWeComAlert(record *models.CertRecord) {
	webhook := config.Cfg.Alert.WeCom.Webhook

	level := s.getAlertLevel(record.Status)
	title := fmt.Sprintf("【SSL证书%s告警】", s.getAlertLevelText(level))

	content := fmt.Sprintf("## %s\n\n", title)
	content += fmt.Sprintf("**域名**: <font color=\"info\">%s</font>\n", record.Domain)
	content += fmt.Sprintf("**端口**: %d\n", record.Port)
	content += fmt.Sprintf("**签发机构**: %s\n", record.Issuer)
	content += fmt.Sprintf("**有效期至**: %s\n", record.NotAfter.Format("2006-01-02 15:04:05"))
	content += fmt.Sprintf("**剩余天数**: <font color=\"warning\">%d天</font>\n", record.DaysLeft)
	content += fmt.Sprintf("**加密算法**: %s (%d位)\n", record.PublicKeyAlgo, record.PublicKeyBits)
	content += fmt.Sprintf("**签名算法**: %s\n", record.SignatureAlgo)
	content += fmt.Sprintf("**告警级别**: <font color=\"comment\">%s</font>\n", s.getAlertLevelText(level))
	content += fmt.Sprintf("**检查时间**: %s\n", time.Now().Format("2006-01-02 15:04:05"))

	if record.ErrorMsg != "" {
		content += fmt.Sprintf("**错误信息**: %s\n", record.ErrorMsg)
	}

	msg := WeComMessage{
		MsgType: "markdown",
		Markdown: &WeComMarkdownContent{
			Content: content,
		},
	}

	body, _ := json.Marshal(msg)

	resp, err := http.Post(webhook, "application/json", bytes.NewReader(body))
	if err != nil {
		config.Logger.Error("发送企微告警失败", zap.Error(err))
		return
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	config.Logger.Info("企微告警发送完成", zap.String("response", string(respBody)))
}

func (s *AlertService) generateDingTalkSign(timestamp string, secret string) string {
	stringToSign := fmt.Sprintf("%s\n%s", timestamp, secret)
	h := hmac.New(sha256.New, []byte(secret))
	h.Write([]byte(stringToSign))
	sign := base64.StdEncoding.EncodeToString(h.Sum(nil))
	return url.QueryEscape(sign)
}

func (s *AlertService) getAlertLevel(status string) string {
	switch status {
	case "expired":
		return "critical"
	case "critical":
		return "critical"
	case "warning":
		return "warning"
	case "error":
		return "error"
	default:
		return "info"
	}
}

func (s *AlertService) getAlertLevelText(level string) string {
	levelMap := map[string]string{
		"critical": "严重",
		"warning":  "警告",
		"error":    "错误",
		"info":     "信息",
	}
	if text, ok := levelMap[level]; ok {
		return text
	}
	return "未知"
}

func (s *AlertService) saveAlertLog(record *models.CertRecord) {
	db := storage.GetDB()
	level := s.getAlertLevel(record.Status)

	alertLog := &models.AlertLog{
		DomainID:  record.DomainID,
		Domain:    record.Domain,
		AlertType: s.determineAlertType(record),
		Level:     level,
		Content:   s.buildAlertContent(record),
		Sent:      true,
		SentAt:    timePtr(time.Now()),
	}

	db.Create(alertLog)
}

func (s *AlertService) determineAlertType(record *models.CertRecord) string {
	types := []string{}
	if config.Cfg.Alert.DingTalk.Enabled {
		types = append(types, "DingTalk")
	}
	if config.Cfg.Alert.Email.Enabled {
		types = append(types, "Email")
	}
	if config.Cfg.Alert.WeCom.Enabled {
		types = append(types, "WeCom")
	}
	if len(types) == 0 {
		return "None"
	}
	return strings.Join(types, ", ")
}

func (s *AlertService) buildAlertContent(record *models.CertRecord) string {
	return fmt.Sprintf("SSL证书告警: 域名=%s, 剩余天数=%d, 状态=%s, 签发机构=%s",
		record.Domain, record.DaysLeft, record.Status, record.Issuer)
}

func (s *AlertService) SendCustomAlert(domain string, message string, level string) error {
	db := storage.GetDB()

	var domainModel models.Domain
	if err := db.Where("domain_name = ?", domain).First(&domainModel).Error; err != nil {
		return fmt.Errorf("域名不存在: %s", domain)
	}

	record := &models.CertRecord{
		DomainID: domainModel.ID,
		Domain:   domain,
		Status:   "warning",
	}

	if config.Cfg.Alert.DingTalk.Enabled {
		s.sendDingTalkAlert(record)
	}
	if config.Cfg.Alert.Email.Enabled {
		s.sendEmailAlert(record)
	}
	if config.Cfg.Alert.WeCom.Enabled {
		s.sendWeComAlert(record)
	}

	alertLog := &models.AlertLog{
		DomainID:  domainModel.ID,
		Domain:    domain,
		AlertType: s.determineAlertType(record),
		Level:     level,
		Content:   message,
		Sent:      true,
		SentAt:    timePtr(time.Now()),
	}
	db.Create(alertLog)

	return nil
}

func (s *AlertService) GetAlertLogs(page, pageSize int) ([]models.AlertLog, int64, error) {
	db := storage.GetDB()
	var logs []models.AlertLog
	var total int64

	offset := (page - 1) * pageSize

	db.Model(&models.AlertLog{}).Count(&total)
	err := db.Order("created_at DESC").Offset(offset).Limit(pageSize).Find(&logs).Error

	return logs, total, err
}

func timePtr(t time.Time) *time.Time {
	return &t
}

func (s *AlertService) SendCertIssueAlert(domain string, domainID uint, message string, level string) error {
	record := &models.CertRecord{
		DomainID: domainID,
		Domain:   domain,
		Status:   "warning",
	}

	if config.Cfg.Alert.DingTalk.Enabled {
		go s.sendDingTalkCertIssue(domain, message, level)
	}
	if config.Cfg.Alert.Email.Enabled {
		go s.sendEmailCertIssue(domain, message, level)
	}
	if config.Cfg.Alert.WeCom.Enabled {
		go s.sendWeComCertIssue(domain, message, level)
	}

	alertLog := &models.AlertLog{
		DomainID:  domainID,
		Domain:    domain,
		AlertType: s.determineAlertType(record),
		Level:     level,
		Content:   message,
		Sent:      true,
		SentAt:    timePtr(time.Now()),
	}

	db := storage.GetDB()
	db.Create(alertLog)

	return nil
}

func (s *AlertService) sendDingTalkCertIssue(domain, message, level string) {
	webhook := config.Cfg.Alert.DingTalk.Webhook
	secret := config.Cfg.Alert.DingTalk.Secret

	timestamp := fmt.Sprintf("%d", time.Now().UnixMilli())
	sign := s.generateDingTalkSign(timestamp, secret)
	fullURL := fmt.Sprintf("%s&timestamp=%s&sign=%s", webhook, timestamp, sign)

	title := fmt.Sprintf("【SSL证书%s告警】", s.getAlertLevelText(level))
	content := fmt.Sprintf("## %s\n\n", title)
	content += fmt.Sprintf("**域名**: %s\n\n", domain)
	content += fmt.Sprintf("**告警内容**: %s\n\n", message)
	content += fmt.Sprintf("**告警级别**: %s\n\n", s.getAlertLevelText(level))
	content += fmt.Sprintf("**检查时间**: %s\n", time.Now().Format("2006-01-02 15:04:05"))

	msg := DingTalkMessage{
		MsgType: "markdown",
		Markdown: &DingTalkMarkdownContent{
			Title: title,
			Text:  content,
		},
	}

	body, _ := json.Marshal(msg)
	resp, err := http.Post(fullURL, "application/json", bytes.NewReader(body))
	if err != nil {
		config.Logger.Error("发送钉钉证书问题告警失败", zap.Error(err))
		return
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	config.Logger.Info("钉钉证书问题告警发送完成", zap.String("response", string(respBody)))
}

func (s *AlertService) sendEmailCertIssue(domain, message, level string) {
	emailConfig := config.Cfg.Alert.Email
	subject := fmt.Sprintf("【SSL证书%s告警】%s", s.getAlertLevelText(level), domain)

	body := fmt.Sprintf(`
		<h2>SSL证书告警通知</h2>
		<table border="1" cellpadding="8" cellspacing="0">
			<tr><td><strong>域名</strong></td><td>%s</td></tr>
			<tr><td><strong>告警内容</strong></td><td>%s</td></tr>
			<tr><td><strong>告警级别</strong></td><td>%s</td></tr>
			<tr><td><strong>检查时间</strong></td><td>%s</td></tr>
		</table>
	`, domain, message, s.getAlertLevelText(level), time.Now().Format("2006-01-02 15:04:05"))

	m := gomail.NewMessage()
	m.SetHeader("From", emailConfig.From)
	m.SetHeader("To", emailConfig.To)
	m.SetHeader("Subject", subject)
	m.SetBody("text/html", body)

	d := gomail.NewDialer(emailConfig.Host, emailConfig.Port, emailConfig.Username, emailConfig.Password)
	if err := d.DialAndSend(m); err != nil {
		config.Logger.Error("发送邮件证书问题告警失败", zap.Error(err))
		return
	}
	config.Logger.Info("邮件证书问题告警发送完成", zap.String("domain", domain))
}

func (s *AlertService) sendWeComCertIssue(domain, message, level string) {
	webhook := config.Cfg.Alert.WeCom.Webhook

	title := fmt.Sprintf("【SSL证书%s告警】", s.getAlertLevelText(level))
	content := fmt.Sprintf("## %s\n\n", title)
	content += fmt.Sprintf("**域名**: <font color=\"info\">%s</font>\n", domain)
	content += fmt.Sprintf("**告警内容**: %s\n", message)
	content += fmt.Sprintf("**告警级别**: <font color=\"comment\">%s</font>\n", s.getAlertLevelText(level))
	content += fmt.Sprintf("**检查时间**: %s\n", time.Now().Format("2006-01-02 15:04:05"))

	msg := WeComMessage{
		MsgType: "markdown",
		Markdown: &WeComMarkdownContent{
			Content: content,
		},
	}

	body, _ := json.Marshal(msg)
	resp, err := http.Post(webhook, "application/json", bytes.NewReader(body))
	if err != nil {
		config.Logger.Error("发送企微证书问题告警失败", zap.Error(err))
		return
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	config.Logger.Info("企微证书问题告警发送完成", zap.String("response", string(respBody)))
}
