#!/bin/bash

set -e

echo "=== 服务网格故障注入测试平台部署脚本 ==="

echo ""
echo "1. 创建命名空间..."
kubectl apply -f ../k8s/namespace.yaml

echo ""
echo "2. 部署 Jaeger..."
kubectl apply -f ../k8s/jaeger.yaml

echo ""
echo "3. 创建配置..."
kubectl apply -f ../k8s/configmap.yaml

echo ""
echo "4. 构建后端镜像..."
cd ../backend
docker build -t fault-injection-backend:latest .

echo ""
echo "5. 构建前端镜像..."
cd ../frontend
docker build -t fault-injection-frontend:latest .

echo ""
echo "6. 部署后端服务..."
kubectl apply -f ../k8s/backend-deployment.yaml

echo ""
echo "7. 部署前端服务..."
kubectl apply -f ../k8s/frontend-deployment.yaml

echo ""
echo "8. 部署示例应用（可选）..."
read -p "是否部署示例应用？(y/n): " deploy_sample
if [ "$deploy_sample" = "y" ]; then
    kubectl apply -f ../k8s/sample-app.yaml
fi

echo ""
echo "=== 部署完成！ ==="
echo ""
echo "获取访问地址："
echo "kubectl get service istio-ingressgateway -n istio-system"
echo ""
echo "查看Pod状态："
echo "kubectl get pods -n fault-injection"
echo "kubectl get pods -n observability"
