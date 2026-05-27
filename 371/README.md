# 企业级单点登录系统 (SSO Server)

基于 Spring Security + OAuth2 + SAML2 + CAS + LDAP + Redis 构建的企业级统一身份认证平台。

## 功能特性

### 🔐 多协议支持
- **OAuth2 / OIDC**: 完整的授权服务器实现，支持授权码、刷新令牌、客户端凭证、密码模式
- **SAML2**: SAML 2.0 身份提供商 (IdP)，支持签名、加密、单点登出
- **CAS**: CAS 3.0 协议支持，票据验证

### 👥 用户管理
- **LDAP 集成**: 支持 LDAP 目录服务用户认证和同步
- **多因素认证 (MFA)**: TOTP 基于时间的一次性密码，支持 Google Authenticator
- **用户目录同步**: 定时从 LDAP 同步用户信息到本地数据库

### 🎨 登录体验
- **可定制登录页面**: 通过配置文件自定义标题、Logo、背景、版权信息
- **记住我**: 支持持久化登录
- **账户锁定**: 5次失败自动锁定30分钟
- **多登录方式**: 用户名密码、SAML2、CAS 三种登录入口

### 🔄 会话管理
- **Redis 会话存储**: 分布式会话，支持集群部署
- **单点登出 (SSLO)**: 一处登出，所有系统同时失效
- **会话监控**: 实时查看在线用户、活跃会话数
- **强制登出**: 管理员可强制指定用户下线

### 🛡️ 安全特性
- **密码加密**: BCrypt 加密存储
- **CSRF 保护**: Cookie 模式 CSRF Token
- **会话固定保护**: 会话迁移策略
- **并发会话控制**: 限制同一用户同时登录数
- **审计日志**: 登录成功/失败、登出、MFA操作等

## 技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Spring Boot | 3.2.5 | 基础框架 |
| Spring Security | 6.2.4 | 安全框架 |
| Spring Authorization Server | 1.2.3 | OAuth2 授权服务器 |
| Spring Security SAML2 | 6.2.4 | SAML2 支持 |
| Spring Security CAS | 6.2.4 | CAS 支持 |
| Spring Security LDAP | 6.2.4 | LDAP 支持 |
| Spring Session | 3.2.1 | 会话管理 |
| Redis | 7.x | 会话存储 |
| JPA / Hibernate | 6.x | ORM 框架 |
| H2 / MySQL | - | 数据库支持 |
| Thymeleaf | 3.x | 模板引擎 |

## 项目结构

```
sso-server/
├── src/main/java/com/sso/
│   ├── SsoServerApplication.java          # 主启动类
│   ├── auth/                               # 认证模块
│   │   ├── CustomAuthenticationSuccessHandler.java
│   │   ├── CustomAuthenticationFailureHandler.java
│   │   ├── MfaAuthenticationToken.java
│   │   ├── MfaAuthenticationFilter.java
│   │   ├── MfaAuthenticationProvider.java
│   │   └── saml2/                          # SAML2 认证
│   │       ├── Saml2AuthenticationSuccessHandler.java
│   │       ├── Saml2MetadataController.java
│   │       └── Saml2ResponseGenerator.java
│   ├── config/                             # 配置模块
│   │   ├── SecurityConfig.java
│   │   ├── RedisSessionConfig.java
│   │   ├── LdapConfig.java
│   │   ├── CasConfig.java
│   │   ├── Saml2Config.java
│   │   ├── DataInitializer.java
│   │   ├── OAuth2AuthorizationServerConfig.java
│   │   ├── OAuth2ResourceServerConfig.java
│   │   └── properties/
│   │       └── SsoProperties.java
│   ├── controller/                         # 控制器
│   │   ├── LoginController.java
│   │   ├── UserController.java
│   │   ├── SessionController.java
│   │   └── OAuth2Controller.java
│   ├── entity/                             # 数据实体
│   │   ├── User.java
│   │   ├── Role.java
│   │   ├── Permission.java
│   │   ├── UserSession.java
│   │   ├── OAuth2Client.java
│   │   └── Saml2Sp.java
│   ├── repository/                         # 数据访问层
│   ├── service/                            # 业务逻辑层
│   │   ├── UserService.java
│   │   └── CustomUserDetailsService.java
│   ├── session/                            # 会话管理
│   │   ├── SessionManager.java
│   │   ├── SingleLogoutHandler.java
│   │   └── SessionEventListener.java
│   ├── sync/                               # 目录同步
│   │   └── LdapSyncService.java
│   └── exception/                          # 异常处理
│       └── GlobalExceptionHandler.java
├── src/main/resources/
│   ├── application.yml                     # 主配置文件
│   ├── application-prod.yml                # 生产环境配置
│   ├── templates/                          # 页面模板
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── logout-success.html
│   │   └── oauth2-consent.html
│   ├── static/                             # 静态资源
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   └── credentials/                        # 密钥证书
└── src/test/java/                          # 测试代码
```

## 快速开始

### 环境要求
- JDK 17+
- Maven 3.8+
- Redis 7.x
- MySQL 8.x (可选，默认使用 H2)
- LDAP 服务 (可选)

### 配置说明

#### 1. 基础配置
编辑 `src/main/resources/application.yml`:

