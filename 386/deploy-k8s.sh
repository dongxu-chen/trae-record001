#!/bin/bash

set -e

NAMESPACE="gray-release"

echo "============================================"
echo "  Gray Release Platform - K8s Deployment"
echo "============================================"

echo "[1/5] Creating namespace..."
kubectl apply -f k8s/namespace.yaml

echo "[2/5] Deploying Kafka..."
kubectl apply -f k8s/kafka.yaml -n $NAMESPACE

echo "[3/5] Deploying Prometheus..."
kubectl apply -f k8s/prometheus.yaml -n $NAMESPACE

echo "Waiting for infrastructure..."
kubectl wait --for=condition=available deployment/kafka -n $NAMESPACE --timeout=120s
kubectl wait --for=condition=available deployment/prometheus -n $NAMESPACE --timeout=120s

echo "[4/5] Deploying Release Service..."
kubectl apply -f k8s/release-service.yaml -n $NAMESPACE

echo "[5/5] Deploying Gateway Service..."
kubectl apply -f k8s/gateway-service.yaml -n $NAMESPACE
kubectl apply -f k8s/monitor-service.yaml -n $NAMESPACE

echo ""
echo "============================================"
echo "  Deployment Complete!"
echo "============================================"

kubectl get pods -n $NAMESPACE
kubectl get svc -n $NAMESPACE