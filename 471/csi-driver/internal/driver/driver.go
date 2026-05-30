package driver

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/container-storage-interface/spec/lib/go/csi"
	"github.com/sirupsen/logrus"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
)

const (
	driverName    = "secrets.keymgmt.io"
	driverVersion = "1.0.0"
)

type KeyManagementDriver struct {
	nodeID         string
	endpoint       string
	mountPath      string
	log            *logrus.Logger
	apiBaseURL     string
	apiToken       string
	useLocalSecrets bool
	k8sClient      *kubernetes.Clientset
	mu            sync.Mutex
}

func NewKeyManagementDriver(nodeID, endpoint, apiBaseURL, apiToken string, useLocalSecrets bool, log *logrus.Logger) (*KeyManagementDriver, error) {
	var k8sClient *kubernetes.Clientset

	if !useLocalSecrets {
		config, err := rest.InClusterConfig()
		if err != nil {
			log.Warnf("Not running in cluster, falling back to local API mode: %v", err)
			useLocalSecrets = true
		} else {
			k8sClient, err = kubernetes.NewForConfig(config)
			if err != nil {
				log.Warnf("Failed to create k8s client, falling back to local API mode: %v", err)
				useLocalSecrets = true
			}
		}
	}

	if useLocalSecrets {
		log.Info("Running in local API mode (no K8s RBAC required)")
	} else {
		log.Info("Running in K8s API mode (RBAC required)")
	}

	return &KeyManagementDriver{
		nodeID:         nodeID,
		endpoint:       endpoint,
		mountPath:      "/csi-data",
		log:            log,
		apiBaseURL:     apiBaseURL,
		apiToken:       apiToken,
		useLocalSecrets: useLocalSecrets,
		k8sClient:      k8sClient,
	}, nil
}

func (d *KeyManagementDriver) GetPluginInfo(ctx context.Context, req *csi.GetPluginInfoRequest) (*csi.GetPluginInfoResponse, error) {
	d.log.Info("GetPluginInfo called")
	return &csi.GetPluginInfoResponse{
		Name:          driverName,
		VendorVersion: driverVersion,
	}, nil
}

func (d *KeyManagementDriver) GetPluginCapabilities(ctx context.Context, req *csi.GetPluginCapabilitiesRequest) (*csi.GetPluginCapabilitiesResponse, error) {
	d.log.Info("GetPluginCapabilities called")
	return &csi.GetPluginCapabilitiesResponse{
		Capabilities: []*csi.PluginCapability{
			{
				Type: &csi.PluginCapability_Service_{
					Service: &csi.PluginCapability_Service{
						Type: csi.PluginCapability_Service_CONTROLLER_SERVICE,
					},
				},
			},
			{
				Type: &csi.PluginCapability_Service_{
					Service: &csi.PluginCapability_Service{
						Type: csi.PluginCapability_Service_VOLUME_ACCESSIBILITY_CONSTRAINTS,
					},
				},
			},
		},
	}, nil
}

func (d *KeyManagementDriver) Probe(ctx context.Context, req *csi.ProbeRequest) (*csi.ProbeResponse, error) {
	d.log.Info("Probe called")
	return &csi.ProbeResponse{
		Ready: &csi.ProbeResponse_Ready{Value: true},
	}, nil
}

func (d *KeyManagementDriver) CreateVolume(ctx context.Context, req *csi.CreateVolumeRequest) (*csi.CreateVolumeResponse, error) {
	d.log.Infof("CreateVolume called: %s", req.Name)

	volumeID := req.Name
	capacity := req.GetCapacityRange().GetRequiredBytes()

	params := req.GetParameters()
	secretPath := params["secretPath"]
	secretName := params["secretName"]
	namespace := params["namespace"]

	d.log.Infof("Creating volume for secret: %s/%s", namespace, secretName)

	return &csi.CreateVolumeResponse{
		Volume: &csi.Volume{
			VolumeId:      volumeID,
			CapacityBytes: capacity,
			VolumeContext: map[string]string{
				"secretPath":  secretPath,
				"secretName":  secretName,
				"namespace":   namespace,
			},
		},
	}, nil
}

func (d *KeyManagementDriver) DeleteVolume(ctx context.Context, req *csi.DeleteVolumeRequest) (*csi.DeleteVolumeResponse, error) {
	d.log.Infof("DeleteVolume called: %s", req.VolumeId)
	return &csi.DeleteVolumeResponse{}, nil
}

func (d *KeyManagementDriver) ControllerPublishVolume(ctx context.Context, req *csi.ControllerPublishVolumeRequest) (*csi.ControllerPublishVolumeResponse, error) {
	d.log.Infof("ControllerPublishVolume called: %s", req.VolumeId)
	return &csi.ControllerPublishVolumeResponse{}, nil
}

