# 短链接服务 (Shortlink Service)

基于 Spring Boot + Redis + MySQL 实现的高性能短链接服务。

## 功能特性

- ✅ 短链接生成（长链接转短码）
- ✅ 短码解析重定向
- ✅ 支持自定义短码（6位字母数字）
- ✅ 支持有效期设置
- ✅ 访问统计（UV、PV）
- ✅ 来源设备统计（移动端/桌面端/平板）
- ✅ 浏览器统计
- ✅ 地理位置统计
- ✅ 雪花算法 + Base62编码 短码生成（零碰撞）
- ✅ UV指纹识别（IP + User-Agent）
- ✅ Guava本地IP缓存（减少API调用）
- ✅ **批量生成：CSV文件批量导入，导出映射表**
- ✅ **生命周期管理：定时自动清理过期短码**
- ✅ **访问趋势：按小时展示最近7天访问量曲线**
- ✅ **报表导出：CSV格式导出详细访问记录**

## 技术栈

- **框架**: Spring Boot 3.2.0
- **数据库**: MySQL 8.0+
- **缓存**: Redis
- **ORM**: Spring Data JPA
- **构建工具**: Maven
- **Java 版本**: 17

## 快速开始

### 1. 环境准备

确保已安装以下软件：
- JDK 17+
- Maven 3.6+
- MySQL 8.0+
- Redis 5.0+

### 2. 数据库初始化

```bash
# 执行数据库初始化脚本
mysql -u root -p < src/main/resources/schema.sql
```

### 3. 修改配置

编辑 `src/main/resources/application.yml`：

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/shortlink?useUnicode=true&characterEncoding=utf-8&serverTimezone=Asia/Shanghai&useSSL=false
    username: root
    password: your_password

  data:
    redis:
      host: localhost
      port: 6379
      password: your_redis_password

shortlink:
  domain: http://your-domain.com  # 短链接域名
```

### 4. 启动服务

```bash
# 编译项目
mvn clean package -DskipTests

# 启动服务
java -jar target/shortlink-service-1.0.0.jar
```

或使用 Maven 直接运行：

```bash
mvn spring-boot:run
```

## API 接口

### 1. 创建短链接

**POST** `/api/shortlink/create`

请求体：
```json
{
  "originUrl": "https://www.example.com/very/long/url/path",
  "customCode": "mycode",
  "description": "示例链接",
  "expireDays": 30,
  "enableStats": true
}
```

参数说明：
- `originUrl`: 原始URL（必填）
- `customCode`: 自定义短码（可选，4-16位字母数字）
- `description`: 描述（可选）
- `expireDays`: 过期天数（可选）
- `enableStats`: 是否启用统计（可选，默认true）

响应：
```json
{
  "code": 200,
  "message": "success",
  "data": "http://localhost:8080/abc123"
}
```

### 2. 获取短链接信息

**GET** `/api/shortlink/info/{shortCode}`

响应：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "originUrl": "https://www.example.com",
    "shortCode": "abc123",
    "description": "示例链接",
    "expireTime": "2024-02-20T12:00:00",
    "enabled": true,
    "pvCount": 100,
    "uvCount": 50,
    "createTime": "2024-01-20T12:00:00"
  }
}
```

### 3. 获取访问统计

**GET** `/api/shortlink/stats/{shortCode}?days=7`

响应：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "shortCode": "abc123",
    "totalPv": 1000,
    "totalUv": 500,
    "deviceStats": {
      "Desktop": 600,
      "Mobile": 350,
      "Tablet": 50
    },
    "browserStats": {
      "Chrome 120": 400,
      "Firefox 121": 200,
      "Safari 17": 300
    },
    "regionStats": {
      "北京": 150,
      "上海": 120,
      "广东": 100
    },
    "dailyStats": {
      "2024-01-14": 100,
      "2024-01-15": 150
    }
  }
}
```

### 4. 清理过期链接

**DELETE** `/api/shortlink/cleanup-expired`

响应：
```json
{
  "code": 200,
  "message": "success",
  "data": 10
}
```

### 5. 短链接重定向

**GET** `/{shortCode}`

直接访问短链接会自动重定向到原始URL。

## 核心设计

### 短码生成算法

采用 **雪花算法 + Base62编码** 的方案：

1. **雪花算法 (Snowflake)**: 生成全局唯一的64位ID
   - 时间戳 (41位) + 数据中心ID (5位) + 工作节点ID (5位) + 序列号 (12位)
   - 理论上每秒可生成 409.6万 个唯一ID

2. **Base62编码**: 将长数字转换为短字符串
   - 字符集: 0-9, A-Z, a-z (共62个字符)
   - 6位短码可表示: 62^6 ≈ 568亿 种组合
   - 碰撞率极低，配合重试机制确保唯一性

### 缓存策略

- 使用 Redis 缓存热门短链接映射，减少数据库查询
- 缓存过期时间可配置（默认1小时）
- UV统计使用Redis的 `SETNX` 命令实现去重

### 异步统计

访问日志采用异步写入，不影响重定向性能：
- PV/UV 计数实时更新
- 详细访问日志异步持久化

## 项目结构

```
src/main/java/com/shortlink/
├── ShortlinkApplication.java        # 主启动类
├── common/
│   ├── Result.java                  # 统一返回格式
│   └── ErrorCode.java               # 错误码枚举
├── config/
│   ├── RedisConfig.java             # Redis配置
│   └── RestTemplateConfig.java      # HTTP客户端配置
├── controller/
│   ├── RedirectController.java      # 重定向控制器
│   └── ShortLinkController.java     # API控制器
├── dto/
│   ├── CreateShortLinkRequest.java  # 创建请求DTO
│   ├── BatchCreateResult.java       # 批量创建结果DTO
│   ├── StatsResponse.java           # 统计响应DTO
│   ├── HourlyStatsResponse.java     # 小时统计响应DTO
│   └── IpLocationResult.java        # IP地理位置结果DTO
├── entity/
│   ├── ShortLink.java               # 短链接实体
│   └── AccessLog.java               # 访问日志实体
├── exception/
│   ├── BusinessException.java       # 业务异常
│   └── GlobalExceptionHandler.java  # 全局异常处理
├── repository/
│   ├── ShortLinkRepository.java     # 短链接DAO
│   └── AccessLogRepository.java     # 访问日志DAO
├── service/
│   ├── ShortLinkService.java        # 短链接服务
│   ├── AccessLogService.java        # 访问日志服务
│   └── IpLocationService.java       # IP地理位置服务
├── task/
│   └── ShortLinkCleanupTask.java    # 定时清理任务
└── util/
    ├── SnowflakeIdGenerator.java    # 雪花ID生成器
    ├── Base62Encoder.java           # Base62编码器
    ├── CsvUtil.java                 # CSV工具类
    └── UserAgentParser.java         # UserAgent解析器

src/main/resources/
├── application.yml                  # 应用配置
├── schema.sql                       # 数据库初始化脚本
└── templates/
    └── batch_import_template.csv    # 批量导入模板
```

## 性能优化建议

1. **数据库优化**:
   - 为短码字段建立唯一索引
   - 考虑对访问日志表进行分表

2. **Redis优化**:
   - 合理设置缓存过期时间
   - 考虑使用Redis集群

3. **部署优化**:
   - 使用Nginx进行反向代理和负载均衡
   - 配置CDN加速静态资源

## License

MIT License
