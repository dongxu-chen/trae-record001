package cert

import (
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"time"

	"ssl-manager/internal/acme"
	"ssl-manager/internal/config"
	"ssl-manager/internal/deploy"
)

type Manager struct {
	cfg        *config.Config
	acmeClient *acme.ACMEClient
}

func NewManager(cfg *config.Config, acmeClient *acme.ACMEClient) *Manager {
	return &Manager{
		cfg:        cfg,
		acmeClient: acmeClient,
	}
}

func (m *Manager) CheckAndRenewAll() error {
	for _, certCfg := range m.cfg.Certificates {
		log.Printf("Checking certificate: %s", certCfg.Name)

		certPath := filepath.Join(certCfg.OutputDir, "fullchain.pem")
		keyPath := filepath.Join(certCfg.OutputDir, "privkey.pem")

		needsRenewal, err := m.needsRenewal(certPath)
		if err != nil {
			log.Printf("Error checking certificate %s: %v, will attempt to issue new one", certCfg.Name, err)
			needsRenewal = true
		}

		if needsRenewal {
			log.Printf("Certificate %s needs renewal, starting process...", certCfg.Name)

			if _, err := os.Stat(certPath); os.IsNotExist(err) {
				log.Printf("Issuing new certificate for %s", certCfg.Name)
				if err := m.acmeClient.ObtainCertificate(certCfg.Domains, certCfg.OutputDir); err != nil {
					return fmt.Errorf("obtain certificate for %s failed: %w", certCfg.Name, err)
				}
			} else {
				log.Printf("Renewing certificate for %s", certCfg.Name)
				if err := m.acmeClient.RenewCertificate(certPath, keyPath, certCfg.Domains, certCfg.OutputDir); err != nil {
					return fmt.Errorf("renew certificate for %s failed: %w", certCfg.Name, err)
				}
			}

			if certCfg.DeployTarget != "" {
				log.Printf("Deploying certificate %s to %s", certCfg.Name, certCfg.DeployTarget)
				deployer, err := deploy.NewDeployer(&m.cfg.Deploy, certCfg.DeployTarget)
				if err != nil {
					return fmt.Errorf("create deployer for %s failed: %w", certCfg.Name, err)
				}

				if err := deployer.Deploy(certPath, keyPath); err != nil {
					return fmt.Errorf("deploy certificate %s failed: %w", certCfg.Name, err)
				}
				log.Printf("Certificate %s deployed successfully", certCfg.Name)
			}

			log.Printf("Certificate %s processed successfully", certCfg.Name)
		} else {
			log.Printf("Certificate %s is valid, no renewal needed", certCfg.Name)
		}
	}

	return nil
}

func (m *Manager) needsRenewal(certPath string) (bool, error) {
	if _, err := os.Stat(certPath); os.IsNotExist(err) {
		return true, nil
	}

	cert, err := loadCertificate(certPath)
	if err != nil {
		return false, fmt.Errorf("load certificate failed: %w", err)
	}

	daysRemaining := int(time.Until(cert.NotAfter).Hours() / 24)
	log.Printf("Certificate expires in %d days (threshold: %d days)", daysRemaining, m.cfg.Renewal.DaysBefore)

	return daysRemaining <= m.cfg.Renewal.DaysBefore, nil
}

func loadCertificate(certPath string) (*x509.Certificate, error) {
	certBytes, err := os.ReadFile(certPath)
	if err != nil {
		return nil, fmt.Errorf("read certificate file failed: %w", err)
	}

	block, _ := pem.Decode(certBytes)
	if block == nil {
		return nil, fmt.Errorf("failed to decode PEM block")
	}

	cert, err := x509.ParseCertificate(block.Bytes)
	if err != nil {
		return nil, fmt.Errorf("parse certificate failed: %w", err)
	}

	return cert, nil
}

func (m *Manager) GetCertificateInfo(certPath string) (string, time.Time, error) {
	cert, err := loadCertificate(certPath)
	if err != nil {
		return "", time.Time{}, err
	}

	return cert.Subject.CommonName, cert.NotAfter, nil
}
