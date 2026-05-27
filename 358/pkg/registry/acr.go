package registry

import (
	"context"
	"crypto/hmac"
	"crypto/sha1"
	"encoding/base64"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"
)

type ACRClient struct {
	baseURL      string
	accessKey    string
	secretKey    string
	region       string
	httpClient   *http.Client
	generic      *GenericRegistryClient
}

func NewACRClient(baseURL, accessKey, secretKey, region string, insecure bool) (*ACRClient, error) {
	generic, err := NewGenericRegistryClient(baseURL, accessKey, "", insecure)
	if err != nil {
		return nil, err
	}

	return &ACRClient{
		baseURL:   strings.TrimSuffix(baseURL, "/"),
		accessKey: accessKey,
		secretKey: secretKey,
		region:    region,
		httpClient: &http.Client{
			Timeout: 5 * time.Minute,
		},
		generic: generic,
	}, nil
}

func (c *ACRClient) signRequest(req *http.Request) {
	timestamp := strconv.FormatInt(time.Now().UnixNano()/1e6, 10)
	signature := c.generateSignature(req.Method, req.URL.Path, timestamp)
	
	req.Header.Set("X-Ac-Access-Key", c.accessKey)
	req.Header.Set("X-Ac-Timestamp", timestamp)
	req.Header.Set("X-Ac-Signature", signature)
}

func (c *ACRClient) generateSignature(method, path, timestamp string) string {
	signString := method + "\n" + path + "\n" + timestamp
	mac := hmac.New(sha1.New, []byte(c.secretKey))
	mac.Write([]byte(signString))
	return base64.StdEncoding.EncodeToString(mac.Sum(nil))
}

func (c *ACRClient) getAuthToken(ctx context.Context) (string, error) {
	path := "/tokens"
	req, err := http.NewRequestWithContext(ctx, "GET", c.baseURL+path, nil)
	if err != nil {
		return "", err
	}

	c.signRequest(req)
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("failed to get token: %s", body)
	}

	var result struct {
		Token string `json:"token"`
	}
	return result.Token, nil
}

func (c *ACRClient) ListRepositories(ctx context.Context, prefix string) ([]string, error) {
	return c.generic.ListRepositories(ctx, prefix)
}

func (c *ACRClient) ListTags(ctx context.Context, repository string) ([]string, error) {
	return c.generic.ListTags(ctx, repository)
}

func (c *ACRClient) GetImageInfo(ctx context.Context, repository, tag string) (*ImageInfo, error) {
	return c.generic.GetImageInfo(ctx, repository, tag)
}

func (c *ACRClient) GetManifest(ctx context.Context, repository, reference string) (*Manifest, error) {
	return c.generic.GetManifest(ctx, repository, reference)
}

func (c *ACRClient) GetBlob(ctx context.Context, repository, digest string) (io.ReadCloser, int64, error) {
	return c.generic.GetBlob(ctx, repository, digest)
}

func (c *ACRClient) PushManifest(ctx context.Context, repository, reference string, manifest *Manifest) error {
	return c.generic.PushManifest(ctx, repository, reference, manifest)
}

func (c *ACRClient) PushBlob(ctx context.Context, repository, digest string, content io.Reader, size int64) error {
	return c.generic.PushBlob(ctx, repository, digest, content, size)
}

func (c *ACRClient) BlobExists(ctx context.Context, repository, digest string) (bool, error) {
	return c.generic.BlobExists(ctx, repository, digest)
}

func (c *ACRClient) ManifestExists(ctx context.Context, repository, reference string) (bool, error) {
	return c.generic.ManifestExists(ctx, repository, reference)
}

func (c *ACRClient) DeleteTag(ctx context.Context, repository, tag string) error {
	return c.generic.DeleteTag(ctx, repository, tag)
}

func (c *ACRClient) DeleteManifest(ctx context.Context, repository, reference string) error {
	return c.generic.DeleteManifest(ctx, repository, reference)
}
