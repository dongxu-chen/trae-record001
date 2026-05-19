# 云存储文件网关服务

基于 Go + Gin + MinIO + Redis 实现的文件分片上传服务，支持大文件（最大5GB）断点续传、分片顺序校验、MD5去重、HTTP Range断点下载、服务端加密、对象版本控制。

## 功能特性

- ✅ 文件分片上传
- ✅ **分片顺序校验** - 确保分片按序号依次上传
- ✅ **Redis 持久化上传状态** - 服务重启后可恢复
- ✅ **文件MD5去重** - 相同文件只存储一份，引用计数管理
- ✅ **HTTP Range 协议支持** - 断点下载、分块下载
- ✅ **分片MD5校验** - 支持分片完整性校验
- ✅ **服务端加密 (SSE-C)** - AES-256 加密，KMS 密钥管理
- ✅ **对象版本控制** - 保留历史版本，支持版本回滚
- ✅ **生命周期管理** - 自动过期删除文件和历史版本
- ✅ 文件元数据管理
- ✅ 文件下载接口（支持指定版本）
- ✅ 文件删除接口
- ✅ 支持最大5GB文件

## 技术栈

- **Go 1.21+**
- **Gin** - Web 框架
- **MinIO SDK** - 对象存储
- **Redis** - 上传状态缓存、MD5映射
- **KMS** - 密钥管理服务
- **GORM + SQLite** - 元数据持久化

## 项目结构

```
cloud-storage-gateway/
├── config/          # 配置文件
├── database/        # 数据库初始化和操作
├── handlers/        # HTTP 处理器
├── models/          # 数据模型
├── minio/           # MinIO 客户端封装
├── redis/           # Redis 客户端封装
├── main.go          # 程序入口
├── go.mod           # 依赖管理
└── README.md        # 项目文档
```

## 快速开始

### 1. 环境要求

- 安装 Go 1.21 或更高版本
- 安装并运行 MinIO 服务（默认端口 9000）
- 安装并运行 Redis 服务（默认端口 6379）

### 2. 启动依赖服务

```bash
# 启动 MinIO
docker run -p 9000:9000 -p 9001:9001 \
  --name minio \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"

# 启动 Redis
docker run -p 6379:6379 --name redis -d redis
```

### 3. 安装依赖

```bash
go mod tidy
```

### 4. 运行服务

```bash
go run main.go
```

服务将在 `http://localhost:8080` 启动

## API 接口文档

### 1. 初始化上传会话

**POST** `/api/v1/upload/init`

请求体：
```json
{
  "file_name": "example.zip",
  "file_size": 104857600,
  "file_type": "application/zip",
  "md5_hash": "d41d8cd98f00b204e9800998ecf8427e"  // 可选，用于去重
}
```

响应：
```json
{
  "file_id": "uuid-string",
  "total_chunks": 20,
  "chunk_size": 5242880,
  "is_duplicate": false  // 如果MD5已存在则为true
}
```

### 2. 上传分片（带顺序校验）

**POST** `/api/v1/upload/chunk`

Content-Type: `multipart/form-data`

表单字段：
- `file_id`: 文件ID
- `chunk_number`: 分片序号（从1开始，**必须按顺序上传**）
- `chunk`: 分片文件内容

响应：
```json
{
  "message": "Chunk uploaded successfully",
  "chunk_number": 1,
  "file_id": "uuid-string",
  "next_expected": 2
}
```

**分片顺序校验：**
- 必须按 1, 2, 3... 顺序上传
- 如果跳过序号，会返回错误：`{"error": "Chunks must be uploaded in order", "expected_chunk": 2, "received_chunk": 3}`

### 3. 上传分片（带MD5校验）

**POST** `/api/v1/upload/chunk-md5`

Content-Type: `multipart/form-data`

表单字段：
- `file_id`: 文件ID
- `chunk_number`: 分片序号
- `chunk_md5`: 分片MD5值（可选，用于校验）
- `chunk`: 分片文件内容

响应（MD5不匹配时）：
```json
{
  "error": "Chunk MD5 mismatch",
  "expected_md5": "d41d8cd98f00b204e9800998ecf8427e",
  "calculated_md5": "..."
}
```

### 4. 查询上传状态（断点续传）

**GET** `/api/v1/upload/status/:file_id`

