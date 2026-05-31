package email

import (
	"fmt"
	"log"

	"gopkg.in/gomail.v2"
)

type Notifier struct {
	host     string
	port     int
	username string
	password string
	from     string
}

func NewNotifier(host string, port int, username, password, from string) *Notifier {
	return &Notifier{
		host:     host,
		port:     port,
		username: username,
		password: password,
		from:     from,
	}
}

func (n *Notifier) SendConfigChangeNotification(to []string, namespace, group, dataID, operator, oldContent, newContent, diffSummary string) error {
	if len(to) == 0 {
		log.Println("No email recipients configured, skipping notification")
		return nil
	}

	subject := fmt.Sprintf("[Nacos配置变更通知] %s/%s/%s", namespace, group, dataID)

	body := fmt.Sprintf(`
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Nacos配置变更通知</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { background: #4a90d9; color: white; padding: 15px; border-radius: 5px; }
        .content { background: #f9f9f9; padding: 20px; border-radius: 5px; margin-top: 10px; }
        .info-item { margin: 10px 0; }
        .label { font-weight: bold; color: #555; }
        .diff { background: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; margin: 15px 0; }
        .footer { margin-top: 20px; color: #888; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Nacos配置变更通知</h2>
        </div>
        <div class="content">
            <div class="info-item">
                <span class="label">命名空间:</span> %s
            </div>
            <div class="info-item">
                <span class="label">分组:</span> %s
            </div>
            <div class="info-item">
                <span class="label">DataID:</span> %s
            </div>
            <div class="info-item">
                <span class="label">操作人:</span> %s
            </div>
            <div class="diff">
                <div class="label">变更摘要:</div>
                <pre>%s</pre>
            </div>
        </div>
        <div class="footer">
            此邮件由Nacos审计系统自动发送，请勿直接回复。
        </div>
    </div>
</body>
</html>
`, namespace, group, dataID, operator, diffSummary)

	return n.sendEmail(to, subject, body, true)
}

func (n *Notifier) SendRollbackNotification(to []string, namespace, group, dataID, operator, rollbackFrom, rollbackTo string) error {
	if len(to) == 0 {
		log.Println("No email recipients configured, skipping notification")
		return nil
	}

	subject := fmt.Sprintf("[Nacos配置回滚通知] %s/%s/%s", namespace, group, dataID)

	body := fmt.Sprintf(`
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Nacos配置回滚通知</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { background: #dc3545; color: white; padding: 15px; border-radius: 5px; }
        .content { background: #f9f9f9; padding: 20px; border-radius: 5px; margin-top: 10px; }
        .info-item { margin: 10px 0; }
        .label { font-weight: bold; color: #555; }
        .warning { background: #f8d7da; padding: 10px; border-left: 4px solid #dc3545; margin: 15px 0; }
        .footer { margin-top: 20px; color: #888; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Nacos配置回滚通知</h2>
        </div>
        <div class="content">
            <div class="info-item">
                <span class="label">命名空间:</span> %s
            </div>
            <div class="info-item">
                <span class="label">分组:</span> %s
            </div>
            <div class="info-item">
                <span class="label">DataID:</span> %s
            </div>
            <div class="info-item">
                <span class="label">操作人:</span> %s
            </div>
            <div class="warning">
                <div class="label">回滚信息:</div>
                <p>从版本: %s</p>
                <p>回滚至: %s</p>
            </div>
        </div>
        <div class="footer">
            此邮件由Nacos审计系统自动发送，请勿直接回复。
        </div>
    </div>
</body>
</html>
`, namespace, group, dataID, operator, rollbackFrom, rollbackTo)

	return n.sendEmail(to, subject, body, true)
}

func (n *Notifier) SendComplianceAlert(to []string, namespace, group, dataID, operator, ruleName, severity, violationMsg string) error {
	if len(to) == 0 {
		log.Println("No email recipients configured, skipping notification")
		return nil
	}

	subject := fmt.Sprintf("[Nacos合规告警 - %s] %s/%s/%s", severity, namespace, group, dataID)

	body := fmt.Sprintf(`
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Nacos合规告警</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { background: #dc3545; color: white; padding: 15px; border-radius: 5px; }
        .header.warning { background: #ffc107; }
        .content { background: #f9f9f9; padding: 20px; border-radius: 5px; margin-top: 10px; }
        .info-item { margin: 10px 0; }
        .label { font-weight: bold; color: #555; }
        .alert { background: #f8d7da; padding: 10px; border-left: 4px solid #dc3545; margin: 15px 0; }
        .alert.warning { background: #fff3cd; border-left-color: #ffc107; }
        .footer { margin-top: 20px; color: #888; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Nacos合规告警 - %s</h2>
        </div>
        <div class="content">
            <div class="info-item">
                <span class="label">命名空间:</span> %s
            </div>
            <div class="info-item">
                <span class="label">分组:</span> %s
            </div>
            <div class="info-item">
                <span class="label">DataID:</span> %s
            </div>
            <div class="info-item">
                <span class="label">操作人:</span> %s
            </div>
            <div class="alert">
                <div class="label">违规规则: %s</div>
                <div class="label">严重级别: %s</div>
                <div class="label">违规详情:</div>
                <p>%s</p>
            </div>
        </div>
        <div class="footer">
            此邮件由Nacos审计系统自动发送，请勿直接回复。
        </div>
    </div>
</body>
</html>
`, severity, namespace, group, dataID, operator, ruleName, severity, violationMsg)

	return n.sendEmail(to, subject, body, true)
}

func (n *Notifier) sendEmail(to []string, subject, body string, isHTML bool) error {
	m := gomail.NewMessage()
	m.SetHeader("From", n.from)
	m.SetHeader("To", to...)
	m.SetHeader("Subject", subject)

	contentType := "text/plain"
	if isHTML {
		contentType = "text/html"
	}
	m.SetBody(contentType, body)

	d := gomail.NewDialer(n.host, n.port, n.username, n.password)

	if err := d.DialAndSend(m); err != nil {
		log.Printf("Failed to send email: %v", err)
		return err
	}

	log.Printf("Email sent successfully to %v", to)
	return nil
}
