package registry

import (
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

type HarborClient struct {
	baseURL    string
	username   string
	password   string
	httpClient *http.Client
	generic    *GenericRegistryClient
}

func NewHarborClient(baseURL, username, password string, insecure bool) (*HarborClient, error) {
	transport := &http.Transport{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: insecure,
		},
	}

	generic, err := NewGenericRegistryClient(baseURL, username, password, insecure)
	if err != nil {
		return nil, err
	}

	return &HarborClient{
		baseURL:  strings.TrimSuffix(baseURL, "/"),
		username: username,
		password: password,
		httpClient: &http.Client{
			Transport: transport,
			Timeout:   5 * time.Minute,
		},
		generic: generic,
	}, nil
}

func (c *HarborClient) doAPIRequest(ctx context.Context, method, path string, body io.Reader) (*http.Response, error) {
	url := c.baseURL + "/api/v2.0" + path
	req, err := http.NewRequestWithContext(ctx, method, url, body)
	if err != nil {
		return nil, err
	}

	req.SetBasicAuth(c.username, c.password)
	req.Header.Set("Content-Type", "application/json")

	return c.httpClient.Do(req)
}

func (c *HarborClient) ListRepositories(ctx context.Context, prefix string) ([]string, error) {
	var allRepos []string
	page := 1
	pageSize := 100

	for {
		projectPath := fmt.Sprintf("/projects?page=%d&page_size=%d", page, pageSize)
		resp, err := c.doAPIRequest(ctx, "GET", projectPath, nil)
		if err != nil {
			return nil, err
		}

		if resp.StatusCode != http.StatusOK {
			body, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			return nil, fmt.Errorf("failed to list projects: %s", body)
		}

		var projects []struct {
			Name string `json:"name"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&projects); err != nil {
			resp.Body.Close()
			return nil, err
		}
		resp.Body.Close()

		if len(projects) == 0 {
			break
		}

		for _, project := range projects {
			repoPage := 1
			for {
				repoPath := fmt.Sprintf("/projects/%s/repositories?page=%d&page_size=%d", project.Name, repoPage, pageSize)
				repoResp, err := c.doAPIRequest(ctx, "GET", repoPath, nil)
				if err != nil {
					return nil, err
				}

				if repoResp.StatusCode != http.StatusOK {
					body, _ := io.ReadAll(repoResp.Body)
					repoResp.Body.Close()
					return nil, fmt.Errorf("failed to list repositories: %s", body)
				}

				var repos []struct {
					Name string `json:"name"`
				}
				if err := json.NewDecoder(repoResp.Body).Decode(&repos); err != nil {
					repoResp.Body.Close()
					return nil, err
				}
				repoResp.Body.Close()

				if len(repos) == 0 {
					break
				}

				for _, repo := range repos {
					repoName := strings.TrimPrefix(repo.Name, project.Name+"/")
					fullName := project.Name + "/" + repoName
					if prefix == "" || strings.HasPrefix(fullName, prefix) {
						allRepos = append(allRepos, fullName)
					}
				}

				repoPage++
			}
		}

		page++
	}

	return allRepos, nil
}

func (c *HarborClient) ListTags(ctx context.Context, repository string) ([]string, error) {
	return c.generic.ListTags(ctx, repository)
}

func (c *HarborClient) GetImageInfo(ctx context.Context, repository, tag string) (*ImageInfo, error) {
	return c.generic.GetImageInfo(ctx, repository, tag)
}

func (c *HarborClient) GetManifest(ctx context.Context, repository, reference string) (*Manifest, error) {
	return c.generic.GetManifest(ctx, repository, reference)
}

func (c *HarborClient) GetBlob(ctx context.Context, repository, digest string) (io.ReadCloser, int64, error) {
	return c.generic.GetBlob(ctx, repository, digest)
}

func (c *HarborClient) PushManifest(ctx context.Context, repository, reference string, manifest *Manifest) error {
	return c.generic.PushManifest(ctx, repository, reference, manifest)
}

func (c *HarborClient) PushBlob(ctx context.Context, repository, digest string, content io.Reader, size int64) error {
	return c.generic.PushBlob(ctx, repository, digest, content, size)
}

func (c *HarborClient) BlobExists(ctx context.Context, repository, digest string) (bool, error) {
	return c.generic.BlobExists(ctx, repository, digest)
}

func (c *HarborClient) ManifestExists(ctx context.Context, repository, reference string) (bool, error) {
	return c.generic.ManifestExists(ctx, repository, reference)
}

func (c *HarborClient) DeleteTag(ctx context.Context, repository, tag string) error {
	return c.generic.DeleteTag(ctx, repository, tag)
}

func (c *HarborClient) DeleteManifest(ctx context.Context, repository, reference string) error {
	return c.generic.DeleteManifest(ctx, repository, reference)
}
