# 敏感数据脱敏服务 (Data Masking Service)

一个基于 Java + Spring Boot 的敏感数据脱敏服务，支持多种数据库，提供自动敏感字段识别、动态脱敏策略和访问权限控制。

## 功能特性

### 1. 敏感字段自动识别
- **字段名识别**: 通过列名和注释自动识别敏感字段
- **内容识别**: 通过正则表达式识别字段内容中的敏感数据
- **支持的敏感类型**:
  - 身份证号 (ID_CARD)
  - 手机号 (PHONE)
  - 银行卡号 (BANK_CARD)
  - 姓名 (NAME)
  - 邮箱 (EMAIL)
  - 地址 (ADDRESS)

### 2. 多数据库支持
- MySQL
- PostgreSQL
- MongoDB

### 3. 脱敏策略引擎
- **掩码 (MASK)**: 用特殊字符替换部分内容（如：138****8000）
- **替换 (REPLACE)**: 用固定值替换整个内容（如：[已隐藏]）
- **哈希 (HASH)**: 对内容进行哈希运算（支持 MD5、SHA256、SHA512）
- **截断 (TRUNCATE)**: 只保留部分内容

### 4. 访问权限控制
- 基于角色的访问控制 (RBAC)
- 支持的角色: ADMIN, DBA, OPERATOR, VIEWER
- 支持细粒度的敏感类型权限控制

### 5. 数据代理层
- MyBatis 拦截器: 自动拦截 SQL 查询结果并脱敏
- AOP 切面: 通过注解自动脱敏方法返回值
- MongoDB 拦截器: 支持 MongoDB 查询结果脱敏
- Redis 缓存: 元数据缓存支持

## 项目结构

```
data-masking-service/
├── src/main/java/com/datasecurity/masking/
│   ├── DataMaskingApplication.java      # 启动类
│   ├── annotation/
│   │   └── DataMasking.java             # 脱敏注解
│   ├── aspect/
│   │   └── DataMaskingAspect.java       # AOP切面
│   ├── config/
│   │   ├── MyBatisConfig.java           # MyBatis配置
│   │   ├── RedisConfig.java             # Redis配置
│   │   └── StartupInitializer.java      # 启动初始化
│   ├── enums/
│   │   ├── DatabaseType.java            # 数据库类型枚举
│   │   ├── MaskStrategy.java            # 脱敏策略枚举
│   │   └── SensitiveType.java           # 敏感类型枚举
│   ├── interceptor/
│   │   ├── MyBatisMaskInterceptor.java  # MyBatis拦截器
│   │   └── MongoDBMaskInterceptor.java  # MongoDB拦截器
│   ├── model/
│   │   ├── DatabaseConfig.java          # 数据库配置模型
│   │   ├── MaskPolicy.java              # 脱敏策略模型
│   │   └── SensitiveField.java          # 敏感字段模型
│   ├── proxy/
│   │   ├── DataMaskingProxy.java        # 数据代理接口
│   │   └── impl/
│   │       └── DataMaskingProxyImpl.java # 数据代理实现
│   ├── recognizer/
│   │   └── SensitiveFieldRecognizer.java # 敏感字段识别器
│   ├── scanner/
│   │   ├── MetadataScanner.java         # 元数据扫描接口
│   │   ├── MetadataScannerFactory.java  # 扫描器工厂
│   │   └── impl/
│   │       ├── MySQLMetadataScanner.java      # MySQL扫描器
│   │       ├── PostgreSQLMetadataScanner.java # PG扫描器
│   │       └── MongoDBMetadataScanner.java    # MongoDB扫描器
│   ├── access/
│   │   ├── PermissionService.java       # 权限服务
│   │   ├── UserContext.java             # 用户上下文
│   │   └── UserContextHolder.java       # 用户上下文持有器
│   ├── service/
│   │   ├── DataMaskingService.java      # 脱敏服务
│   │   └── MetadataService.java         # 元数据服务
│   ├── controller/
│   │   ├── DataMaskingController.java   # 脱敏API控制器
│   │   └── MetadataController.java      # 元数据API控制器
│   └── example/
│       ├── User.java                    # 示例用户模型
│       ├── UserService.java             # 示例服务
│       └── DemoController.java          # 演示控制器
├── src/main/resources/
│   └── application.yml                  # 配置文件
├── src/test/java/
│   ├── DataMaskingServiceTest.java      # 脱敏服务测试
│   └── PermissionServiceTest.java       # 权限服务测试
└── pom.xml
```

