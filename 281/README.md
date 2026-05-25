# 文件传输管理系统

基于 Spring Boot + MinIO + WebSocket + MySQL 实现的大文件传输管理系统。

## 功能特性

### 核心功能
- ✅ **大文件分片上传** - 支持超大文件分片上传，默认分片大小5MB
- ✅ **断点续传** - 支持上传中断后继续上传，无需重新开始
- ✅ **秒传** - 通过MD5校验实现文件秒传，相同文件无需重复上传
- ✅ **分片下载** - 支持Range请求断点续传下载
- ✅ **传输限速** - 可配置上传下载速度限制
- ✅ **用户存储配额** - 每个用户有独立的存储空间配额
- ✅ **压缩包在线预览** - 支持ZIP/JAR/WAR/EAR等压缩包在线浏览
- ✅ **文件收集链接** - 可创建收集链接，他人无需登录即可上传文件
- ✅ **WebSocket实时进度** - 实时推送上传进度到前端
- ✅ **操作审计日志** - 记录所有文件操作日志

## 技术栈

- **后端框架**: Spring Boot 3.2.0
- **数据库**: MySQL 8.0+
- **对象存储**: MinIO
- **实时通信**: WebSocket
- **ORM**: Spring Data JPA
- **工具库**: Apache Commons Compress, Lombok

## 项目结构

```
src/main/java/com/filetransfer/
├── FileTransferApplication.java    # 启动类
├── common/                          # 通用类
│   └── Result.java                 # 统一响应结果
├── config/                          # 配置类
│   ├── AppInitializer.java         # 应用初始化
│   ├── CorsConfig.java             # 跨域配置
│   ├── DataInitializer.java        # 测试数据初始化
│   ├── MinIOConfig.java            # MinIO配置
│   └── WebSocketConfig.java        # WebSocket配置
├── controller/                      # 控制器
│   ├── ArchivePreviewController.java   # 压缩包预览
│   ├── AuditLogController.java         # 审计日志
│   ├── FileCollectionController.java   # 文件收集
│   ├── FileController.java             # 文件管理
│   ├── FileDownloadController.java     # 文件下载
│   └── FileUploadController.java       # 文件上传
├── dto/                             # 数据传输对象
│   ├── ArchiveEntryDTO.java
│   ├── ChunkUploadRequest.java
│   ├── CreateCollectionLinkRequest.java
│   ├── ProgressMessage.java
│   ├── UploadInitRequest.java
│   ├── UploadInitResponse.java
│   └── UploadToCollectionRequest.java
├── entity/                          # 实体类
│   ├── AuditLog.java
│   ├── ChunkUploadTask.java
│   ├── CollectedFile.java
│   ├── FileCollectionLink.java
│   ├── FileInfo.java
│   ├── UploadedChunk.java
│   └── User.java
├── exception/                       # 异常处理
│   └── GlobalExceptionHandler.java
├── repository/                      # 数据访问层
│   ├── AuditLogRepository.java
│   ├── ChunkUploadTaskRepository.java
│   ├── CollectedFileRepository.java
│   ├── FileCollectionLinkRepository.java
│   ├── FileInfoRepository.java
│   ├── UploadedChunkRepository.java
│   └── UserRepository.java
├── service/                         # 业务逻辑层
│   ├── ArchivePreviewService.java
│   ├── AuditLogService.java
│   ├── FileCollectionService.java
│   ├── FileDownloadService.java
│   ├── FileUploadService.java
│   ├── MinIOService.java
│   └── StorageQuotaService.java
├── util/                            # 工具类
│   ├── RateLimitedInputStream.java
│   └── RateLimiter.java
└── websocket/                       # WebSocket
    └── ProgressWebSocketHandler.java
```

## 快速开始

### 环境要求
- JDK 17+
- MySQL 8.0+
- MinIO
- Maven 3.6+

### 配置数据库

1. 创建数据库
```sql
CREATE DATABASE file_transfer_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. 修改 `application.yml` 中的数据库配置
```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/file_transfer_db
    username: root
    password: your_password
```

### 配置MinIO

1. 启动MinIO服务
2. 修改 `application.yml` 中的MinIO配置
```yaml
minio:
  endpoint: http://localhost:9000
  accessKey: minioadmin
  secretKey: minioadmin
  bucketName: file-transfer-bucket
```

### 启动项目

```bash
# 编译
mvn clean package

# 运行
java -jar target/file-transfer-system-1.0.0.jar
```

### 默认测试用户

| 用户名 | 密码 | 配额 |
|--------|------|------|
| admin | admin123 | 100GB |
| test | test123 | 10GB |

## API接口

### 文件上传

1. **初始化上传**
   ```
   POST /api/upload/init
   Content-Type: application/json
   
   {
     "fileName": "test.zip",
     "fileSize": 104857600,
     "fileMd5": "xxx",
     "userId": 1
   }
   ```

2. **上传分片**
   ```
   POST /api/upload/chunk/{uploadId}
   Content-Type: multipart/form-data
   
   chunkNumber: 1
   totalChunks: 20
   chunkSize: 5242880
   fileSize: 104857600
   fileName: test.zip
   file: [分片文件]
   ```

3. **合并分片**
   ```
   POST /api/upload/merge/{uploadId}
   ```

### 文件下载

```
GET /api/download/{fileId}?userId=1
```

支持Range请求断点续传。

### WebSocket进度通知

连接地址: `ws://localhost:8080/api/ws/progress`

订阅上传进度: 发送 `subscribe:{uploadId}`

### 文件收集

1. **创建收集链接**
   ```
   POST /api/collection/create
   Content-Type: application/json
   
   {
     "title": "项目文件收集",
     "description": "请上传项目相关文件",
     "maxFileSize": 104857600,
     "maxFiles": 10,
     "expireDays": 7,
     "userId": 1
   }
   ```

2. **上传文件到收集链接**
   ```
   POST /api/collection/upload
   Content-Type: multipart/form-data
   
   linkCode: ABC12345
   uploaderName: 张三
   file: [文件]
   ```

### 压缩包预览

1. **列出压缩包内容**
   ```
   GET /api/archive/list/{fileId}
   ```

2. **预览压缩包内文件**
   ```
   GET /api/archive/preview/{fileId}?path=folder/file.txt
   ```

## 配置说明

### application.yml 主要配置

```yaml
file:
  chunk-size: 5242880           # 分片大小 (5MB)
  rate-limit:
    enabled: true               # 是否启用限速
    max-upload-speed: 10485760  # 最大上传速度 (10MB/s)
    max-download-speed: 10485760 # 最大下载速度 (10MB/s)

user:
  default-quota: 10737418240    # 默认用户配额 (10GB)
```

## 注意事项

1. 生产环境请修改默认密码和密钥
2. 建议配置HTTPS
3. 大文件上传建议使用Nginx反向代理并调整超时时间
4. MinIO建议部署集群以保证高可用
