# API响应校验工具

基于OpenAPI规范的API响应结构校验和多环境对比工具。

## 功能特性

- ✅ **OpenAPI规范解析** - 支持OpenAPI 3.0+规范（YAML/JSON格式）
- ✅ **JSON Schema校验** - 校验响应结构、字段类型、必填字段
- ✅ **多环境对比** - 支持dev/prod等多环境响应对比
- ✅ **差异报告** - 生成详细的差异报告，支持导出
- ✅ **可视化界面** - React前端，直观易用

## 技术栈

### 后端
- Java 17
- Spring Boot 3.2
- Swagger Parser (OpenAPI解析)
- Everit JSON Schema (校验引擎)
- Jackson (JSON处理)

### 前端
- React 18
- Axios (HTTP客户端)
- CSS3 (样式)

## 项目结构

```
api-response-validator/
├── backend/                 # Java后端
│   ├── src/
│   │   └── main/
│   │       ├── java/com/api/validator/
│   │       │   ├── ApiValidatorApplication.java
│   │       │   ├── config/
│   │       │   ├── controller/
│   │       │   ├── model/
│   │       │   └── service/
│   │       └── resources/
│   └── pom.xml
├── frontend/                # React前端
│   ├── src/
│   │   ├── components/
│   │   ├── App.js
│   │   ├── App.css
│   │   └── index.js
│   ├── public/
│   └── package.json
└── README.md
```

## 快速开始

### 启动后端

```bash
cd backend
mvn clean install
mvn spring-boot:run
```

后端服务将在 `http://localhost:8080` 启动

### 启动前端

```bash
cd frontend
npm install
npm start
```

前端应用将在 `http://localhost:3000` 启动

## API接口

### 1. 解析OpenAPI规范

**POST** `/api/parse`

请求体:
```json
{
  "openApiSpec": "openapi: 3.0.0..."
}
```

### 2. 校验响应

**POST** `/api/validate`

请求体:
```json
{
  "openApiSpec": "...",
  "path": "/api/users",
  "method": "GET",
  "statusCode": 200,
  "responseBody": "{\"id\": 1, \"name\": \"test\"}"
}
```

### 3. 获取JSON Schema

**POST** `/api/schema`

### 4. 对比环境响应

**POST** `/api/compare`

请求体:
```json
{
  "openApiSpec": "...",
  "path": "/api/users",
  "method": "GET",
  "statusCode": 200,
  "env1Name": "dev",
  "env2Name": "prod",
  "env1ResponseBody": "{...}",
  "env2ResponseBody": "{...}"
}
```

### 5. 生成对比报告

**POST** `/api/compare/report`

## 使用说明

### 1. 输入OpenAPI规范

在左侧面板粘贴你的OpenAPI规范内容（支持YAML和JSON格式），点击"解析规范"按钮。

### 2. 响应校验

- 切换到"响应校验"标签
- 选择API端点或手动输入路径、方法、状态码
- 粘贴API响应体（JSON格式）
- 点击"开始校验"查看结果

### 3. 环境对比

- 切换到"环境对比"标签
- 输入两个环境的名称（如: dev, prod）
- 分别粘贴两个环境的响应体
- 点击"开始对比"查看差异

### 4. 生成报告

- 切换到"差异报告"标签
- 配置对比参数后点击"生成报告"
- 可导出JSON格式报告或复制到剪贴板

## 示例

### 示例OpenAPI规范

```yaml
openapi: 3.0.0
info:
  title: 用户API
  version: 1.0.0
paths:
  /api/users/{id}:
    get:
      summary: 获取用户信息
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                type: object
                required:
                  - id
                  - name
                properties:
                  id:
                    type: integer
                  name:
                    type: string
                  email:
                    type: string
                    format: email
                  age:
                    type: integer
                    minimum: 0
                    maximum: 150
```

### 示例响应（通过校验）

```json
{
  "id": 1,
  "name": "张三",
  "email": "zhangsan@example.com",
  "age": 25
}
```

### 示例响应（校验失败）

```json
{
  "id": "1",
  "email": "invalid-email"
}
```

错误:
- `id` 类型错误 (expected integer, got string)
- `name` 必填字段缺失
- `email` 格式错误

## 校验错误类型

| 类型 | 说明 |
|------|------|
| REQUIRED_FIELD_MISSING | 必填字段缺失 |
| TYPE_MISMATCH | 字段类型不匹配 |
| FORMAT_INVALID | 格式校验失败 |
| STRUCTURE_INVALID | 结构错误 |
| UNKNOWN_FIELD | 未知字段 |
| SCHEMA_ERROR | Schema解析错误 |

## 差异类型

| 类型 | 说明 |
|------|------|
| FIELD_ADDED | 字段新增 |
| FIELD_REMOVED | 字段删除 |
| VALUE_CHANGED | 值变更 |
| TYPE_CHANGED | 类型变更 |
| ARRAY_LENGTH_CHANGED | 数组长度变更 |
| STRUCTURE_MISMATCH | 结构不匹配 |

## 开发说明

### 后端开发

```bash
cd backend
mvn compile
mvn test
```

### 前端开发

```bash
cd frontend
npm run build
npm test
```

## License

MIT
