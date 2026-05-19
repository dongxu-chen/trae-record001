package dns

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/aliyun/alibaba-cloud-sdk-go/services/alidns"
	"github.com/go-acme/lego/v4/challenge/dns01"
	"ssl-manager/internal/config"
)

type Provider interface {
	Present(domain, token, keyAuth string) error
	CleanUp(domain, token, keyAuth string) error
	Timeout() (timeout, interval time.Duration)
}

type AliyunDNSProvider struct {
	client     *alidns.Client
	cfg        config.AliyunDNSConfig
	recordIDs  map[string]string
}

func NewAliyunDNSProvider(cfg config.AliyunDNSConfig) (*AliyunDNSProvider, error) {
	client, err := alidns.NewClientWithAccessKey(cfg.RegionID, cfg.AccessKeyID, cfg.AccessKeySecret)
	if err != nil {
		return nil, fmt.Errorf("create aliyun dns client failed: %w", err)
	}
	return &AliyunDNSProvider{
		client:    client,
		cfg:       cfg,
		recordIDs: make(map[string]string),
	}, nil
}

func (p *AliyunDNSProvider) Present(domain, token, keyAuth string) error {
	fqdn, value := dns01.GetRecord(domain, keyAuth)
	zoneName, recordName := splitDomain(fqdn)
	recordKey := fmt.Sprintf("%s:%s", domain, token)

	request := alidns.CreateAddDomainRecordRequest()
	request.DomainName = zoneName
	request.RR = recordName
	request.Type = "TXT"
	request.Value = value
	request.TTL = "60"

	response, err := p.client.AddDomainRecord(request)
	if err != nil {
		return fmt.Errorf("add dns record failed: %w", err)
	}

	p.recordIDs[recordKey] = response.RecordId
	return nil
}

func (p *AliyunDNSProvider) CleanUp(domain, token, keyAuth string) error {
	recordKey := fmt.Sprintf("%s:%s", domain, token)
	recordID, exists := p.recordIDs[recordKey]
	if !exists {
		return nil
	}

	deleteRequest := alidns.CreateDeleteDomainRecordRequest()
	deleteRequest.RecordId = recordID
	_, err := p.client.DeleteDomainRecord(deleteRequest)
	if err != nil {
		return fmt.Errorf("delete dns record failed: %w", err)
	}

	delete(p.recordIDs, recordKey)
	return nil
}

func (p *AliyunDNSProvider) Timeout() (timeout, interval time.Duration) {
	return 120 * time.Second, 2 * time.Second
}

type CloudflareProvider struct {
	apiKey    string
	email     string
	recordIDs map[string]string
}

func NewCloudflareProvider(cfg config.CloudflareConfig) (*CloudflareProvider, error) {
	return &CloudflareProvider{
		apiKey:    cfg.APIKey,
		email:     cfg.Email,
		recordIDs: make(map[string]string),
	}, nil
}

func (p *CloudflareProvider) Present(domain, token, keyAuth string) error {
	fqdn, value := dns01.GetRecord(domain, keyAuth)
	zoneName, recordName := splitDomain(fqdn)
	recordKey := fmt.Sprintf("%s:%s", domain, token)

	zoneID, err := p.getZoneID(zoneName)
	if err != nil {
		return err
	}

	recordID, err := p.addTXTRecord(zoneID, recordName, value)
	if err != nil {
		return err
	}

	p.recordIDs[recordKey] = recordID
	return nil
}

func (p *CloudflareProvider) CleanUp(domain, token, keyAuth string) error {
	recordKey := fmt.Sprintf("%s:%s", domain, token)
	recordID, exists := p.recordIDs[recordKey]
	if !exists {
		return nil
	}

	fqdn, _ := dns01.GetRecord(domain, keyAuth)
	zoneName, _ := splitDomain(fqdn)

	zoneID, err := p.getZoneID(zoneName)
	if err != nil {
		return err
	}

	if err := p.deleteTXTRecordByID(zoneID, recordID); err != nil {
		return err
	}

	delete(p.recordIDs, recordKey)
	return nil
}

func (p *CloudflareProvider) Timeout() (timeout, interval time.Duration) {
	return 120 * time.Second, 2 * time.Second
}

