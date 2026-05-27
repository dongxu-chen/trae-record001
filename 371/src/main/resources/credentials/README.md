# SSO Server Credentials

此目录用于存放 SSO 服务器的密钥和证书文件。

## 安全警告

⚠️ **重要提示**:
- 请勿将真实密钥文件提交到版本控制系统
- 生产环境的密钥和密码必须严格保密
- 建议使用密钥管理服务 (KMS) 管理生产环境密钥

## 需要的文件

### 1. OAuth2 JWT 密钥库
- **文件名**: `oauth2.jks`
- **格式**: JKS (Java KeyStore)
- **用途**: 签名和验证 OAuth2 JWT 令牌

生成命令:
```bash
keytool -genkeypair -alias oauth2-key -keyalg RSA -keysize 2048 \
  -keystore oauth2.jks \
  -storepass changeit -keypass changeit \
  -dname "CN=SSO Server, OU=IT, O=Company, L=City, ST=State, C=CN"
```

导出公钥:
```bash
keytool -export -alias oauth2-key -keystore oauth2.jks -rfc -file oauth2.crt
```

### 2. SAML2 签名密钥对
- **私钥文件名**: `saml-signing.key`
- **证书文件名**: `saml-signing.crt`
- **格式**: PEM 格式
- **用途**: 签名 SAML2 响应和断言

生成命令:
```bash
# 生成 2048 位 RSA 私钥
openssl genrsa -out saml-signing.key 2048

# 生成自签名证书 (有效期 10 年)
openssl req -new -x509 -key saml-signing.key \
  -out saml-signing.crt -days 3650 \
  -subj "/C=CN/ST=State/L=City/O=Company/OU=IT/CN=sso.example.com"
```

### 3. SAML2 加密密钥对
- **私钥文件名**: `saml-encryption.key`
- **证书文件名**: `saml-encryption.crt`
- **格式**: PEM 格式
- **用途**: 加密 SAML2 断言 (可选)

生成命令 (同上，换文件名):
```bash
openssl genrsa -out saml-encryption.key 2048
openssl req -new -x509 -key saml-encryption.key \
  -out saml-encryption.crt -days 3650 \
  -subj "/C=CN/ST=State/L=City/O=Company/OU=IT/CN=sso.example.com"
```

## 文件说明

| 文件 | 说明 | 是否必须 |
|------|------|----------|
| `oauth2.jks` | OAuth2 JWT 签名密钥库 | 是 |
| `saml-signing.key` | SAML2 签名私钥 | 是 (启用 SAML2 时) |
| `saml-signing.crt` | SAML2 签名证书 | 是 (启用 SAML2 时) |
| `saml-encryption.key` | SAML2 加密私钥 | 否 |
| `saml-encryption.crt` | SAML2 加密证书 | 否 |

## 密钥轮换建议

### 密钥轮换步骤

1. **生成新密钥**: 创建新的密钥对，保留旧密钥
2. **双密钥发布**: 在 JWKS 端点同时发布新旧密钥
3. **客户端更新**: 通知所有客户端更新配置
4. **停用旧密钥**: 所有客户端更新完成后，移除旧密钥
5. **验证**: 确认所有系统正常工作

### 轮换周期建议
- OAuth2 JWT 密钥: 每 6 个月
- SAML2 签名密钥: 每 1 年
- SAML2 加密密钥: 每 1 年

## 开发环境说明

为了方便开发和测试，你可以生成测试用的自签名证书。
但在生产环境中，**必须**使用由受信任的证书颁发机构 (CA) 签发的证书。

## 故障排除

### 密钥库密码错误
检查 `application.yml` 中的密码配置:
```yaml
sso:
  oauth2:
    jks-password: your_password
    key-password: your_key_password
```

### SAML2 签名验证失败
1. 确认 SP 端导入了正确的签名证书
2. 检查系统时间是否同步 (SAML 对时间敏感)
3. 验证 EntityID 是否匹配

### JWT 签名验证失败
1. 确认资源服务器可以访问 JWKS 端点
2. 检查 JWT 的 `iss` (issuer) 声明是否匹配
3. 验证系统时间是否同步