```yaml
server:
  port: 8080
  servlet:
    context-path: /sso

sso:
  login:
    title: "企业统一身份认证平台"
    logo: "/images/logo.png"
    background-image: "/images/login-bg.jpg"
    mfa-enabled: true
```

#### 2. Redis 配置
```yaml
spring:
  data:
    redis:
      host: localhost
      port: 6379
      password: your_password
```

#### 3. OAuth2 配置
```yaml
sso:
  oauth2:
    issuer: https://sso.example.com/sso
    jks-keystore: classpath:credentials/oauth2.jks
    jks-password: changeit
    key-alias: oauth2-key
    key-password: changeit
```

#### 4. SAML2 配置
```yaml
sso:
  saml2:
    entity-id: https://sso.example.com/sso/saml2
    base-url: https://sso.example.com/sso
    signing-key-location: classpath:credentials/saml-signing.key
    signing-cert-location: classpath:credentials/saml-signing.crt
```

#### 5. LDAP 配置
```yaml
sso:
  ldap:
    enabled: true
    urls: ldap://localhost:389
    base: dc=example,dc=com
    user-dn-pattern: uid={0},ou=users
    manager-dn: cn=admin,dc=example,dc=com
    manager-password: admin
```

#### 6. CAS 配置
```yaml
sso:
  cas:
    server-url: https://cas.example.com/cas
    service-url: https://sso.example.com/sso
```

### 生成密钥证书

#### 1. 生成 OAuth2 JWT 密钥库
```bash
keytool -genkeypair -alias oauth2-key -keyalg RSA -keysize 2048 \
  -keystore src/main/resources/credentials/oauth2.jks \
  -storepass changeit -keypass changeit \
  -dname "CN=SSO Server, OU=IT, O=Company, L=City, ST=State, C=CN"
```

#### 2. 生成 SAML2 签名密钥对
```bash
# 生成私钥
openssl genrsa -out src/main/resources/credentials/saml-signing.key 2048

# 生成自签名证书
openssl req -new -x509 -key src/main/resources/credentials/saml-signing.key \
  -out src/main/resources/credentials/saml-signing.crt -days 3650

# 加密密钥对（同上，换个文件名）
```

### 启动运行

#### 开发模式
```bash
mvn spring-boot:run
```

访问: http://localhost:8080/sso/login

#### 默认账户
| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | ADMIN, USER |
| manager | manager123 | MANAGER, USER |
| user | user123 | USER |

#### 生产部署
```bash
mvn clean package -Pprod
java -jar target/sso-server-1.0.0.jar --spring.profiles.active=prod
```

## API 接口

### OAuth2 端点
- `GET /oauth2/authorize` - 授权端点
- `POST /oauth2/token` - 获取令牌
- `POST /oauth2/introspect` - 令牌内省
- `POST /oauth2/revoke` - 吊销令牌
- `GET /oauth2/jwks` - JWKS 公钥集
- `GET /oauth2/userinfo` - 用户信息端点
- `GET /.well-known/openid-configuration` - OIDC 发现端点

### SAML2 端点
- `GET /saml2/metadata` - IdP 元数据
- `GET /saml2/metadata/{spId}` - 指定 SP 元数据
- `POST /saml2/SSO` - SSO 端点
- `POST /saml2/SLO` - SLO 端点

### 管理 API (需要 ADMIN 角色)
- `GET /api/users` - 用户列表
- `GET /api/users/{id}` - 用户详情
- `POST /api/users` - 创建用户
- `PUT /api/users/{id}` - 更新用户
- `DELETE /api/users/{id}` - 删除用户
- `POST /api/users/{username}/unlock` - 解锁用户
- `GET /api/sessions/stats` - 会话统计
- `POST /api/sessions/user/{username}/logout` - 强制登出用户
- `POST /api/users/sync` - 触发 LDAP 同步

## 主要功能说明

### 多因素认证 (MFA)
1. 用户调用 `/api/users/{username}/mfa/generate` 生成密钥
2. 使用 Authenticator App 扫描二维码或手动输入密钥
3. 调用 `/api/users/{username}/mfa/enable` 输入验证码完成绑定
4. 登录时需输入 6 位动态验证码

### 单点登出 (SLO)
1. 用户在任一系统点击登出
2. 系统调用登出接口，失效当前 Session
3. 通知所有已登录的服务提供商执行登出
4. 清理 Redis 中所有相关会话数据
5. 跳转到统一登出成功页面

### LDAP 同步
1. 每日凌晨 2 点自动执行全量同步
2. 支持手动触发同步 `/api/users/sync`
3. 支持单个用户同步 `/api/users/sync/{username}`
4. 自动创建本地用户账号，映射 LDAP 属性

## 安全建议

1. **证书管理**: 生产环境使用正式 CA 签发的证书
2. **密钥轮换**: 定期轮换 OAuth2 JWT 密钥和 SAML2 签名密钥
3. **网络安全**: 启用 HTTPS，配置 HSTS 头
4. **访问控制**: 限制管理接口的访问来源 IP
5. **监控告警**: 配置登录失败告警、异常登录检测
6. **日志审计**: 定期审计登录日志和操作日志

## License

MIT License