func (p *CloudflareProvider) getZoneID(domain string) (string, error) {
	url := fmt.Sprintf("https://api.cloudflare.com/client/v4/zones?name=%s", domain)
	headers := map[string]string{
		"X-Auth-Email": p.email,
		"X-Auth-Key":   p.apiKey,
		"Content-Type": "application/json",
	}

	body, err := httpGet(url, headers)
	if err != nil {
		return "", fmt.Errorf("get zone id failed: %w", err)
	}

	var result struct {
		Success bool `json:"success"`
		Result  []struct {
			ID string `json:"id"`
		} `json:"result"`
	}

	if err := json.Unmarshal(body, &result); err != nil {
		return "", fmt.Errorf("parse zone id response failed: %w", err)
	}

	if !result.Success || len(result.Result) == 0 {
		return "", fmt.Errorf("zone not found for domain: %s", domain)
	}

	return result.Result[0].ID, nil
}

func (p *CloudflareProvider) addTXTRecord(zoneID, recordName, value string) (string, error) {
	url := fmt.Sprintf("https://api.cloudflare.com/client/v4/zones/%s/dns_records", zoneID)
	headers := map[string]string{
		"X-Auth-Email": p.email,
		"X-Auth-Key":   p.apiKey,
		"Content-Type": "application/json",
	}

	payload := map[string]interface{}{
		"type":    "TXT",
		"name":    recordName,
		"content": value,
		"ttl":     60,
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return "", fmt.Errorf("marshal payload failed: %w", err)
	}

	respBody, err := httpPost(url, headers, body)
	if err != nil {
		return "", fmt.Errorf("add txt record failed: %w", err)
	}

	var result struct {
		Success bool `json:"success"`
		Result  struct {
			ID string `json:"id"`
		} `json:"result"`
	}

	if err := json.Unmarshal(respBody, &result); err != nil {
		return "", fmt.Errorf("parse response failed: %w", err)
	}

	if !result.Success {
		return "", fmt.Errorf("add txt record failed")
	}

	return result.Result.ID, nil
}

func (p *CloudflareProvider) deleteTXTRecordByID(zoneID, recordID string) error {
	url := fmt.Sprintf("https://api.cloudflare.com/client/v4/zones/%s/dns_records/%s", zoneID, recordID)
	headers := map[string]string{
		"X-Auth-Email": p.email,
		"X-Auth-Key":   p.apiKey,
		"Content-Type": "application/json",
	}

	_, err := httpDelete(url, headers)
	if err != nil {
		return fmt.Errorf("delete txt record by id failed: %w", err)
	}
	return nil
}

func (p *CloudflareProvider) deleteTXTRecord(zoneID, recordName string) error {
	url := fmt.Sprintf("https://api.cloudflare.com/client/v4/zones/%s/dns_records?type=TXT&name=%s", zoneID, recordName)
	headers := map[string]string{
		"X-Auth-Email": p.email,
		"X-Auth-Key":   p.apiKey,
		"Content-Type": "application/json",
	}

	body, err := httpGet(url, headers)
	if err != nil {
		return fmt.Errorf("get txt records failed: %w", err)
	}

	var result struct {
		Success bool `json:"success"`
		Result  []struct {
			ID string `json:"id"`
		} `json:"result"`
	}

	if err := json.Unmarshal(body, &result); err != nil {
		return fmt.Errorf("parse dns records response failed: %w", err)
	}

	for _, record := range result.Result {
		deleteURL := fmt.Sprintf("https://api.cloudflare.com/client/v4/zones/%s/dns_records/%s", zoneID, record.ID)
		_, err := httpDelete(deleteURL, headers)
		if err != nil {
			return fmt.Errorf("delete txt record failed: %w", err)
		}
	}
	return nil
}

func splitDomain(fqdn string) (zoneName, recordName string) {
	parts := dns01.SplitDomain(fqdn)
	return parts[0], parts[1]
}

func NewProvider(cfg *config.DNSConfig) (Provider, error) {
	switch cfg.Provider {
	case "aliyun":
		return NewAliyunDNSProvider(cfg.Aliyun)
	case "cloudflare":
		return NewCloudflareProvider(cfg.Cloudflare)
	default:
		return nil, fmt.Errorf("unsupported dns provider: %s", cfg.Provider)
	}
}
