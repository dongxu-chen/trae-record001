package deploy

import (
	"fmt"
	"io"
	"log"
	"math"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/aliyun/alibaba-cloud-sdk-go/services/slb"
	"ssl-manager/internal/config"
)

const (
	maxRetries     = 5
	baseDelay      = 1 * time.Second
	maxDelay       = 60 * time.Second
)

type Deployer interface {
	Deploy(certPath, keyPath string) error
}

type NginxDeployer struct {
	cfg config.NginxDeployConfig
}

func NewNginxDeployer(cfg config.NginxDeployConfig) *NginxDeployer {
	return &NginxDeployer{cfg: cfg}
}

func (d *NginxDeployer) Deploy(certPath, keyPath string) error {
	if err := copyFile(certPath, d.cfg.CertPath); err != nil {
		return fmt.Errorf("copy certificate to nginx failed: %w", err)
	}

	if err := copyFile(keyPath, d.cfg.KeyPath); err != nil {
		return fmt.Errorf("copy private key to nginx failed: %w", err)
	}

	if d.cfg.ReloadCommand != "" {
		cmd := exec.Command("sh", "-c", d.cfg.ReloadCommand)
		output, err := cmd.CombinedOutput()
		if err != nil {
			return fmt.Errorf("reload nginx failed: %w, output: %s", err, string(output))
		}
	}

	return nil
}

type AliyunSLBDeployer struct {
	client *slb.Client
	cfg    config.AliyunSLBDeployConfig
}

func NewAliyunSLBDeployer(cfg config.AliyunSLBDeployConfig) (*AliyunSLBDeployer, error) {
	client, err := slb.NewClientWithAccessKey(cfg.RegionID, cfg.AccessKeyID, cfg.AccessKeySecret)
	if err != nil {
		return nil, fmt.Errorf("create slb client failed: %w", err)
	}
	return &AliyunSLBDeployer{client: client, cfg: cfg}, nil
}

func (d *AliyunSLBDeployer) Deploy(certPath, keyPath string) error {
	certBytes, err := os.ReadFile(certPath)
	if err != nil {
		return fmt.Errorf("read certificate failed: %w", err)
	}

	keyBytes, err := os.ReadFile(keyPath)
	if err != nil {
		return fmt.Errorf("read private key failed: %w", err)
	}

	certName := fmt.Sprintf("ssl-cert-%d", time.Now().Unix())

	uploadRequest := slb.CreateUploadServerCertificateRequest()
	uploadRequest.ServerCertificateName = certName
	uploadRequest.ServerCertificate = string(certBytes)
	uploadRequest.PrivateKey = string(keyBytes)

	var uploadResponse *slb.UploadServerCertificateResponse
	err = retryWithBackoff(func() error {
		var uploadErr error
		uploadResponse, uploadErr = d.client.UploadServerCertificate(uploadRequest)
		return uploadErr
	}, "upload server certificate")
	if err != nil {
		return fmt.Errorf("upload server certificate failed: %w", err)
	}

	certID := uploadResponse.ServerCertificateId

	setListenerRequest := slb.CreateSetLoadBalancerHTTPSListenerAttributeRequest()
	setListenerRequest.LoadBalancerId = d.cfg.LoadBalancerID
	setListenerRequest.ListenerPort = d.cfg.ListenerPort
	setListenerRequest.ServerCertificateId = certID

	err = retryWithBackoff(func() error {
		_, setErr := d.client.SetLoadBalancerHTTPSListenerAttribute(setListenerRequest)
		return setErr
	}, "set load balancer https listener attribute")
	if err != nil {
		return fmt.Errorf("set load balancer https listener attribute failed: %w", err)
	}

	return nil
}

func isThrottlingError(err error) bool {
	if err == nil {
		return false
	}
	errStr := err.Error()
	return strings.Contains(errStr, "Throttling") ||
		strings.Contains(errStr, "throttling") ||
		strings.Contains(errStr, "RateLimit") ||
		strings.Contains(errStr, "rate limit") ||
		strings.Contains(errStr, "503") ||
		strings.Contains(errStr, "ServiceUnavailable") ||
		strings.Contains(errStr, "TryAgain")
}

func retryWithBackoff(operation func() error, operationName string) error {
	var lastErr error
	for attempt := 0; attempt < maxRetries; attempt++ {
		err := operation()
		if err == nil {
			return nil
		}

		lastErr = err
		if !isThrottlingError(err) {
			return err
		}

		delay := time.Duration(math.Pow(2, float64(attempt))) * baseDelay
		if delay > maxDelay {
			delay = maxDelay
		}

		log.Printf("Operation %s throttled (attempt %d/%d), retrying in %v...",
			operationName, attempt+1, maxRetries, delay)
		time.Sleep(delay)
	}

	return fmt.Errorf("operation %s failed after %d attempts: %w",
		operationName, maxRetries, lastErr)
}

func copyFile(src, dst string) error {
	srcFile, err := os.Open(src)
	if err != nil {
		return fmt.Errorf("open source file failed: %w", err)
	}
	defer srcFile.Close()

	if err := os.MkdirAll(filepath.Dir(dst), 0755); err != nil {
		return fmt.Errorf("create destination directory failed: %w", err)
	}

	dstFile, err := os.Create(dst)
	if err != nil {
		return fmt.Errorf("create destination file failed: %w", err)
	}
	defer dstFile.Close()

	_, err = io.Copy(dstFile, srcFile)
	if err != nil {
		return fmt.Errorf("copy file content failed: %w", err)
	}

	return nil
}

func NewDeployer(cfg *config.DeployConfig, target string) (Deployer, error) {
	switch target {
	case "nginx":
		if !cfg.Nginx.Enabled {
			return nil, fmt.Errorf("nginx deploy is not enabled")
		}
		return NewNginxDeployer(cfg.Nginx), nil
	case "aliyun_slb":
		if !cfg.AliyunSLB.Enabled {
			return nil, fmt.Errorf("aliyun slb deploy is not enabled")
		}
		return NewAliyunSLBDeployer(cfg.AliyunSLB)
	default:
		return nil, fmt.Errorf("unsupported deploy target: %s", target)
	}
}
