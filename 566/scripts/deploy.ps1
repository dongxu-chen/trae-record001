Write-Host "=== 服务网格故障注入测试平台部署脚本 ===" -ForegroundColor Cyan

Write-Host ""
Write-Host "1. 创建命名空间..." -ForegroundColor Green
kubectl apply -f ../k8s/namespace.yaml

Write-Host ""
Write-Host "2. 部署 Jaeger..." -ForegroundColor Green
kubectl apply -f ../k8s/jaeger.yaml

Write-Host ""
Write-Host "3. 创建配置..." -ForegroundColor Green
kubectl apply -f ../k8s/configmap.yaml

Write-Host ""
Write-Host "4. 构建后端镜像..." -ForegroundColor Green
Set-Location ../backend
docker build -t fault-injection-backend:latest .

Write-Host ""
Write-Host "5. 构建前端镜像..." -ForegroundColor Green
Set-Location ../frontend
docker build -t fault-injection-frontend:latest .

Write-Host ""
Write-Host "6. 部署后端服务..." -ForegroundColor Green
Set-Location ../scripts
kubectl apply -f ../k8s/backend-deployment.yaml

Write-Host ""
Write-Host "7. 部署前端服务..." -ForegroundColor Green
kubectl apply -f ../k8s/frontend-deployment.yaml

Write-Host ""
Write-Host "8. 部署示例应用（可选）..." -ForegroundColor Green
$deploySample = Read-Host "是否部署示例应用？(y/n)"
if ($deploySample -eq "y") {
    kubectl apply -f ../k8s/sample-app.yaml
}

Write-Host ""
Write-Host "=== 部署完成！ ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "获取访问地址："
Write-Host "kubectl get service istio-ingressgateway -n istio-system"
Write-Host ""
Write-Host "查看Pod状态："
Write-Host "kubectl get pods -n fault-injection"
Write-Host "kubectl get pods -n observability"
