# 电子合同签署平台

基于Java Spring Boot + 区块链 + 人脸识别的电子合同签署平台。

## 功能特性

### 1. 用户管理与身份认证
- 用户注册/登录（用户名/手机号 + 密码）
- 短信验证码（阿里云短信服务）
- 人脸认证（阿里云人脸识别API）
- 实名认证（身份证 + 人脸）
- JWT Token 认证

### 2. 合同模板管理
- 模板上传（PDF格式）
- 模板字段配置
- 签名位置配置
- 模板增删改查

### 3. 合同在线填写
- 基于模板创建合同
- 表单字段自动填充
- 自由上传PDF合同
- 合同预览与下载

### 4. 电子签名
- **手写板签名**：Canvas实现，支持撤销、清除
- **拖动签名**：拖拽式签名定位
- 签名图片嵌入PDF
- 签名类型记录

### 5. 多方顺序签署流程
- 支持N方签署
- 按顺序依次签署
- 签署状态流转（待签署→签署中→已完成/已拒签）
- 签署通知（短信）
- 拒签流程

### 6. 身份认证（签署时）
- 短信验证码认证
- 人脸比对认证
- 认证日志记录

### 7. 可信时间戳
- RFC3161标准时间戳协议
- 支持DigiCert等公共TSA服务
- 签名文件哈希加戳
- 时间戳验证

### 8. 区块链存证
- FISCO BCOS联盟链SDK集成
- 智能合约存证
- 合同签署完成自动上链
- 存证哈希、交易ID、区块高度记录
- 存证查询与验证

## 技术栈

### 后端
- **框架**：Spring Boot 2.7.18
- **数据库**：MySQL 8.0 + MyBatis Plus 3.5.3
- **缓存**：Redis
- **安全**：Spring Security + JWT
- **PDF处理**：Apache PDFBox + iText7
- **短信**：阿里云短信SDK
- **人脸识别**：阿里云人脸识别SDK
- **区块链**：FISCO BCOS Java SDK 3.5.0
- **加密**：Bouncy Castle
- **工具库**：Hutool + FastJSON2

### 前端
- Vue.js 2.6 + Element UI
- Canvas 手写签名
- HTML5 Drag & Drop 拖动签名
- Axios HTTP客户端

## 数据库设计

### 核心表结构
- `sys_user` - 用户表
- `contract_template` - 合同模板表
- `contract` - 合同表
- `contract_signer` - 合同签署人表
- `sign_log` - 签署操作日志表
- `sms_code` - 短信验证码表
- `face_verify_log` - 人脸认证日志表
- `blockchain_evidence` - 区块链存证表

## 快速开始

### 环境要求
- JDK 1.8+
- MySQL 8.0+
- Redis 5.0+
- Maven 3.6+
- FISCO BCOS 节点（可选，支持模拟模式）

### 部署步骤

1. **初始化数据库**
```bash
mysql -u root -p < src/main/resources/sql/econtract.sql
```

2. **配置应用参数**
```bash
编辑 src/main/resources/application.yml
- 数据库连接信息
- Redis连接信息
- 阿里云短信/人脸识别AK/SK
- 时间戳服务地址
- FISCO BCOS节点配置
- 文件存储路径
```

3. **放置中文字体**
```bash
将 simsun.ttf 复制到 src/main/resources/fonts/ 目录
```

4. **编译运行**
```bash
mvn clean package
java -jar target/econtract-platform-1.0.0.jar
```

5. **访问系统**
```
前端地址：http://localhost:8080/api/index.html
默认账号：admin / 123456
         user1 / 123456
         user2 / 123456
```

## API接口列表

### 认证模块
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/auth/login` | POST | 用户登录 |
| `/api/auth/register` | POST | 用户注册 |
| `/api/auth/info` | GET | 获取用户信息 |
| `/api/sms/send` | POST | 发送短信验证码 |

### 用户模块
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/user/identity-verify` | POST | 实名认证 |
| `/api/user/face-verify` | POST | 人脸认证 |
| `/api/user/face-save` | POST | 保存人脸照片 |

