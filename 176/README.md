# SSL Certificate Manager

SSL证书自动化管理工具，支持自动申请、续期和部署Let's Encrypt证书。

## 功能特性

- 自动申请Let's Encrypt证书
- 支持多域名SAN证书
- DNS验证（阿里云/Cloudflare）
- 自动检查证书到期时间，过期前30天自动续期
- 支持部署到Nginx或阿里云SLB
- 可配置的检查间隔

## 快速开始

### 1. 安装依赖

```bash
go mod tidy
```

### 2. 编译

```bash
go build -o ssl-manager cmd/ssl-manager/main.go
```

### 3. 配置

复制配置示例文件并修改：

```bash
cp config.example.yaml config.yaml
```

配置文件说明：

```yaml
acme:
  directory_url: https://acme-v02.api.letsencrypt.org/directory  # Let's Encrypt API地址
  email: your-email@example.com                                    # 注册邮箱
  key_type: rsa2048                                                # 密钥类型

dns:
  provider: aliyun  # DNS提供商: aliyun 或 cloudflare
  aliyun:
    access_key_id: your-access-key-id
    access_key_secret: your-access-key-secret
    region_id: cn-hangzhou

deploy:
  nginx:
    enabled: true
    cert_path: /etc/nginx/ssl/fullchain.pem
    key_path: /etc/nginx/ssl/privkey.pem
    reload_command: systemctl reload nginx
  aliyun_slb:
    enabled: false
    access_key_id: your-access-key-id
    access_key_secret: your-access-key-secret
    region_id: cn-hangzhou
    load_balancer_id: lb-xxxxxx
    listener_port: 443

certificates:
  - name: example.com
    domains:
      - example.com
      - www.example.com
    output_dir: ./certs/example.com
    deploy_target: nginx  # 部署目标: nginx 或 aliyun_slb

renewal:
  check_interval: 24h  # 检查间隔
  days_before: 30      # 过期前多少天开始续期
```

### 4. 运行

一次性运行（申请/续期证书后退出）：

```bash
./ssl-manager --config config.yaml --once
```

守护进程模式（持续运行，定期检查）：

```bash
./ssl-manager --config config.yaml
```

## 项目结构

```
.
├── cmd/ssl-manager/          # 主程序入口
│   └── main.go
├── internal/
│   ├── config/               # 配置模块
│   │   └── config.go
│   ├── acme/                 # ACME证书申请模块
│   │   └── acme.go
│   ├── dns/                  # DNS验证模块
│   │   ├── dns.go
│   │   ├── http.go
│   │   └── adapter.go
│   ├── deploy/               # 证书部署模块
│   │   └── deploy.go
│   └── cert/                 # 证书管理模块
│       └── manager.go
├── config.example.yaml       # 配置示例
├── go.mod
└── README.md
```

## 支持的DNS提供商

### 阿里云DNS

需要配置：
- `access_key_id`: 阿里云AccessKey ID
- `access_key_secret`: 阿里云AccessKey Secret
- `region_id`: 区域ID，如 `cn-hangzhou`

权限要求：
- `alidns:AddDomainRecord`
- `alidns:DeleteDomainRecord`
- `alidns:DescribeDomainRecords`

### Cloudflare DNS

需要配置：
- `api_key`: Cloudflare API Key
- `email`: Cloudflare账号邮箱

## 支持的部署目标

### Nginx

将证书复制到指定路径并执行reload命令。

### 阿里云SLB

上传证书到阿里云并更新HTTPS监听器配置。

权限要求：
- `slb:UploadServerCertificate`
- `slb:SetLoadBalancerHTTPSListenerAttribute`

## 注意事项

1. 首次使用建议使用Let's Encrypt的测试环境：
   ```
   https://acme-staging-v02.api.letsencrypt.org/directory
   ```

2. 证书文件默认保存在配置的 `output_dir` 目录下：
   - `fullchain.pem`: 证书链
   - `privkey.pem`: 私钥
   - `chain.pem`: 中间证书

3. 私钥文件权限为0600，请妥善保管。

## License

MIT
