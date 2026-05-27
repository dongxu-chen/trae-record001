# API文档自动生成工具

基于Java + Swagger Core + JavaParser + Freemarker实现的Spring Boot接口文档自动生成工具。

## 功能特性

- **代码扫描**: 自动扫描Spring Boot项目中的Controller、Request/Response对象
- **OpenAPI 3.0**: 生成符合OpenAPI 3.0规范的JSON/YAML文档
- **Swagger UI**: 内置Web服务器，提供Swagger UI可视化展示
- **Markdown导出**: 生成美观的Markdown格式API文档
- **版本管理**: 支持多版本保存、加载和差异对比

## 项目结构

```
api-doc-generator/
├── src/main/java/com/api/docs/
│   ├── ApiDocGenerator.java      # 主入口类
│   ├── config/
│   │   └── GeneratorConfig.java  # 配置类
│   ├── model/                     # 数据模型
│   │   ├── ApiInfo.java
│   │   ├── ControllerInfo.java
│   │   ├── MethodInfo.java
│   │   ├── ParameterInfo.java
│   │   ├── ModelInfo.java
│   │   └── FieldInfo.java
│   ├── scanner/
│   │   └── CodeScanner.java      # 代码扫描器
│   ├── generator/
│   │   ├── OpenApiGenerator.java # OpenAPI生成器
│   │   └── MarkdownGenerator.java # Markdown生成器
│   ├── server/
│   │   └── SwaggerUiServer.java  # Swagger UI服务器
│   └── version/
│       ├── VersionManager.java   # 版本管理器
│       └── VersionDiff.java      # 版本差异模型
├── src/main/resources/
│   ├── swagger-ui/
│   │   └── index.html            # Swagger UI页面
│   └── templates/
│       └── api-docs.ftl          # Markdown模板
└── sample-app/                   # 示例Spring Boot项目
```

## 快速开始

### 1. 编译项目

```bash
mvn clean package -DskipTests
```

### 2. 生成API文档

```bash
# 生成文档（JSON/YAML/Markdown）
java -jar target/api-doc-generator-1.0.0-jar-with-dependencies.jar generate --project=./sample-app

# 生成文档并启动Swagger UI服务器
java -jar target/api-doc-generator-1.0.0-jar-with-dependencies.jar serve --project=./sample-app --port=8088

# 仅扫描代码查看统计
java -jar target/api-doc-generator-1.0.0-jar-with-dependencies.jar scan --project=./sample-app

# 对比两个版本的API差异
java -jar target/api-doc-generator-1.0.0-jar-with-dependencies.jar diff 1.0.0 1.1.0
```

## 命令行参数

### 命令

| 命令 | 说明 |
|------|------|
| `generate` | 生成API文档 (JSON/YAML/Markdown) |
| `serve` | 生成文档并启动Swagger UI服务器 |
| `diff <v1> <v2>` | 对比两个版本的API差异 |
| `scan` | 仅扫描代码并显示统计 |

### 选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--project=<path>` | Spring Boot项目路径 | 当前目录 |
| `--output=<path>` | 输出目录 | `./docs` |
| `--version=<ver>` | API版本号 | `1.0.0` |
| `--title=<title>` | API标题 | `API Documentation` |
| `--server=<url>` | 服务器地址 | `http://localhost:8080` |
| `--port=<port>` | Swagger UI端口 | `8088` |
| `--no-ui` | 禁用Swagger UI | - |
| `--no-md` | 禁用Markdown导出 | - |

## 支持的Spring Boot注解

### Controller注解

- `@RestController`
- `@Controller`
- `@RequestMapping`

### HTTP方法注解

- `@GetMapping`
- `@PostMapping`
- `@PutMapping`
- `@DeleteMapping`
- `@PatchMapping`
- `@RequestMapping` (with method)

### 参数注解

- `@PathVariable`
- `@RequestParam`
- `@RequestHeader`
- `@RequestBody`

### 验证注解

- `@NotNull`
- `@NonNull`
- `@NotEmpty`

## 输出文件

```
docs/
├── openapi.json       # OpenAPI 3.0 JSON格式
├── openapi.yaml       # OpenAPI 3.0 YAML格式
├── api-docs.md        # Markdown格式文档
└── versions/          # 版本历史
    ├── index.txt      # 版本索引
    ├── 1_0_0.json     # 版本1.0.0
    └── 1_1_0.json     # 版本1.1.0
```

## 访问Swagger UI

启动服务后，访问以下地址：

- Swagger UI: http://localhost:8088/swagger-ui/index.html
- OpenAPI JSON: http://localhost:8088/openapi.json

## 技术栈

- **Java 11**
- **Swagger Core 2.2.x** - OpenAPI 3.0模型和工具
- **JavaParser 3.25.x** - Java代码解析
- **Freemarker 2.3.x** - 模板引擎
- **Spark Java 2.9.x** - Web服务器
- **Jackson** - JSON/YAML处理

## 示例项目

`sample-app`目录包含一个示例Spring Boot项目，用于测试文档生成功能：

- `UserController` - 用户管理接口
- `ProductController` - 商品管理接口
- 4个DTO类: UserRequest, UserResponse, ProductRequest, ProductResponse
