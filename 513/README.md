# PortScanner - 服务器端口扫描和暴露检测工具

一个基于Go语言编写的服务器端口扫描和安全检测工具，支持TCP端口扫描、服务识别、弱口令检测、版本化风险评估。

## ✨ 功能特性

### 🔍 核心功能
- **TCP端口扫描**: 并发扫描目标服务器的开放端口，支持自定义端口范围和并发数
- **服务识别**: 自动识别端口对应的服务类型和版本，支持动态特征库
- **弱口令检测**: 
  - Redis未授权访问检测
  - Redis弱口令认证检测
  - MySQL弱口令检测（支持多个用户名）
  - 自定义密码字典和泄露库导入
- **版本化风险评估**: 根据服务版本生成针对性的加固建议和漏洞信息
- **报告生成**: 支持控制台彩色输出、HTML格式报告和文本格式报告

### 🆕 新增功能
1. **特征库自动更新** - 每日同步最新服务特征，支持NMAP探针库
2. **自定义密码字典** - 支持导入自定义字典和密码泄露库
3. **版本化加固方案** - 根据服务版本生成针对性的加固建议
4. **子命令架构** - 支持多种管理和查询命令

## 📁 项目结构

```
.
├── main.go                        # 主程序入口（子命令调度）
├── go.mod                         # Go模块配置
├── README.md                      # 使用说明
├── scanner/
│   ├── portscanner.go            # TCP端口扫描核心
│   ├── service.go                # 服务识别模块（集成特征库）
│   ├── signature.go              # 特征库管理（自动更新）
│   ├── vulnerability.go          # 漏洞检测模块
│   ├── passwords.go              # 密码字典管理
│   ├── versioned_recommendations.go  # 版本化加固方案
│   └── risk.go                   # 风险评估模块
└── report/
    └── reporter.go               # 报告生成模块
```

## 🚀 快速开始

### 编译
```bash
go build -o portscanner.exe .
```

### 基本使用

```bash
# 扫描本地主机常用端口 (1-10000)
portscanner.exe -host 127.0.0.1

# 或使用子命令
portscanner.exe scan -host 192.168.1.1

# 快速模式 (扫描1-1000端口，高并发)
portscanner.exe -host 192.168.1.1 -fast

# 自定义端口范围
portscanner.exe -host 192.168.1.100 -start 1 -end 65535

# 生成报告
portscanner.exe -host 192.168.1.1 -html report.html -txt report.txt
```

## 🔧 特征库管理

### 查看特征库信息
```bash
portscanner.exe sig-info
```

### 更新特征库
```bash
portscanner.exe sig-update
```

### 导出/导入特征库
```bash
# 导出特征库
portscanner.exe sig-export signatures.json

# 导入特征库
portscanner.exe sig-import signatures.json
```

**特征库特性**:
- 内置常用服务探针（FTP、SSH、HTTP、Redis、MySQL、MongoDB等）
- 自动从NMAP官方源同步服务特征
- 24小时自动更新检测
- 支持自定义特征导入导出
- 版本校验和完整性检查

## 🔐 密码字典管理

### 查看字典库信息
```bash
portscanner.exe dict-info
```

### 导入密码字典
```bash
# 导入普通字典
portscanner.exe dict-import mydict.txt custom_dict

# 导入密码泄露库（支持密码:计数格式）
portscanner.exe dict-leak rockyou.txt rockyou_2024
portscanner.exe dict-leak haveibeenpwned.txt hibp high_risk,leaked
```

### 管理自定义密码
```bash
# 添加自定义密码
portscanner.exe dict-add "MyCustomPass123!"

# 搜索密码
portscanner.exe dict-search admin

# 导出密码字典
portscanner.exe dict-export passwords.txt
portscanner.exe dict-export high_risk_passwords.txt leak,high_risk
```

**自动加载**:
将 `.txt` 或 `.dict` 文件放入 `~/.portscanner/passwords/custom/` 目录，程序将自动加载。

## 📊 版本漏洞查询

```bash
# 查询Redis服务漏洞
portscanner.exe vuln-search redis

# 查询特定CVE
portscanner.exe vuln-search redis CVE-2023-41053

# 查询MySQL漏洞
portscanner.exe vuln-search mysql

# 查询SSH漏洞
portscanner.exe vuln-search ssh
```

**支持的服务版本**:
- Redis: 5.0, 6.0, 7.0, 7.2
- MySQL: 5.7, 8.0, 10.11 (MariaDB)
- OpenSSH: 7.4, 8.9, 9.3
- HTTP: Nginx 1.18, 1.24 / Apache 2.4

## ⚙️ 命令行参数

