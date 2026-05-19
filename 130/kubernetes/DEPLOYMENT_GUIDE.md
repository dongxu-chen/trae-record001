# Pangeo Cloud-Native Climate Analysis Platform - Deployment Guide

## Overview

This guide walks you through deploying a Pangeo-based cloud-native climate analysis platform on Kubernetes, featuring:

- JupyterHub for interactive notebook-based analysis
- Dask Gateway for scalable parallel computing
- S3-compatible object storage for Zarr data
- Custom climate analysis libraries and tools

## Prerequisites

### Required Tools
```bash
# Kubernetes CLI
curl -LO https://storage.googleapis.com/kubernetes-release/release/`curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt`/bin/linux/amd64/kubectl
chmod +x kubectl && sudo mv kubectl /usr/local/bin/

# Helm 3
curl https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash

# Optional: eksctl for AWS EKS
curl --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
```

### Kubernetes Cluster Requirements
- Kubernetes 1.24+
- Minimum 4 worker nodes
- 8 CPU cores and 32GB RAM minimum per node
- Supported cloud providers: AWS, GCP, Azure, or bare-metal
- StorageClass for persistent volumes (e.g., gp2 on AWS)

## Step 1: Cluster Preparation

### Option A: AWS EKS Setup
```yaml
# eks-cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: pangeo-climate
  region: us-west-2
  version: "1.29"

managedNodeGroups:
  - name: pangeo-workers
    instanceType: m5.2xlarge
    minSize: 4
    maxSize: 20
    volumeSize: 100
    labels:
      role: pangeo
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/node-template/label/role: pangeo
    iam:
      withAddonPolicies:
        autoScaler: true
        cloudWatch: true
```

```bash
# Create the cluster
eksctl create cluster -f eks-cluster.yaml
```

### Option B: GCP GKE Setup
```bash
gcloud container clusters create pangeo-climate \
    --region us-central1 \
    --num-nodes 4 \
    --machine-type n1-standard-8 \
    --disk-size 100 \
    --cluster-version 1.29
```

### Create Required Namespaces
```bash
kubectl create namespace jupyterhub
kubectl create namespace pangeo-dask-workers
kubectl create namespace minio
```

## Step 2: Generate Secrets

```bash
# Generate JupyterHub proxy secret token
openssl rand -hex 32

# Generate Dask Gateway API tokens
openssl rand -hex 32
openssl rand -hex 32
```

## Step 3: Configure and Deploy with Helm

### Update values.yaml
Edit `kubernetes/helm/daskhub/values.yaml` and replace:
1. All `GENERATE_WITH_openssl_rand_hex_32` placeholders with generated tokens
2. AWS SSL certificate ARN (if using HTTPS)
3. Domain/hostnames if applicable

### Add Helm Repositories
```bash
helm repo add jupyterhub https://jupyterhub.github.io/helm-chart/
helm repo add dask https://helm.dask.org/
helm repo update
```

### Deploy DaskHub (JupyterHub + Dask Gateway)
```bash
cd kubernetes/helm/daskhub

# Install dependencies
helm dependency update

# Deploy
helm upgrade --install pangeo-daskhub . \
    --namespace jupyterhub \
    --values values.yaml \
    --timeout 10m0s

# Watch deployment
kubectl get pods -n jupyterhub -w
```

### Deploy MinIO (Optional - for S3-compatible storage)
```bash
helm repo add minio https://charts.min.io/
helm install minio minio/minio \
    --namespace minio \
    --set rootUser=minioadmin \
    --set rootPassword=minioadmin \
    --set persistence.size=1Ti \
    --set service.type=LoadBalancer
```

## Step 4: Build and Push Custom Docker Image

```bash
# Build image
cd docker
docker build -t your-registry/pangeo-climate-notebook:v0.3.0 .

# Push to registry
docker push your-registry/pangeo-climate-notebook:v0.3.0
```

Update `values.yaml` to use your custom image:
```yaml
jupyterhub:
  singleuser:
    image:
      name: your-registry/pangeo-climate-notebook
      tag: v0.3.0
```

## Step 5: Verify Installation

### Check Pod Status
```bash
kubectl get pods -n jupyterhub
kubectl get svc -n jupyterhub
```

### Access JupyterHub
Get the LoadBalancer URL:
```bash
kubectl get svc proxy-public -n jupyterhub -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

Open the URL in your browser and log in with the configured credentials.

## Step 6: S3 Data Configuration

### Using AWS S3
1. Create an S3 bucket for climate data
2. Configure IAM roles for S3 access
3. Update the notebook environment with AWS credentials

### Using MinIO (On-Prem or Alternative)
```python
# Inside a Jupyter notebook
from climate_analysis import create_s3_store

# Connect to MinIO
store = create_s3_store(
    bucket="climate-data",
    endpoint_url="http://minio.minio.svc.cluster.local:9000",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin",
    anon=False
)

# List objects
store.list_objects()
```

## Step 7: Example Workflows

### Example 1: Access CMIP6 Data
```python
from climate_analysis import CMIP6Catalog

# Load the Pangeo CMIP6 catalog
cat = CMIP6Catalog()

