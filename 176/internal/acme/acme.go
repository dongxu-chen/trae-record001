package acme

import (
	"crypto"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"fmt"
	"io"
	"os"
	"path/filepath"

	"github.com/go-acme/lego/v4/certcrypto"
	"github.com/go-acme/lego/v4/certificate"
	"github.com/go-acme/lego/v4/lego"
	"github.com/go-acme/lego/v4/registration"
	"ssl-manager/internal/config"
	"ssl-manager/internal/security"
)

type KeyStore interface {
	StorePrivateKey(keyName string, privateKey []byte) error
	LoadPrivateKey(keyName string) ([]byte, error)
}

type ACMEClient struct {
	client    *lego.Client
	cfg       *config.Config
	keyStore  KeyStore
	useHSM     bool
}

type User struct {
	Email        string
	Registration *registration.Resource
	key          crypto.PrivateKey
}

func (u *User) GetEmail() string {
	return u.Email
}

func (u *User) GetRegistration() *registration.Resource {
	return u.Registration
}

func (u *User) GetPrivateKey() crypto.PrivateKey {
	return u.key
}

func NewClient(cfg *config.Config) (*ACMEClient, error) {
	var keyStore KeyStore
	useHSM := cfg.Security.HSM.Enabled

	if useHSM {
		km, err := security.NewKeyManager(cfg.Security.HSM)
		if err != nil {
			return nil, fmt.Errorf("create key manager failed: %w", err)
		}
		keyStore = km
	}

	privateKey, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		return nil, fmt.Errorf("generate private key failed: %w", err)
	}

	user := &User{
		Email: cfg.ACME.Email,
		key:   privateKey,
	}

	legoConfig := lego.NewConfig(user)
	legoConfig.CADirURL = cfg.ACME.DirectoryURL
	legoConfig.Certificate.KeyType = getKeyType(cfg.ACME.KeyType)

	client, err := lego.NewClient(legoConfig)
	if err != nil {
		return nil, fmt.Errorf("create lego client failed: %w", err)
	}

	reg, err := client.Registration.Register(registration.RegisterOptions{TermsOfServiceAgreed: true})
	if err != nil {
		return nil, fmt.Errorf("register user failed: %w", err)
	}
	user.Registration = reg

	return &ACMEClient{
		client:   client,
		cfg:      cfg,
		keyStore: keyStore,
		useHSM:   useHSM,
	}, nil
}

func (c *ACMEClient) SetDNSProvider(provider lego.ChallengeProvider) error {
	return c.client.Challenge.SetDNS01Provider(provider)
}

func (c *ACMEClient) ObtainCertificate(domains []string, outputDir string) error {
	request := certificate.ObtainRequest{
		Domains: domains,
		Bundle:  true,
	}

	cert, err := c.client.Certificate.Obtain(request)
	if err != nil {
		return fmt.Errorf("obtain certificate failed: %w", err)
	}

	return c.saveCertificate(cert, outputDir, domains[0])
}

func (c *ACMEClient) RenewCertificate(certPath, keyPath string, domains []string, outputDir string) error {
	if err := backupCertificate(outputDir); err != nil {
		return fmt.Errorf("backup certificate failed: %w", err)
	}

	certBytes, err := os.ReadFile(certPath)
	if err != nil {
		restoreCertificate(outputDir)
		return fmt.Errorf("read certificate failed: %w", err)
	}

	var keyBytes []byte
	if c.useHSM && c.keyStore != nil {
		keyBytes, err = c.keyStore.LoadPrivateKey(domains[0])
		if err != nil {
			restoreCertificate(outputDir)
			return fmt.Errorf("load private key from hsm failed: %w", err)
		}
	} else {
		keyBytes, err = os.ReadFile(keyPath)
		if err != nil {
			restoreCertificate(outputDir)
			return fmt.Errorf("read private key failed: %w", err)
		}
	}

	resource := &certificate.Resource{
		Domain:      domains[0],
		Certificate: certBytes,
		PrivateKey:  keyBytes,
	}

	cert, err := c.client.Certificate.RenewWithOptions(resource, &certificate.RenewOptions{
		Bundle:     true,
		PreferredChain: "",
	})
	if err != nil {
		restoreCertificate(outputDir)
		return fmt.Errorf("renew certificate failed: %w", err)
	}

	if err := c.saveCertificate(cert, outputDir, domains[0]); err != nil {
		restoreCertificate(outputDir)
		return fmt.Errorf("save certificate failed: %w", err)
	}

	if err := cleanupBackup(outputDir); err != nil {
		return fmt.Errorf("cleanup backup failed: %w", err)
	}

	return nil
}

