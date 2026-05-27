package registry

import (
	"context"
	"encoding/base64"
	"fmt"
	"io"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/ecr"
)

type ECRClient struct {
	region      string
	accessKey   string
	secretKey   string
	accountID   string
	httpClient  *ecr.Client
	generic     *GenericRegistryClient
	registryURL string
	authToken   string
	tokenExpiry time.Time
}

func NewECRClient(accessKey, secretKey, region, accountID string, insecure bool) (*ECRClient, error) {
	cfg, err := config.LoadDefaultConfig(context.TODO(),
		config.WithRegion(region),
		config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider(accessKey, secretKey, "")),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}

	registryURL := fmt.Sprintf("%s.dkr.ecr.%s.amazonaws.com", accountID, region)

	return &ECRClient{
		region:      region,
		accessKey:   accessKey,
		secretKey:   secretKey,
		accountID:   accountID,
		httpClient:  ecr.NewFromConfig(cfg),
		registryURL: "https://" + registryURL,
	}, nil
}

func (c *ECRClient) getAuthToken(ctx context.Context) (string, error) {
	if time.Now().Before(c.tokenExpiry) && c.authToken != "" {
		return c.authToken, nil
	}

	input := &ecr.GetAuthorizationTokenInput{
		RegistryIds: []string{c.accountID},
	}

	output, err := c.httpClient.GetAuthorizationToken(ctx, input)
	if err != nil {
		return "", fmt.Errorf("failed to get ECR authorization token: %w", err)
	}

	if len(output.AuthorizationData) == 0 {
		return "", fmt.Errorf("no authorization data received")
	}

	authData := output.AuthorizationData[0]
	c.authToken = *authData.AuthorizationToken
	c.tokenExpiry = *authData.ExpiresAt

	return c.authToken, nil
}

func (c *ECRClient) getGenericClient(ctx context.Context) (*GenericRegistryClient, error) {
	if c.generic != nil && time.Now().Before(c.tokenExpiry) {
		return c.generic, nil
	}

	token, err := c.getAuthToken(ctx)
	if err != nil {
		return nil, err
	}

	decodedToken, err := base64.StdEncoding.DecodeString(token)
	if err != nil {
		return nil, err
	}

	parts := strings.SplitN(string(decodedToken), ":", 2)
	if len(parts) != 2 {
		return nil, fmt.Errorf("invalid authorization token format")
	}

	username := parts[0]
	password := parts[1]

	generic, err := NewGenericRegistryClient(c.registryURL, username, password, false)
	if err != nil {
		return nil, err
	}

	c.generic = generic
	return c.generic, nil
}

func (c *ECRClient) ListRepositories(ctx context.Context, prefix string) ([]string, error) {
	var allRepos []string
	nextToken := ""

	for {
		input := &ecr.DescribeRepositoriesInput{
			RegistryId:      aws.String(c.accountID),
			MaxResults:      aws.Int32(100),
		}
		if nextToken != "" {
			input.NextToken = aws.String(nextToken)
		}

		output, err := c.httpClient.DescribeRepositories(ctx, input)
		if err != nil {
			return nil, fmt.Errorf("failed to describe repositories: %w", err)
		}

		for _, repo := range output.Repositories {
			repoName := *repo.RepositoryName
			if prefix == "" || strings.HasPrefix(repoName, prefix) {
				allRepos = append(allRepos, repoName)
			}
		}

		if output.NextToken == nil {
			break
		}
		nextToken = *output.NextToken
	}

	return allRepos, nil
}

func (c *ECRClient) ListTags(ctx context.Context, repository string) ([]string, error) {
	generic, err := c.getGenericClient(ctx)
	if err != nil {
		return nil, err
	}
	return generic.ListTags(ctx, repository)
}

func (c *ECRClient) GetImageInfo(ctx context.Context, repository, tag string) (*ImageInfo, error) {
	generic, err := c.getGenericClient(ctx)
	if err != nil {
		return nil, err
	}
	return generic.GetImageInfo(ctx, repository, tag)
}

func (c *ECRClient) GetManifest(ctx context.Context, repository, reference string) (*Manifest, error) {
	generic, err := c.getGenericClient(ctx)
	if err != nil {
		return nil, err
	}
	return generic.GetManifest(ctx, repository, reference)
}

func (c *ECRClient) GetBlob(ctx context.Context, repository, digest string) (io.ReadCloser, int64, error) {
	generic, err := c.getGenericClient(ctx)
	if err != nil {
		return nil, 0, err
	}
	return generic.GetBlob(ctx, repository, digest)
}

func (c *ECRClient) PushManifest(ctx context.Context, repository, reference string, manifest *Manifest) error {
	generic, err := c.getGenericClient(ctx)
	if err != nil {
		return err
	}
	return generic.PushManifest(ctx, repository, reference, manifest)
}

func (c *ECRClient) PushBlob(ctx context.Context, repository, digest string, content io.Reader, size int64) error {
	generic, err := c.getGenericClient(ctx)
	if err != nil {
		return err
	}
	return generic.PushBlob(ctx, repository, digest, content, size)
}

func (c *ECRClient) BlobExists(ctx context.Context, repository, digest string) (bool, error) {
	generic, err := c.getGenericClient(ctx)
	if err != nil {
		return false, err
	}
	return generic.BlobExists(ctx, repository, digest)
}

func (c *ECRClient) ManifestExists(ctx context.Context, repository, reference string) (bool, error) {
	generic, err := c.getGenericClient(ctx)
	if err != nil {
		return false, err
	}
	return generic.ManifestExists(ctx, repository, reference)
}

func (c *ECRClient) DeleteTag(ctx context.Context, repository, tag string) error {
	generic, err := c.getGenericClient(ctx)
	if err != nil {
		return err
	}
	return generic.DeleteTag(ctx, repository, tag)
}

func (c *ECRClient) DeleteManifest(ctx context.Context, repository, reference string) error {
	generic, err := c.getGenericClient(ctx)
	if err != nil {
		return err
	}
	return generic.DeleteManifest(ctx, repository, reference)
}