### 扫描命令 (scan)

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `-host` | 127.0.0.1 | 目标主机IP或域名 |
| `-start` | 1 | 起始端口 |
| `-end` | 10000 | 结束端口 |
| `-timeout` | 1000 | 连接超时时间(毫秒) |
| `-threads` | 100 | 并发线程数 |
| `-html` | "" | 生成HTML报告文件 |
| `-txt` | "" | 生成文本报告文件 |
| `-skip-vuln` | false | 跳过漏洞检测 |
| `-fast` | false | 快速模式 |
| `-password-limit` | 100 | 密码检测最大数量 |
| `-no-version-advice` | false | 禁用版本化加固建议 |

### 所有子命令

```
portscanner.exe [command] [args]

Commands:
  scan          端口扫描（默认命令）
  sig-update    更新特征库
  sig-info      查看特征库信息
  sig-export    导出特征库
  sig-import    导入特征库
  dict-info     查看字典库信息
  dict-import   导入密码字典
  dict-leak     导入密码泄露库
  dict-add      添加自定义密码
  dict-search   搜索密码
  dict-export   导出密码字典
  vuln-search   搜索服务漏洞
  help          显示帮助
```

## 🎯 版本化加固方案示例

### Redis 5.0.x (EOL版本)
```
[Critical] 端口 6379 (Redis) - 风险等级: [Critical]
   风险描述: Redis默认无认证，暴露公网极易被入侵
   ⚠️  该版本已停止支持(EOL)，存在严重安全风险！
   - CVE-2018-12326 (CVSS: 7.5) - 缓冲区溢出漏洞

   加固建议:
   升级路径: 6.0.x → 6.2.x → 7.2.x
   1. 紧急升级到 Redis 7.2.x 版本
   2. 在升级前加强网络隔离
   3. 配置严格的防火墙规则
   4. 不要暴露到公网
   ...
```

### MySQL 5.7.x (EOL版本)
```
[Critical] 端口 3306 (MySQL) - 风险等级: [Critical]
   风险描述: MySQL数据库直接暴露存在数据泄露风险
   ⚠️  该版本已停止支持(EOL)，存在严重安全风险！
   - CVE-2019-5443 (CVSS: 10.0) - 远程代码执行漏洞

   加固建议:
   升级路径: 8.0.x → 8.2.x
   1. 立即规划升级到 MySQL 8.2.x
   2. 在升级前加强网络隔离
   3. 禁用不必要的功能
   ...
```

## 📈 风险等级说明

| 等级 | 颜色 | 说明 | 示例 |
|------|------|------|------|
| Critical | 🔴 红色 | 严重风险，需要立即处理 | Redis未授权、EOL版本、Telnet暴露 |
| High | 🟣 紫色 | 高风险，建议尽快处理 | MySQL弱口令、RDP暴露、已知CVE漏洞 |
| Medium | 🟡 黄色 | 中风险，建议优化配置 | FTP明文传输、旧版本服务 |
| Low | 🟢 绿色 | 低风险，正确配置即可 | 较新版本SSH |
| Info | 🔵 青色 | 信息提示 | 常规HTTP服务 |

## ⚠️ 注意事项

### 法律声明
- 仅对您拥有合法授权的系统进行扫描
- 未经授权的端口扫描可能违反法律法规
- 建议在测试环境中使用
- 高并发扫描可能对网络造成影响

### 性能建议
- 内网扫描: 建议使用 200-500 线程
- 外网扫描: 建议使用 50-100 线程
- 超时时间: 内网 500ms，外网 1000-2000ms
- 密码检测: 根据需要调整 `-password-limit` 参数

### 数据存储位置
- 特征库: `~/.portscanner/signatures/signatures.json`
- 密码库: `~/.portscanner/passwords/passwords.json`
- 自定义字典: `~/.portscanner/passwords/custom/`

## 📝 使用示例

### 1. 完整安全扫描
```bash
portscanner.exe -host 192.168.1.100 -start 1 -end 65535 \
  -threads 200 -password-limit 200 \
  -html full_scan_report.html -txt full_scan_report.txt
```

### 2. 更新特征库后扫描
```bash
portscanner.exe sig-update
portscanner.exe -host target.example.com -fast -html report.html
```

### 3. 导入泄露库后进行密码审计
```bash
portscanner.exe dict-leak rockyou.txt rockyou_2024 high_risk
portscanner.exe -host 192.168.1.100 -password-limit 500
```

### 4. 查询特定服务的漏洞信息
```bash
portscanner.exe vuln-search redis
portscanner.exe vuln-search mysql CVE-2024
```

## 🤝 贡献

欢迎提交Issue和PR来改进这个工具！

---

**本工具仅供安全研究和授权测试使用，请勿用于非法用途。**
