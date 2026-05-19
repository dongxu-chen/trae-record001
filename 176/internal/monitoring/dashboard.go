package monitoring

import (
	"crypto/x509"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"html/template"
	"net/http"
	"os"
	"path/filepath"
	"sync"
	"time"

	"ssl-manager/internal/config"
	"ssl-manager/internal/tenant"
)

type CertificateStatus string

const (
	StatusValid      CertificateStatus = "valid"
	StatusExpiring   CertificateStatus = "expiring"
	StatusExpired    CertificateStatus = "expired"
	StatusNotFound   CertificateStatus = "not_found"
	StatusError      CertificateStatus = "error"
)

type CertificateInfo struct {
	Name             string              `json:"name"`
	Domains          []string            `json:"domains"`
	OutputDir        string              `json:"output_dir"`
	DeployTarget     string              `json:"deploy_target"`
	Status           CertificateStatus   `json:"status"`
	ExpiresAt        time.Time           `json:"expires_at"`
	DaysRemaining    int                 `json:"days_remaining"`
	Issuer           string              `json:"issuer"`
	Subject          string              `json:"subject"`
	NotBefore        time.Time           `json:"not_before"`
	TenantID         string              `json:"tenant_id,omitempty"`
	TenantName       string              `json:"tenant_name,omitempty"`
}

type DashboardData struct {
	TotalCertificates int               `json:"total_certificates"`
	ValidCount        int               `json:"valid_count"`
	ExpiringCount     int               `json:"expiring_count"`
	ExpiredCount      int               `json:"expired_count"`
	ErrorCount        int               `json:"error_count"`
	Certificates      []CertificateInfo `json:"certificates"`
	GeneratedAt       time.Time         `json:"generated_at"`
}

type Monitor struct {
	cfg           *config.Config
	tenantManager *tenant.Manager
	mu            sync.RWMutex
	lastData      *DashboardData
}

func NewMonitor(cfg *config.Config, tenantManager *tenant.Manager) *Monitor {
	return &Monitor{
		cfg:           cfg,
		tenantManager: tenantManager,
	}
}

func (m *Monitor) CollectData() (*DashboardData, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	var allCerts []CertificateInfo

	for _, tenantCfg := range m.cfg.Tenants {
		for _, certCfg := range tenantCfg.Certificates {
			certInfo := m.collectCertificateInfo(certCfg, &tenantCfg)
			allCerts = append(allCerts, certInfo)
		}
	}

	validCount := 0
	expiringCount := 0
	expiredCount := 0
	errorCount := 0

	for _, cert := range allCerts {
		switch cert.Status {
		case StatusValid:
			validCount++
		case StatusExpiring:
			expiringCount++
		case StatusExpired:
			expiredCount++
		case StatusError:
			errorCount++
		}
	}

	data := &DashboardData{
		TotalCertificates: len(allCerts),
		ValidCount:        validCount,
		ExpiringCount:     expiringCount,
		ExpiredCount:      expiredCount,
		ErrorCount:        errorCount,
		Certificates:      allCerts,
		GeneratedAt:       time.Now(),
	}

	m.lastData = data
	return data, nil
}

func (m *Monitor) collectCertificateInfo(certCfg config.CertificateConfig, tenantCfg *config.TenantConfig) CertificateInfo {
	info := CertificateInfo{
		Name:         certCfg.Name,
		Domains:      certCfg.Domains,
		OutputDir:    certCfg.OutputDir,
		DeployTarget: certCfg.DeployTarget,
		Status:       StatusNotFound,
	}

	if tenantCfg != nil {
		info.TenantID = tenantCfg.ID
		info.TenantName = tenantCfg.Name
	}

	certPath := filepath.Join(certCfg.OutputDir, "fullchain.pem")
	certData, err := os.ReadFile(certPath)
	if err != nil {
		if os.IsNotExist(err) {
			info.Status = StatusNotFound
		} else {
			info.Status = StatusError
		}
		return info
	}

	cert, err := parseCertificate(certData)
	if err != nil {
		info.Status = StatusError
		return info
	}

	info.Subject = cert.Subject.CommonName
	info.Issuer = cert.Issuer.CommonName
	info.NotBefore = cert.NotBefore
	info.ExpiresAt = cert.NotAfter

	daysRemaining := int(time.Until(cert.NotAfter).Hours() / 24)
	info.DaysRemaining = daysRemaining

	switch {
	case daysRemaining <= 0:
		info.Status = StatusExpired
	case daysRemaining <= m.cfg.Renewal.DaysBefore:
		info.Status = StatusExpiring
	default:
		info.Status = StatusValid
	}

	return info
}

func parseCertificate(certData []byte) (*x509.Certificate, error) {
	block, _ := pem.Decode(certData)
	if block == nil {
		return nil, fmt.Errorf("failed to decode PEM block")
	}

	cert, err := x509.ParseCertificate(block.Bytes)
	if err != nil {
		return nil, fmt.Errorf("failed to parse certificate: %w", err)
	}

	return cert, nil
}

func (m *Monitor) GetLastData() *DashboardData {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.lastData
}

func (m *Monitor) StartServer(addr string) error {
	http.HandleFunc("/", m.handleDashboard)
	http.HandleFunc("/api/status", m.handleAPIStatus)
	http.HandleFunc("/api/metrics", m.handleAPIMetrics)

	return http.ListenAndServe(addr, nil)
}

func (m *Monitor) handleDashboard(w http.ResponseWriter, r *http.Request) {
	data, err := m.CollectData()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	tmpl := template.Must(template.New("dashboard").Parse(dashboardTemplate))
	tmpl.Execute(w, data)
}