响应：
```json
{
  "file_id": "uuid-string",
  "file_name": "example.zip",
  "status": "uploading",
  "total_chunks": 20,
  "uploaded_chunks": 5,
  "uploaded_chunk_list": [1, 2, 3, 4, 5],
  "next_expected": 6
}
```

### 5. 完成上传

**POST** `/api/v1/upload/complete`

请求体：
```json
{
  "file_id": "uuid-string",
  "md5_hash": "d41d8cd98f00b204e9800998ecf8427e"  // 可选
}
```

响应（文件去重时）：
```json
{
  "message": "File deduplicated",
  "file_id": "existing-file-id",
  "object_path": "files/existing-file-id.zip",
  "is_duplicate": true
}
```

### 6. 断点下载（HTTP Range）

**GET** `/api/v1/files/:file_id/download`

支持 HTTP Range 头进行断点续传：

```bash
# 下载整个文件
curl -O http://localhost:8080/api/v1/files/:file_id/download

# 从第1000字节开始下载
curl -H "Range: bytes=1000-" -O http://localhost:8080/api/v1/files/:file_id/download

# 下载 1000-2000 字节范围
curl -H "Range: bytes=1000-2000" -O http://localhost:8080/api/v1/files/:file_id/download

# 下载最后500字节
curl -H "Range: bytes=-500" -O http://localhost:8080/api/v1/files/:file_id/download
```

响应头示例：
```
Accept-Ranges: bytes
Content-Length: 1001
Content-Range: bytes 1000-2000/104857600
Content-Disposition: attachment; filename="example.zip"
```

### 7. 获取文件元数据

**GET** `/api/v1/files/:file_id`

