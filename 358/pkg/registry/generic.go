package registry

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"
)

type GenericRegistryClient struct {
	baseURL    string
	username   string
	password   string
	httpClient *http.Client
}

func NewGenericRegistryClient(baseURL, username, password string, insecure bool) (*GenericRegistryClient, error) {
	transport := &http.Transport{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: insecure,
		},
	}

	return &GenericRegistryClient{
		baseURL:  strings.TrimSuffix(baseURL, "/"),
		username: username,
		password: password,
		httpClient: &http.Client{
			Transport: transport,
			Timeout:   5 * time.Minute,
		},
	}, nil
}

func (c *GenericRegistryClient) doRequest(ctx context.Context, method, path string, body io.Reader, headers map[string]string) (*http.Response, error) {
	url := c.baseURL + path
	req, err := http.NewRequestWithContext(ctx, method, url, body)
	if err != nil {
		return nil, err
	}

	if c.username != "" && c.password != "" {
		req.SetBasicAuth(c.username, c.password)
	}

	for k, v := range headers {
		req.Header.Set(k, v)
	}

	return c.httpClient.Do(req)
}

func (c *GenericRegistryClient) ListRepositories(ctx context.Context, prefix string) ([]string, error) {
	var allRepos []string
	last := ""

	for {
		path := "/v2/_catalog?n=100"
		if last != "" {
			path += "&last=" + url.QueryEscape(last)
		}

		resp, err := c.doRequest(ctx, "GET", path, nil, nil)
		if err != nil {
			return nil, err
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			body, _ := io.ReadAll(resp.Body)
			return nil, fmt.Errorf("failed to list repositories: %s", body)
		}

		var result struct {
			Repositories []string `json:"repositories"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
			return nil, err
		}

		for _, repo := range result.Repositories {
			if prefix == "" || strings.HasPrefix(repo, prefix) {
				allRepos = append(allRepos, repo)
			}
		}

		linkHeader := resp.Header.Get("Link")
		if linkHeader == "" || !strings.Contains(linkHeader, "rel=\"next\"") {
			break
		}

		if strings.Contains(linkHeader, "last=") {
			parts := strings.Split(linkHeader, "last=")
			if len(parts) > 1 {
				last = strings.Split(parts[1], ">")[0]
				last, _ = url.QueryUnescape(last)
			}
		}

		if len(result.Repositories) == 0 {
			break
		}
	}

	return allRepos, nil
}

func (c *GenericRegistryClient) ListTags(ctx context.Context, repository string) ([]string, error) {
	var allTags []string
	last := ""

	for {
		path := fmt.Sprintf("/v2/%s/tags/list?n=100", repository)
		if last != "" {
			path += "&last=" + url.QueryEscape(last)
		}

		resp, err := c.doRequest(ctx, "GET", path, nil, nil)
		if err != nil {
			return nil, err
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			body, _ := io.ReadAll(resp.Body)
			return nil, fmt.Errorf("failed to list tags: %s", body)
		}

		var result struct {
			Tags []string `json:"tags"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
			return nil, err
		}

		allTags = append(allTags, result.Tags...)

		linkHeader := resp.Header.Get("Link")
		if linkHeader == "" || !strings.Contains(linkHeader, "rel=\"next\"") {
			break
		}

		if len(result.Tags) == 0 {
			break
		}
	}

	return allTags, nil
}

func (c *GenericRegistryClient) GetImageInfo(ctx context.Context, repository, tag string) (*ImageInfo, error) {
	manifest, err := c.GetManifest(ctx, repository, tag)
	if err != nil {
		return nil, err
	}

	var manifestObj map[string]interface{}
	if err := json.Unmarshal(manifest.Content, &manifestObj); err != nil {
		return nil, err
	}

	var size int64
	if layers, ok := manifestObj["layers"].([]interface{}); ok {
		for _, layer := range layers {
			if layerMap, ok := layer.(map[string]interface{}); ok {
				if layerSize, ok := layerMap["size"].(float64); ok {
					size += int64(layerSize)
				}
			}
		}
	}

	return &ImageInfo{
		Repository: repository,
		Tag:        tag,
		Digest:     manifest.Digest,
		Size:       size,
		MediaType:  manifest.MediaType,
	}, nil
}