func backupCertificate(outputDir string) error {
	backupDir := outputDir + ".backup"

	if err := os.RemoveAll(backupDir); err != nil {
		return fmt.Errorf("remove old backup failed: %w", err)
	}

	if _, err := os.Stat(outputDir); os.IsNotExist(err) {
		return nil
	}

	if err := copyDir(outputDir, backupDir); err != nil {
		return fmt.Errorf("copy certificate to backup failed: %w", err)
	}

	return nil
}

func restoreCertificate(outputDir string) error {
	backupDir := outputDir + ".backup"

	if _, err := os.Stat(backupDir); os.IsNotExist(err) {
		return nil
	}

	if err := os.RemoveAll(outputDir); err != nil {
		return fmt.Errorf("remove current certificate failed: %w", err)
	}

	if err := copyDir(backupDir, outputDir); err != nil {
		return fmt.Errorf("restore certificate from backup failed: %w", err)
	}

	return nil
}

func cleanupBackup(outputDir string) error {
	backupDir := outputDir + ".backup"
	if err := os.RemoveAll(backupDir); err != nil {
		return fmt.Errorf("remove backup directory failed: %w", err)
	}
	return nil
}

func copyDir(src, dst string) error {
	if err := os.MkdirAll(dst, 0755); err != nil {
		return fmt.Errorf("create destination directory failed: %w", err)
	}

	entries, err := os.ReadDir(src)
	if err != nil {
		return fmt.Errorf("read source directory failed: %w", err)
	}

	for _, entry := range entries {
		srcPath := filepath.Join(src, entry.Name())
		dstPath := filepath.Join(dst, entry.Name())

		if entry.IsDir() {
			if err := copyDir(srcPath, dstPath); err != nil {
				return err
			}
		} else {
			if err := copyFile(srcPath, dstPath); err != nil {
				return err
			}
		}
	}

	return nil
}

func copyFile(src, dst string) error {
	srcFile, err := os.Open(src)
	if err != nil {
		return fmt.Errorf("open source file failed: %w", err)
	}
	defer srcFile.Close()

	info, err := srcFile.Stat()
	if err != nil {
		return fmt.Errorf("get source file info failed: %w", err)
	}

	dstFile, err := os.OpenFile(dst, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, info.Mode())
	if err != nil {
		return fmt.Errorf("create destination file failed: %w", err)
	}
	defer dstFile.Close()

	if _, err := io.Copy(dstFile, srcFile); err != nil {
		return fmt.Errorf("copy file content failed: %w", err)
	}

	return nil
}

func (c *ACMEClient) saveCertificate(cert *certificate.Resource, outputDir, keyName string) error {
	if err := os.MkdirAll(outputDir, 0755); err != nil {
		return fmt.Errorf("create output directory failed: %w", err)
	}

	certPath := filepath.Join(outputDir, "fullchain.pem")
	if err := os.WriteFile(certPath, cert.Certificate, 0644); err != nil {
		return fmt.Errorf("save certificate failed: %w", err)
	}

	if c.useHSM && c.keyStore != nil {
		if err := c.keyStore.StorePrivateKey(keyName, cert.PrivateKey); err != nil {
			return fmt.Errorf("encrypt and store private key failed: %w", err)
		}
	} else {
		keyPath := filepath.Join(outputDir, "privkey.pem")
		if err := os.WriteFile(keyPath, cert.PrivateKey, 0600); err != nil {
			return fmt.Errorf("save private key failed: %w", err)
		}
	}

	issuerPath := filepath.Join(outputDir, "chain.pem")
	if err := os.WriteFile(issuerPath, cert.IssuerCertificate, 0644); err != nil {
		return fmt.Errorf("save issuer certificate failed: %w", err)
	}

	return nil
}

func getKeyType(keyType string) certcrypto.KeyType {
	switch keyType {
	case "rsa2048":
		return certcrypto.RSA2048
	case "rsa4096":
		return certcrypto.RSA4096
	case "rsa8192":
		return certcrypto.RSA8192
	case "ec256":
		return certcrypto.EC256
	case "ec384":
		return certcrypto.EC384
	default:
		return certcrypto.RSA2048
	}
}