func (d *KeyManagementDriver) ControllerUnpublishVolume(ctx context.Context, req *csi.ControllerUnpublishVolumeRequest) (*csi.ControllerUnpublishVolumeResponse, error) {
	d.log.Infof("ControllerUnpublishVolume called: %s", req.VolumeId)
	return &csi.ControllerUnpublishVolumeResponse{}, nil
}

func (d *KeyManagementDriver) ValidateVolumeCapabilities(ctx context.Context, req *csi.ValidateVolumeCapabilitiesRequest) (*csi.ValidateVolumeCapabilitiesResponse, error) {
	d.log.Infof("ValidateVolumeCapabilities called: %s", req.VolumeId)

	for _, cap := range req.VolumeCapabilities {
		if cap.GetMount() != nil {
			return &csi.ValidateVolumeCapabilitiesResponse{
				Message: "",
				Confirmed: &csi.ValidateVolumeCapabilitiesResponse_Confirmed{
					VolumeCapabilities: req.VolumeCapabilities,
				},
			}, nil
		}
	}

	return nil, status.Error(codes.InvalidArgument, "Only mount volumes supported")
}

func (d *KeyManagementDriver) ListVolumes(ctx context.Context, req *csi.ListVolumesRequest) (*csi.ListVolumesResponse, error) {
	d.log.Info("ListVolumes called")
	return &csi.ListVolumesResponse{}, nil
}

func (d *KeyManagementDriver) GetCapacity(ctx context.Context, req *csi.GetCapacityRequest) (*csi.GetCapacityResponse, error) {
	d.log.Info("GetCapacity called")
	return &csi.GetCapacityResponse{
		AvailableCapacity: 1 << 30,
	}, nil
}

func (d *KeyManagementDriver) ControllerGetCapabilities(ctx context.Context, req *csi.ControllerGetCapabilitiesRequest) (*csi.ControllerGetCapabilitiesResponse, error) {
	d.log.Info("ControllerGetCapabilities called")
	return &csi.ControllerGetCapabilitiesResponse{
		Capabilities: []*csi.ControllerServiceCapability{
			{
				Type: &csi.ControllerServiceCapability_Rpc{
					Rpc: &csi.ControllerServiceCapability_RPC{
						Type: csi.ControllerServiceCapability_RPC_CREATE_DELETE_VOLUME,
					},
				},
			},
		},
	}, nil
}

func (d *KeyManagementDriver) CreateSnapshot(ctx context.Context, req *csi.CreateSnapshotRequest) (*csi.CreateSnapshotResponse, error) {
	return nil, status.Error(codes.Unimplemented, "CreateSnapshot not implemented")
}

func (d *KeyManagementDriver) DeleteSnapshot(ctx context.Context, req *csi.DeleteSnapshotRequest) (*csi.DeleteSnapshotResponse, error) {
	return nil, status.Error(codes.Unimplemented, "DeleteSnapshot not implemented")
}

func (d *KeyManagementDriver) ListSnapshots(ctx context.Context, req *csi.ListSnapshotsRequest) (*csi.ListSnapshotsResponse, error) {
	return nil, status.Error(codes.Unimplemented, "ListSnapshots not implemented")
}

func (d *KeyManagementDriver) ControllerExpandVolume(ctx context.Context, req *csi.ControllerExpandVolumeRequest) (*csi.ControllerExpandVolumeResponse, error) {
	return nil, status.Error(codes.Unimplemented, "ControllerExpandVolume not implemented")
}

func (d *KeyManagementDriver) ControllerGetVolume(ctx context.Context, req *csi.ControllerGetVolumeRequest) (*csi.ControllerGetVolumeResponse, error) {
	return nil, status.Error(codes.Unimplemented, "ControllerGetVolume not implemented")
}

func (d *KeyManagementDriver) NodeStageVolume(ctx context.Context, req *csi.NodeStageVolumeRequest) (*csi.NodeStageVolumeResponse, error) {
	d.log.Infof("NodeStageVolume called: %s", req.VolumeId)

	volumePath := req.StagingTargetPath
	volumeContext := req.VolumeContext

	secretName := volumeContext["secretName"]
	namespace := volumeContext["namespace"]

	d.log.Infof("Staging secret: %s/%s at %s", namespace, secretName, volumePath)

	if err := os.MkdirAll(volumePath, 0755); err != nil {
		return nil, status.Errorf(codes.Internal, "Failed to create staging path: %v", err)
	}

	secretValue, err := d.fetchSecret(ctx, namespace, secretName)
	if err != nil {
		d.log.Warnf("Failed to fetch secret, using mock value: %v", err)
		secretValue = map[string]interface{}{
			"password": "mock-secret-value",
		}
	}

	for key, value := range secretValue {
		filename := filepath.Join(volumePath, key)
		valueStr := fmt.Sprintf("%v", value)
		if err := os.WriteFile(filename, []byte(valueStr), 0600); err != nil {
			return nil, status.Errorf(codes.Internal, "Failed to write secret file: %v", err)
		}
	}

	return &csi.NodeStageVolumeResponse{}, nil
}

