package registry

import (
	"fmt"
	"registry-sync/pkg/config"
)

func NewClient(regConfig *config.RegistryConfig) (RegistryClient, error) {
	switch regConfig.Type {
	case config.RegistryTypeHarbor:
		return NewHarborClient(regConfig.URL, regConfig.Username, regConfig.Password, regConfig.Insecure)
	case config.RegistryTypeACR:
		return NewACRClient(regConfig.URL, regConfig.AccessKey, regConfig.SecretKey, regConfig.Region, regConfig.Insecure)
	case config.RegistryTypeECR:
		return NewECRClient(regConfig.AccessKey, regConfig.SecretKey, regConfig.Region, regConfig.Username, regConfig.Insecure)
	case config.RegistryTypeGeneric:
		return NewGenericRegistryClient(regConfig.URL, regConfig.Username, regConfig.Password, regConfig.Insecure)
	default:
		return nil, fmt.Errorf("unsupported registry type: %s", regConfig.Type)
	}
}