func (c *GenericRegistryClient) GetManifest(ctx context.Context, repository, reference string) (*Manifest, error) {
	headers := map[string]string{
		"Accept": "application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json",
	}

	resp, err := c.doRequest(ctx, "GET", fmt.Sprintf("/v2/%s/manifests/%s", repository, reference), nil, headers)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("failed to get manifest: %s", body)
	}

	content, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	digest := resp.Header.Get("Docker-Content-Digest")
	mediaType := resp.Header.Get("Content-Type")

	return &Manifest{
		Content:     content,
		Digest:      digest,
		MediaType:   mediaType,
		SchemaVersion: 2,
	}, nil
}

func (c *GenericRegistryClient) GetBlob(ctx context.Context, repository, digest string) (io.ReadCloser, int64, error) {
	resp, err := c.doRequest(ctx, "GET", fmt.Sprintf("/v2/%s/blobs/%s", repository, digest), nil, nil)
	if err != nil {
		return nil, 0, err
	}

	if resp.StatusCode != http.StatusOK {
		resp.Body.Close()
		body, _ := io.ReadAll(resp.Body)
		return nil, 0, fmt.Errorf("failed to get blob: %s", body)
	}

	size, _ := strconv.ParseInt(resp.Header.Get("Content-Length"), 10, 64)
	return resp.Body, size, nil
}

func (c *GenericRegistryClient) PushManifest(ctx context.Context, repository, reference string, manifest *Manifest) error {
	headers := map[string]string{
		"Content-Type": manifest.MediaType,
	}

	resp, err := c.doRequest(ctx, "PUT", fmt.Sprintf("/v2/%s/manifests/%s", repository, reference), bytes.NewReader(manifest.Content), headers)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("failed to push manifest: %s", body)
	}

	return nil
}

func (c *GenericRegistryClient) PushBlob(ctx context.Context, repository, digest string, content io.Reader, size int64) error {
	locationResp, err := c.doRequest(ctx, "POST", fmt.Sprintf("/v2/%s/blobs/uploads/", repository), nil, nil)
	if err != nil {
		return err
	}
	defer locationResp.Body.Close()

	if locationResp.StatusCode != http.StatusAccepted {
		body, _ := io.ReadAll(locationResp.Body)
		return fmt.Errorf("failed to start blob upload: %s", body)
	}

	location := locationResp.Header.Get("Location")
	if location == "" {
		return fmt.Errorf("no location header in blob upload response")
	}

	uploadURL := location
	if !strings.HasPrefix(uploadURL, "http") {
		uploadURL = c.baseURL + uploadURL
	}

	sep := "?"
	if strings.Contains(uploadURL, "?") {
		sep = "&"
	}
	uploadURL += sep + "digest=" + digest

	req, err := http.NewRequestWithContext(ctx, "PUT", uploadURL, content)
	if err != nil {
		return err
	}

	if c.username != "" && c.password != "" {
		req.SetBasicAuth(c.username, c.password)
	}

	req.ContentLength = size
	req.Header.Set("Content-Type", "application/octet-stream")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("failed to push blob: %s", body)
	}

	return nil
}

func (c *GenericRegistryClient) BlobExists(ctx context.Context, repository, digest string) (bool, error) {
	resp, err := c.doRequest(ctx, "HEAD", fmt.Sprintf("/v2/%s/blobs/%s", repository, digest), nil, nil)
	if err != nil {
		return false, err
	}
	defer resp.Body.Close()

	return resp.StatusCode == http.StatusOK, nil
}

func (c *GenericRegistryClient) ManifestExists(ctx context.Context, repository, reference string) (bool, error) {
	headers := map[string]string{
		"Accept": "application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json",
	}

	resp, err := c.doRequest(ctx, "HEAD", fmt.Sprintf("/v2/%s/manifests/%s", repository, reference), nil, headers)
	if err != nil {
		return false, err
	}
	defer resp.Body.Close()

	return resp.StatusCode == http.StatusOK, nil
}

func (c *GenericRegistryClient) DeleteTag(ctx context.Context, repository, tag string) error {
	manifest, err := c.GetManifest(ctx, repository, tag)
	if err != nil {
		return fmt.Errorf("failed to get manifest for deletion: %w", err)
	}

	return c.DeleteManifest(ctx, repository, manifest.Digest)
}

func (c *GenericRegistryClient) DeleteManifest(ctx context.Context, repository, reference string) error {
	headers := map[string]string{
		"Accept": "application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json",
	}

	resp, err := c.doRequest(ctx, "DELETE", fmt.Sprintf("/v2/%s/manifests/%s", repository, reference), nil, headers)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusAccepted {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("failed to delete manifest: %s", body)
	}

	return nil
}
