#!/bin/bash
# 生成TLS证书用于Admission Webhook

set -e

SERVICE_NAME="trivy-admission-scanner"
NAMESPACE="trivy-admission-system"
SECRET_NAME="trivy-admission-tls"
OUTPUT_DIR="./certs"

mkdir -p ${OUTPUT_DIR}

echo "生成CA证书..."
openssl genrsa -out ${OUTPUT_DIR}/ca.key 2048
openssl req -new -x509 -days 365 -key ${OUTPUT_DIR}/ca.key \
    -out ${OUTPUT_DIR}/ca.crt \
    -subj "/CN=ca.trivy.io"

echo "生成服务器证书..."
openssl genrsa -out ${OUTPUT_DIR}/tls.key 2048
openssl req -new -key ${OUTPUT_DIR}/tls.key \
    -out ${OUTPUT_DIR}/tls.csr \
    -subj "/CN=${SERVICE_NAME}.${NAMESPACE}.svc" \
    -config <(cat <<-EOF
[req]
distinguished_name = dn
[dn]
[ext]
subjectAltName = DNS:${SERVICE_NAME},DNS:${SERVICE_NAME}.${NAMESPACE},DNS:${SERVICE_NAME}.${NAMESPACE}.svc
EOF
)

openssl x509 -req -in ${OUTPUT_DIR}/tls.csr \
    -CA ${OUTPUT_DIR}/ca.crt \
    -CAkey ${OUTPUT_DIR}/ca.key \
    -CAcreateserial \
    -out ${OUTPUT_DIR}/tls.crt \
    -days 365 \
    -extensions ext \
    -extfile <(cat <<-EOF
[ext]
subjectAltName = DNS:${SERVICE_NAME},DNS:${SERVICE_NAME}.${NAMESPACE},DNS:${SERVICE_NAME}.${NAMESPACE}.svc
EOF
)

echo "创建Kubernetes Secret..."
kubectl create secret tls ${SECRET_NAME} \
    --cert=${OUTPUT_DIR}/tls.crt \
    --key=${OUTPUT_DIR}/tls.key \
    --namespace=${NAMESPACE} \
    --dry-run=client -o yaml | kubectl apply -f -

echo "提取CA Bundle..."
CA_BUNDLE=$(cat ${OUTPUT_DIR}/ca.crt | base64 -w0)
echo "CA_BUNDLE=${CA_BUNDLE}" > ${OUTPUT_DIR}/ca_bundle.env

echo ""
echo "证书生成完成！"
echo "CA证书: ${OUTPUT_DIR}/ca.crt"
echo "服务器证书: ${OUTPUT_DIR}/tls.crt"
echo "服务器密钥: ${OUTPUT_DIR}/tls.key"
echo "CA Bundle已保存到: ${OUTPUT_DIR}/ca_bundle.env"
echo ""
echo "使用以下命令更新webhook配置:"
echo "export CA_BUNDLE=${CA_BUNDLE}"
echo "envsubst < deploy/validating_webhook.yaml | kubectl apply -f -"