### 模板模块
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/template/page` | GET | 模板分页列表 |
| `/api/template/{id}` | GET | 模板详情 |
| `/api/template` | POST | 上传模板 |
| `/api/template/{id}` | PUT | 更新模板 |
| `/api/template/{id}` | DELETE | 删除模板 |

### 合同模块
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/contract/page` | GET | 合同分页列表 |
| `/api/contract/pending` | GET | 待我签署列表 |
| `/api/contract/{id}` | GET | 合同详情 |
| `/api/contract` | POST | 创建合同 |
| `/api/contract/sign` | POST | 签署合同 |
| `/api/contract/reject` | POST | 拒签 |
| `/api/contract/download/{id}` | GET | 下载合同 |
| `/api/contract/{id}` | DELETE | 删除合同 |

### 区块链模块
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/blockchain/evidence/{no}` | GET | 查询存证 |
| `/api/blockchain/evidence/list` | GET | 存证列表 |
| `/api/blockchain/evidence/save` | POST | 手动存证 |

## 签署流程说明

### 1. 合同发起
1. 创建人选择模板或上传PDF
2. 填写合同内容
3. 添加多方签署人，设置签署顺序
4. 发起合同，系统自动通知第一方签署

### 2. 顺序签署
1. 第N方收到签署通知
2. 在线查看合同
3. 选择手写签名或拖动签名
4. 完成身份认证（短信/人脸）
5. 提交签署，系统：
   - 嵌入签名到PDF
   - 获取可信时间戳
   - 记录签署信息（IP、设备、时间）
   - 异步写入区块链存证
   - 自动通知下一方

### 3. 签署完成
- 所有签署人完成后，合同状态变为"已完成"
- 最终合同文件自动上链存证
- 各方可下载已签署的PDF文件

## 核心特性说明

### 降级模式
为便于开发测试，系统在第三方服务不可用时自动降级：
- **短信服务**：API失败时保存验证码到数据库，可通过日志查看
- **人脸认证**：API失败时默认通过，相似度设为95.5%
- **时间戳服务**：TSA不可用时生成模拟时间戳
- **区块链服务**：节点不可用时使用模拟上链模式

### 安全机制
- 所有接口JWT鉴权
- 密码BCrypt加密存储
- 敏感操作日志记录（IP、User-Agent）
- 文件SHA256哈希校验
- 跨域配置

### 可靠性保证
- 数据库事务保证数据一致性
- 区块链存证异步重试
- 签署状态幂等性检查
- 顺序签署逻辑校验

## 智能合约示例（Solidity）

```solidity
// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.4.25;

contract Evidence {
    struct EvidenceInfo {
        string evidenceId;
        string hash;
        uint256 timestamp;
        string data;
    }
    
    mapping(string => EvidenceInfo) private evidences;
    
    function saveEvidence(string memory evidenceId, string memory hash, string memory data) public {
        evidences[evidenceId] = EvidenceInfo(evidenceId, hash, block.timestamp, data);
    }
    
    function getEvidence(string memory evidenceId) public view returns(string memory, string memory, uint256, string memory) {
        EvidenceInfo memory e = evidences[evidenceId];
        return (e.evidenceId, e.hash, e.timestamp, e.data);
    }
}
```

## 项目结构

```
econtract-platform/
├── src/
│   └── main/
│       ├── java/com/econtract/
│       │   ├── common/          # 公共类（Result、异常处理等）
│       │   ├── config/          # 配置类
│       │   ├── controller/      # Controller层
│       │   ├── dto/             # 数据传输对象
│       │   ├── entity/          # 实体类
│       │   ├── mapper/          # Mapper接口
│       │   ├── security/        # 安全认证
│       │   ├── service/         # 业务服务
│       │   ├── util/            # 工具类
│       │   └── EcontractApplication.java
│       └── resources/
│           ├── fonts/           # 中文字体
│           ├── fisco/           # FISCO BCOS配置
│           ├── mapper/          # MyBatis XML
│           ├── sql/             # 数据库脚本
│           ├── static/          # 前端页面
│           └── application.yml  # 应用配置
├── pom.xml
└── README.md
```

## 注意事项

1. 生产环境请配置真实的阿里云AK/SK
2. 建议使用HTTPS协议部署
3. 区块链节点需提前部署并配置好证书
4. 中文字体需自行准备（避免版权问题）
5. 默认密码为123456，生产环境请修改

## License

Apache License 2.0