响应：
```json
{
  "id": 1,
  "file_id": "uuid-string",
  "file_name": "example.zip",
  "file_size": 104857600,
  "file_type": "application/zip",
  "total_chunks": 20,
  "status": "completed",
  "object_path": "files/uuid-string.zip",
  "md5_hash": "d41d8cd98f00b204e9800998ecf8427e",
  "ref_count": 1,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### 8. 文件列表

**GET** `/api/v1/files/`

### 9. 删除文件

**DELETE** `/api/v1/files/:file_id`

- 当 `ref_count > 1` 时，只减少引用计数
- 当 `ref_count == 1` 时，真正删除文件

响应（引用计数减少时）：
```json
{
  "message": "Reference count decreased",
  "ref_count": 2
}
```

响应（真正删除时）：
```json
{
  "message": "File deleted successfully"
}
```

## 上传状态说明

- `init` - 已初始化，等待上传
- `uploading` - 上传中
- `completed` - 上传完成
- `failed` - 上传失败

## 配置说明

在 `config/config.go` 中可修改以下配置：

```go
const (
    MinIOEndpoint   = "localhost:9000"  // MinIO 地址
    MinIOAccessKey  = "minioadmin"       // MinIO 用户名
    MinIOSecretKey  = "minioadmin"       // MinIO 密码
    MinIOBucketName = "file-storage"     // 存储桶名称

    RedisAddr       = "localhost:6379"   // Redis 地址
    RedisPassword   = ""                  // Redis 密码
    RedisDB         = 0                   // Redis 数据库

    ChunkSize       = 5 * 1024 * 1024    // 分片大小（5MB）
    MaxFileSize     = 5 * 1024 * 1024 * 1024  // 最大文件（5GB）
    
    ServerPort      = ":8080"            // 服务端口
)
```

## 分片上传流程

1. **客户端** 调用 `/upload/init` 初始化上传，传入文件MD5实现秒传
2. **客户端** 将文件按 5MB 分片，计算每个分片的MD5
3. **客户端** 按顺序调用 `/upload/chunk-md5` 上传每个分片
   - 服务端校验分片序号是否正确
   - 服务端校验分片MD5是否匹配
4. 支持断点续传：调用 `/upload/status/:file_id` 获取已上传分片和下一个期望序号
5. 所有分片上传完成后，调用 `/upload/complete` 合并文件
6. 服务端自动清理临时分片文件和Redis缓存

## 关键特性说明

### Redis 状态持久化

- 上传会话信息保存在 Redis（24小时过期）
- 已上传分片记录保存在 Redis
- 服务重启后上传状态不丢失
- Redis宕机时自动降级到SQLite查询

### 文件MD5去重

- 初始化上传时传入文件MD5
- 如果相同MD5的文件已上传完成，直接返回已有file_id，并增加引用计数
- 完成上传时再次校验MD5，避免重复存储
- 删除文件时使用引用计数，只有最后一个引用才真正删除

### 分片顺序校验

- 强制分片按 1, 2, 3... 顺序上传
- 每次上传后返回 `next_expected` 告诉客户端下一个应上传的分片
- 避免分片乱序导致的合并错误

### HTTP Range 断点下载

- 支持 Range 头协议
- 支持多种范围格式：`bytes=start-`、`bytes=start-end`、`bytes=-suffix`
- 返回 206 Partial Content 状态码
- 支持浏览器和下载工具的断点续传功能
- 下载接口支持 `version_id` 参数下载特定版本

### 服务端加密 (SSE-C)

- 支持 AES-256 服务端加密
- 内建 KMS 密钥管理系统
- 支持创建、启用、禁用、轮换、导出、导入密钥
- 支持生成数据密钥用于客户端加密
- 初始化上传时指定 encryption_key_id 即可启用加密
- 下载时自动使用对应密钥解密

### 对象版本控制

- 桶默认开启版本控制
- 每次文件修改自动创建新版本
- 支持查询对象的所有历史版本
- 支持恢复到任意历史版本
- 支持删除特定版本
- 删除文件时创建删除标记，不真正删除数据

### 生命周期管理

- 支持设置文件过期时间（自动删除）
- 支持全局过期规则
- 支持历史版本自动过期
- 支持查询和删除生命周期规则

## API 参考 - KMS 密钥管理

### 创建加密密钥
```
POST /api/v1/kms/keys
{
  "key_id": "my-key",
  "description": "My encryption key"
}
```

### 列出所有密钥
```
GET /api/v1/kms/keys
```

### 获取密钥元数据
```
GET /api/v1/kms/keys/:key_id
```

### 启用/禁用密钥
```
POST /api/v1/kms/keys/:key_id/enable
POST /api/v1/kms/keys/:key_id/disable
```

### 轮换密钥
```
POST /api/v1/kms/keys/:key_id/rotate
```

### 导出/导入密钥
```
POST /api/v1/kms/keys/:key_id/export
POST /api/v1/kms/keys/:key_id/import
```

### 生成数据密钥
```
POST /api/v1/kms/keys/:key_id/generate-data-key
```

## API 参考 - 对象版本控制

### 获取对象版本列表
```
GET /api/v1/versions/:file_id
```

响应：
```json
{
  "file_id": "uuid",
  "versions": [
    {
      "version_id": "version-id",
      "is_latest": true,
      "size": 1048576,
      "last_modified": "2024-01-01T00:00:00Z",
      "is_delete_marker": false
    }
  ]
}
```

### 恢复到指定版本
```
POST /api/v1/versions/restore
{
  "file_id": "uuid",
  "version_id": "version-id"
}
```

### 删除特定版本
```
DELETE /api/v1/versions/:file_id?version_id=version-id
```

### 获取版本控制状态
```
GET /api/v1/versions/status
```

## API 参考 - 生命周期管理

### 设置文件过期时间
```
POST /api/v1/lifecycle/expiration
{
  "file_id": "uuid",
  "days": 30
}
```

### 设置全局过期规则
```
POST /api/v1/lifecycle/global-expiration
{
  "days": 180
}
```

### 设置历史版本过期时间
```
POST /api/v1/lifecycle/noncurrent-expiration
{
  "days": 90
}
```

### 获取生命周期配置
```
GET /api/v1/lifecycle/config
```

### 删除生命周期规则
```
DELETE /api/v1/lifecycle/rules/:rule_id
```

## API 参考 - 使用加密上传文件

### 初始化加密上传
```json
POST /api/v1/upload/init
{
  "file_name": "secret.pdf",
  "file_size": 10485760,
  "file_type": "application/pdf",
  "md5_hash": "file-md5-hash",
  "encryption_key_id": "my-key"
}
```

然后正常上传分片和完成上传，文件将在服务端加密存储。

## API 参考 - 下载特定版本

```
GET /api/v1/files/:file_id/download?version_id=version-id
```
