package nacos

import (
	"fmt"
	"log"
	"strings"

	"github.com/nacos-group/nacos-sdk-go/v2/clients"
	"github.com/nacos-group/nacos-sdk-go/v2/clients/config_client"
	"github.com/nacos-group/nacos-sdk-go/v2/clients/naming_client"
	"github.com/nacos-group/nacos-sdk-go/v2/common/constant"
	"github.com/nacos-group/nacos-sdk-go/v2/model"
	"github.com/nacos-group/nacos-sdk-go/v2/vo"
)

type NacosClient struct {
	configClient config_client.IConfigClient
	namingClient naming_client.INamingClient
	host         string
	port         uint64
	username     string
	password     string
}

func NewNacosClient(host string, port uint64, username, password string) (*NacosClient, error) {
	sc := []constant.ServerConfig{
		*constant.NewServerConfig(host, port, constant.WithScheme("http")),
	}

	cc := constant.ClientConfig{
		Username:      username,
		Password:      password,
		TimeoutMs:     5000,
		LogLevel:      "error",
		CacheDir:      "./nacos_cache",
		LogDir:        "./nacos_logs",
	}

	configClient, err := clients.CreateConfigClient(map[string]interface{}{
		"serverConfigs": sc,
		"clientConfig":  cc,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create config client: %v", err)
	}

	namingClient, err := clients.CreateNamingClient(map[string]interface{}{
		"serverConfigs": sc,
		"clientConfig":  cc,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create naming client: %v", err)
	}

	return &NacosClient{
		configClient: configClient,
		namingClient: namingClient,
		host:         host,
		port:         port,
		username:     username,
		password:     password,
	}, nil
}

func (c *NacosClient) GetConfig(namespaceID, group, dataID string) (string, string, error) {
	content, err := c.configClient.GetConfig(vo.ConfigParam{
		DataId:      dataID,
		Group:       group,
		Tenant:      namespaceID,
	})
	if err != nil {
		return "", "", err
	}

	contentType := "text"
	if strings.HasSuffix(dataID, ".yaml") || strings.HasSuffix(dataID, ".yml") {
		contentType = "yaml"
	} else if strings.HasSuffix(dataID, ".json") {
		contentType = "json"
	} else if strings.HasSuffix(dataID, ".properties") {
		contentType = "properties"
	} else if strings.HasSuffix(dataID, ".xml") {
		contentType = "xml"
	}

	return content, contentType, nil
}

func (c *NacosClient) PublishConfig(namespaceID, group, dataID, content, operator string) error {
	_, err := c.configClient.PublishConfig(vo.ConfigParam{
		DataId:      dataID,
		Group:       group,
		Tenant:      namespaceID,
		Content:     content,
	})
	return err
}

func (c *NacosClient) DeleteConfig(namespaceID, group, dataID string) error {
	_, err := c.configClient.DeleteConfig(vo.ConfigParam{
		DataId:  dataID,
		Group:   group,
		Tenant:  namespaceID,
	})
	return err
}

func (c *NacosClient) ListenConfig(namespaceID, group, dataID string, callback func(namespaceID, group, dataID, content string)) error {
	return c.configClient.ListenConfig(vo.ConfigParam{
		DataId: dataID,
		Group:  group,
		Tenant: namespaceID,
		OnChange: func(namespace, group, dataId, data string) {
			callback(namespace, group, dataId, data)
		},
	})
}

func (c *NacosClient) CancelListenConfig(namespaceID, group, dataID string) error {
	return c.configClient.CancelListenConfig(vo.ConfigParam{
		DataId: dataID,
		Group:  group,
		Tenant: namespaceID,
	})
}

func (c *NacosClient) GetNamespaces() ([]model.Namespace, error) {
	return c.namingClient.GetAllNamespaces()
}

type ConfigInfo struct {
	TotalCount     int
	PageNumber     int
	PagesAvailable int
	PageItems      []ConfigItem
}

type ConfigItem struct {
	ID         string
	DataID     string
	Group      string
	Content    string
	MD5        string
	CreateTime int64
	ModifyTime int64
	AppName    string
	Desc       string
	Use        string
	Effect     string
	Type       string
	Schema     string
}

func (c *NacosClient) GetConfigs(namespaceID, group string, pageNo, pageSize int) (*ConfigInfo, error) {
	result := &ConfigInfo{}
	log.Printf("GetConfigs called with namespaceID: %s, group: %s, pageNo: %d, pageSize: %d", namespaceID, group, pageNo, pageSize)
	return result, nil
}

func (c *NacosClient) SearchConfig(namespaceID, search string, pageNo, pageSize int) (*ConfigInfo, error) {
	result := &ConfigInfo{}
	log.Printf("SearchConfig called with namespaceID: %s, search: %s, pageNo: %d, pageSize: %d", namespaceID, search, pageNo, pageSize)
	return result, nil
}
