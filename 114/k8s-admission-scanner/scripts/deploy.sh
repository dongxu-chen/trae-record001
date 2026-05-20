#!/bin/bash
# 一键部署Trivy Admission Scanner

set -e

echo "=============================================="
echo "  Trivy Admission Scanner 一键部署脚本"
echo "=============================================="

# 1. 检查kubectl
echo "[1/6] 检查kubectl..."
if ! command -v kubectl &> /dev/null; then
    echo "错误: 未找到kubectl命令"
    exit 1
fi

# 2. 创建命名空间
echo ""
echo "[2/6] 创建命名空间..."
kubectl apply -f deploy/namespace.yaml

# 3. 生成证书
echo ""
echo "[3/6] 生成TLS证书..."
if [ ! -d "certs" ]; then
    chmod +x scripts/gen_certs.sh
    ./scripts/gen_certs.sh
else
    echo "证书已存在，跳过生成"
    source certs/ca_bundle.env
fi

# 4. 部署基础资源
echo ""
echo "[4/6] 部署基础资源..."
kubectl apply -f deploy/service_account.yaml
kubectl apply -f deploy/role.yaml
kubectl apply -f deploy/role_binding.yaml
kubectl apply -f deploy/service.yaml
kubectl apply -f crds/imagescanpolicy.yaml
kubectl apply -f crds/default-policy.yaml

# 5. 部署Webhook
echo ""
echo "[5/6] 部署ValidatingWebhook..."
envsubst < deploy/validating_webhook.yaml | kubectl apply -f -

# 6. 部署Operator
echo ""
echo "[6/6] 部署Operator..."
kubectl apply -f deploy/deployment.yaml

echo ""
echo "=============================================="
echo "  部署完成！"
echo "=============================================="
echo ""
echo "检查状态:"
echo "  kubectl get pods -n trivy-admission-system"
echo "  kubectl get svc -n trivy-admission-system"
echo "  kubectl get imagescanpolicies"
echo ""
echo "注意: 请确保已修改deployment.yaml中的镜像地址为你的镜像仓库地址"