# Search for specific data
subset = cat.search(
    experiment_id="historical",
    variable_id="tas",
    source_id="CESM2",
    member_id="r1i1p1f1"
)

# Load into xarray datasets
datasets = cat.to_dataset_dict(subset)
```

### Example 2: Create a Dask Cluster
```python
from climate_analysis import DaskGatewayCluster

# Connect to Dask Gateway
cluster_manager = DaskGatewayCluster()

# Create a new cluster
cluster = cluster_manager.new_cluster(
    worker_cores=4,
    worker_memory="16G",
    worker_count=8,
    autoscale=True
)

# Get client
client = cluster_manager.get_client()
print(f"Dask Dashboard: {client.dashboard_link}")

# Your parallel computation here
# ...

# Cleanup
cluster_manager.stop_cluster()
```

### Example 3: Read Zarr from S3
```python
from climate_analysis import CloudDataStore

# Open Zarr store from S3
store = CloudDataStore(bucket="my-climate-data", anon=True)
ds = store.open_zarr(
    "cmip6/tas_day_CESM2_historical_r1i1p1f1.zarr",
    chunks={"time": 100, "lat": 45, "lon": 90}
)

# Compute spatial mean
tas_mean = ds.tas.mean(dim=["lat", "lon"]).compute()
```

## Step 8: Monitoring and Maintenance

### View Logs
```bash
# JupyterHub logs
kubectl logs -n jupyterhub -l component=hub -f

# Dask Gateway logs
kubectl logs -n jupyterhub -l app.kubernetes.io/name=dask-gateway -f
```

### Scale Worker Nodes
```bash
# EKS
eksctl scale nodegroup --cluster=pangeo-climate --name=pangeo-workers --nodes=10

# kubectl scale (if using cluster-autoscaler)
# Automatically handled based on resource requests
```

### Backup and Upgrade
```bash
# Backup user volumes (example)
kubectl get pvc -n jupyterhub -o yaml > pvc-backup.yaml

# Upgrade deployment
helm dependency update
helm upgrade pangeo-daskhub . -n jupyterhub -f values.yaml
```

## Troubleshooting

### Common Issues

1. **Pods stuck in Pending state**
   - Check resource quotas: `kubectl describe quota -n jupyterhub`
   - Verify node resources: `kubectl describe nodes`

2. **Dask workers not connecting**
   - Check Dask Gateway logs: `kubectl logs -n jupyterhub -l app.kubernetes.io/name=dask-gateway`
   - Verify network policies allow communication

3. **S3 access denied**
   - Verify IAM permissions
   - Check bucket policies and CORS configuration
   - Ensure credentials are correctly set in environment

4. **Image pull errors**
   - Verify image registry accessibility
   - Check image pull secrets if using private registry

### Useful Debug Commands
```bash
# Describe pod events
kubectl describe pod -n jupyterhub <pod-name>

# Exec into a pod
kubectl exec -it -n jupyterhub <pod-name> -- /bin/bash

# Check resource usage
kubectl top pods -n jupyterhub
kubectl top nodes
```

## Performance Optimization

### Recommended Chunk Sizes
For climate data on S3:
- Time series analysis: `{"time": 100, "lat": -1, "lon": -1}`
- Spatial analysis: `{"time": -1, "lat": 90, "lon": 180}`
- Target chunk size: 100MB-200MB

### Dask Configuration
```python
# Optimize for cloud
from dask.distributed import Client

client = Client(
    local_directory="/tmp",
    timeout="60s",
    memory_limit="auto"
)
```

## Security Considerations

1. **Authentication**: Replace DummyAuthenticator with a production solution
   - OAuth2 with GitHub/Google
   - Keycloak or other OIDC provider
   - LDAP integration

2. **Networking**:
   - Use HTTPS with valid SSL certificates
   - Configure network policies
   - Enable private endpoints if possible

3. **Data Access**:
   - Use IAM roles for service accounts (IRSA) on AWS
   - Never hardcode credentials
   - Use Kubernetes secrets for sensitive data

4. **Image Security**:
   - Scan images for vulnerabilities
   - Use private container registry
   - Implement image pull policies

## Cost Optimization

1. **Spot Instances**: Configure worker nodes to use spot instances (70% cost savings)
2. **Autoscaling**: Enable Kubernetes cluster autoscaler and Dask adaptive scaling
3. **Data Locality**: Keep compute in the same region as S3 data
4. **Lifecycle Policies**: Configure S3 lifecycle policies for infrequently accessed data
5. **Volume Sizing**: Don't overprovision storage - most data stays in S3

## Next Steps

1. Set up SSL/TLS with cert-manager
2. Configure user storage and persistence
3. Set up monitoring with Prometheus/Grafana
4. Add authentication and authorization
5. Create custom notebook images for specific use cases
6. Set up CI/CD for image builds and deployment

## Support and Resources

- Pangeo Documentation: https://pangeo.io/
- Dask Gateway: https://gateway.dask.org/
- JupyterHub for Kubernetes: https://z2jh.jupyter.org/
- Dask Documentation: https://docs.dask.org/
- Xarray Documentation: https://docs.xarray.dev/