func (m *Monitor) handleAPIStatus(w http.ResponseWriter, r *http.Request) {
	data, err := m.CollectData()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(data)
}

func (m *Monitor) handleAPIMetrics(w http.ResponseWriter, r *http.Request) {
	data := m.GetLastData()
	if data == nil {
		var err error
		data, err = m.CollectData()
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
	}

	metrics := fmt.Sprintf(`# HELP ssl_certificates_total Total number of certificates
# TYPE ssl_certificates_total gauge
ssl_certificates_total %d
# HELP ssl_certificates_valid Number of valid certificates
# TYPE ssl_certificates_valid gauge
ssl_certificates_valid %d
# HELP ssl_certificates_expiring Number of expiring certificates
# TYPE ssl_certificates_expiring gauge
ssl_certificates_expiring %d
# HELP ssl_certificates_expired Number of expired certificates
# TYPE ssl_certificates_expired gauge
ssl_certificates_expired %d
`, data.TotalCertificates, data.ValidCount, data.ExpiringCount, data.ExpiredCount)

	for _, cert := range data.Certificates {
		metrics += fmt.Sprintf(`# HELP ssl_certificate_days_remaining Days until certificate expires
# TYPE ssl_certificate_days_remaining gauge
ssl_certificate_days_remaining{name="%s",tenant="%s"} %d
`, cert.Name, cert.TenantName, cert.DaysRemaining)
	}

	w.Header().Set("Content-Type", "text/plain")
	w.Write([]byte(metrics))
}

const dashboardTemplate = `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SSL证书监控看板</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; color: #333; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; text-align: center; }
        .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .stat-card { background: white; border-radius: 10px; padding: 1.5rem; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }
        .stat-card h3 { font-size: 0.9rem; color: #666; margin-bottom: 0.5rem; }
        .stat-card .number { font-size: 2.5rem; font-weight: bold; }
        .stat-card.valid .number { color: #10b981; }
        .stat-card.expiring .number { color: #f59e0b; }
        .stat-card.expired .number { color: #ef4444; }
        .stat-card.error .number { color: #6366f1; }
        .certificates { background: white; border-radius: 10px; padding: 1.5rem; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .certificates h2 { margin-bottom: 1rem; color: #333; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 1rem; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8fafc; font-weight: 600; color: #374151; }
        tr:hover { background: #f9fafb; }
        .status-badge { padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.875rem; font-weight: 500; }
        .status-valid { background: #d1fae5; color: #065f46; }
        .status-expiring { background: #fef3c7; color: #92400e; }
        .status-expired { background: #fee2e2; color: #991b1b; }
        .status-not-found { background: #e5e7eb; color: #374151; }
        .status-error { background: #e0e7ff; color: #3730a3; }
        .days-warning { color: #f59e0b; font-weight: bold; }
        .days-danger { color: #ef4444; font-weight: bold; }
        .footer { text-align: center; padding: 2rem; color: #666; font-size: 0.875rem; }
        .tenant-tag { background: #e0e7ff; color: #3730a3; padding: 0.125rem 0.5rem; border-radius: 4px; font-size: 0.75rem; margin-right: 0.5rem; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔐 SSL证书监控看板</h1>
        <p>实时监控所有证书的签发状态和到期时间</p>
    </div>
    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <h3>证书总数</h3>
                <div class="number">{{.TotalCertificates}}</div>
            </div>
            <div class="stat-card valid">
                <h3>有效证书</h3>
                <div class="number">{{.ValidCount}}</div>
            </div>
            <div class="stat-card expiring">
                <h3>即将到期</h3>
                <div class="number">{{.ExpiringCount}}</div>
            </div>
            <div class="stat-card expired">
                <h3>已过期</h3>
                <div class="number">{{.ExpiredCount}}</div>
            </div>
        </div>
        <div class="certificates">
            <h2>证书详情</h2>
            <table>
                <thead>
                    <tr>
                        <th>租户</th>
                        <th>证书名称</th>
                        <th>域名</th>
                        <th>状态</th>
                        <th>剩余天数</th>
                        <th>到期时间</th>
                        <th>部署目标</th>
                    </tr>
                </thead>
                <tbody>
                    {{range .Certificates}}
                    <tr>
                        <td>{{if .TenantName}}<span class="tenant-tag">{{.TenantName}}</span>{{else}}<span style="color:#999">默认</span>{{end}}</td>
                        <td><strong>{{.Name}}</strong></td>
                        <td>{{range .Domains}}<div>{{.}}</div>{{end}}</td>
                        <td><span class="status-badge status-{{.Status}}">{{.Status}}</span></td>
                        <td>
                            {{if le .DaysRemaining 0}}
                                <span class="days-danger">{{.DaysRemaining}} 天</span>
                            {{else if le .DaysRemaining 30}}
                                <span class="days-warning">{{.DaysRemaining}} 天</span>
                            {{else}}
                                {{.DaysRemaining}} 天
                            {{end}}
                        </td>
                        <td>{{.ExpiresAt.Format "2006-01-02 15:04:05"}}</td>
                        <td>{{if .DeployTarget}}{{.DeployTarget}}{{else}}<span style="color:#999">未部署</span>{{end}}</td>
                    </tr>
                    {{end}}
                </tbody>
            </table>
        </div>
    </div>
    <div class="footer">
        <p>数据更新时间: {{.GeneratedAt.Format "2006-01-02 15:04:05"}}</p>
    </div>
</body>
</html>
`