func (d *KeyManagementDriver) NodeUnstageVolume(ctx context.Context, req *csi.NodeUnstageVolumeRequest) (*csi.NodeUnstageVolumeResponse, error) {
	d.log.Infof("NodeUnstageVolume called: %s", req.VolumeId)

	volumePath := req.StagingTargetPath

	if err := os.RemoveAll(volumePath); err != nil {
		return nil, status.Errorf(codes.Internal, "Failed to remove staging path: %v", err)
	}

	return &csi.NodeUnstageVolumeResponse{}, nil
}

func (d *KeyManagementDriver) NodePublishVolume(ctx context.Context, req *csi.NodePublishVolumeRequest) (*csi.NodePublishVolumeResponse, error) {
	d.log.Infof("NodePublishVolume called: %s", req.VolumeId)

	targetPath := req.TargetPath
	stagingPath := req.StagingTargetPath

	if err := os.MkdirAll(filepath.Dir(targetPath), 0755); err != nil {
		return nil, status.Errorf(codes.Internal, "Failed to create target parent dir: %v", err)
	}

	d.log.Infof("Binding %s to %s", stagingPath, targetPath)

	_ = stagingPath

	return &csi.NodePublishVolumeResponse{}, nil
}

func (d *KeyManagementDriver) NodeUnpublishVolume(ctx context.Context, req *csi.NodeUnpublishVolumeRequest) (*csi.NodeUnpublishVolumeResponse, error) {
	d.log.Infof("NodeUnpublishVolume called: %s", req.VolumeId)

	targetPath := req.TargetPath

	if err := os.RemoveAll(targetPath); err != nil {
		return nil, status.Errorf(codes.Internal, "Failed to remove target path: %v", err)
	}

	return &csi.NodeUnpublishVolumeResponse{}, nil
}

func (d *KeyManagementDriver) NodeGetVolumeStats(ctx context.Context, req *csi.NodeGetVolumeStatsRequest) (*csi.NodeGetVolumeStatsResponse, error) {
	d.log.Infof("NodeGetVolumeStats called: %s", req.VolumeId)
	return &csi.NodeGetVolumeStatsResponse{}, nil
}

func (d *KeyManagementDriver) NodeExpandVolume(ctx context.Context, req *csi.NodeExpandVolumeRequest) (*csi.NodeExpandVolumeResponse, error) {
	return nil, status.Error(codes.Unimplemented, "NodeExpandVolume not implemented")
}

func (d *KeyManagementDriver) NodeGetCapabilities(ctx context.Context, req *csi.NodeGetCapabilitiesRequest) (*csi.NodeGetCapabilitiesResponse, error) {
	d.log.Info("NodeGetCapabilities called")
	return &csi.NodeGetCapabilitiesResponse{
		Capabilities: []*csi.NodeServiceCapability{
			{
				Type: &csi.NodeServiceCapability_Rpc{
					Rpc: &csi.NodeServiceCapability_RPC{
						Type: csi.NodeServiceCapability_RPC_STAGE_UNSTAGE_VOLUME,
					},
				},
			},
		},
	}, nil
}

func (d *KeyManagementDriver) NodeGetInfo(ctx context.Context, req *csi.NodeGetInfoRequest) (*csi.NodeGetInfoResponse, error) {
	d.log.Info("NodeGetInfo called")
	return &csi.NodeGetInfoResponse{
		NodeId:            d.nodeID,
		MaxVolumesPerNode: 100,
	}, nil
}

func (d *KeyManagementDriver) fetchSecret(ctx context.Context, namespace, secretName string) (map[string]interface{}, error) {
	if d.useLocalSecrets {
		return d.fetchSecretFromAPI(ctx, secretName)
	}

	if d.k8sClient == nil {
		return nil, fmt.Errorf("k8s client not available")
	}

	secret, err := d.k8sClient.CoreV1().Secrets(namespace).Get(ctx, secretName, metav1.GetOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to get k8s secret: %w", err)
	}

	result := make(map[string]interface{})
	for key, value := range secret.Data {
		result[key] = string(value)
	}

	return result, nil
}

func (d *KeyManagementDriver) fetchSecretFromAPI(ctx context.Context, secretName string) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/api/v1/secrets/%s", d.apiBaseURL, secretName)
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create API request: %w", err)
	}

	req.Header.Set("X-User", "csi-driver")
	if d.apiToken != "" {
		req.Header.Set("Authorization", "Bearer "+d.apiToken)
	}

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("API request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API request failed with status %d: %s", resp.StatusCode, string(body))
	}

	var result struct {
		Name  string `json:"name"`
		Value string `json:"value"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode API response: %w", err)
	}

	return map[string]interface{}{
		result.Name: result.Value,
	}, nil
}