## 快速开始

### 1. 环境要求
- JDK 1.8+
- Maven 3.6+
- MySQL 5.7+ / PostgreSQL 10+ / MongoDB 4.0+ (可选)
- Redis 5.0+ (可选，用于元数据缓存)

### 2. 构建项目

```bash
mvn clean package -DskipTests
```

### 3. 运行项目

```bash
java -jar target/data-masking-service-1.0.0.jar
```

或使用 Maven 直接运行：

```bash
mvn spring-boot:run
```

服务启动后访问: http://localhost:8080

## API 使用说明

### 1. 扫描数据库元数据

**POST** `/api/metadata/scan`

请求体:
```json
{
  "id": "mysql001",
  "name": "用户数据库",
  "type": "MYSQL",
  "host": "localhost",
  "port": 3306,
  "database": "test",
  "username": "root",
  "password": "root"
}
```

### 2. 获取敏感字段列表

**GET** `/api/metadata/{databaseId}`

### 3. 批量脱敏

**POST** `/api/masking/mask/result?databaseId=default`

请求体:
```json
[
  {
    "id": 1,
    "name": "张三",
    "id_card": "110101199001011234",
    "phone": "13800138000"
  }
]
```

### 4. 演示接口

**GET** `/api/demo/users` - 获取用户列表（自动脱敏）

**POST** `/api/demo/user/role/admin` - 切换到管理员角色

**POST** `/api/demo/user/role/viewer` - 切换到查看者角色

## 代码使用示例

### 1. 使用注解自动脱敏

```java
@Service
public class UserService {

    @DataMasking(databaseId = "default")
    public List<Map<String, Object>> findAllUsers() {
        // 查询数据库...
        return userList;
    }
}
```

### 2. 手动调用脱敏服务

```java
@Autowired
private DataMaskingService dataMaskingService;

public void demo() {
    Map<String, Object> user = new HashMap<>();
    user.put("name", "张三");
    user.put("phone", "13800138000");

    // 脱敏单条数据
    Map<String, Object> maskedUser = dataMaskingService.maskRow(user, "default");
}
```

### 3. 设置用户上下文

```java
// 设置管理员角色（可查看原始数据）
UserContext admin = UserContext.builder()
    .userId("admin001")
    .roles(Set.of("ADMIN"))
    .build();
UserContextHolder.set(admin);

// 设置普通用户角色（数据脱敏）
UserContext viewer = UserContext.builder()
    .userId("viewer001")
    .roles(Set.of("VIEWER"))
    .build();
UserContextHolder.set(viewer);

// 清理上下文
UserContextHolder.clear();
```

### 4. 自定义脱敏策略

```java
MaskPolicy customPolicy = MaskPolicy.builder()
    .sensitiveType(SensitiveType.PHONE)
    .strategy(MaskStrategy.MASK)
    .maskChar("#")
    .keepStart(5)
    .keepEnd(2)
    .build();

String masked = maskStrategyService.mask("13800138000", customPolicy);
// 结果: 13800##00
```

## 运行测试

```bash
mvn test
```

## 默认脱敏规则

| 敏感类型 | 策略 | 示例 | 结果 |
|---------|------|------|------|
| 身份证号 | 掩码(前6后4) | 110101199001011234 | 110101********1234 |
| 手机号 | 掩码(前3后4) | 13800138000 | 138****8000 |
| 银行卡号 | 掩码(前4后4) | 6222021234567890123 | 6222***********0123 |
| 姓名 | 掩码(前1后0) | 张三 | 张* |
| 邮箱 | 掩码(前2后0) | zhangsan@example.com | zh*******@example.com |
| 地址 | 截断(前6) | 北京市朝阳区建国路88号 | 北京市朝阳区*** |

## 技术栈

- **框架**: Spring Boot 2.7.x
- **持久层**: MyBatis-Plus 3.5.x
- **连接池**: Druid 1.2.x
- **SQL解析**: JSqlParser 4.6
- **MongoDB**: Spring Data MongoDB
- **缓存**: Spring Data Redis
- **工具库**: Apache Commons Lang3, Commons Codec, Guava
- **代码简化**: Lombok

## License

MIT License
