# 日志脱敏清洗工具

一个功能强大的日志脱敏清洗工具，支持自动识别日志中的敏感信息并进行脱敏处理。

## 功能特性

- 🔒 **敏感信息识别**: 自动识别密码、身份证号、手机号、邮箱、银行卡号等敏感信息
- 📝 **多格式支持**: 支持文本、JSON、XML 三种日志格式
- 🔍 **敏感信息发现**: 扫描日志发现未脱敏的敏感数据，生成风险报告
- 🔐 **动态脱敏**: 根据访问者权限动态调整脱敏程度（完全/部分/不脱敏）
- 📋 **脱敏审计**: 记录所有脱敏操作和原因，支持审计追溯
- 🌳 **JSON 递归遍历**: 完整脱敏 JSON 所有层级，支持深层嵌套和数组
- 🏆 **优先级排序**: 规则按优先级数值排序，数字越大优先级越高
- ⚡ **DFA 正则引擎**: 基于 Brics Automaton 的 DFA 引擎，大日志性能提升 10 倍以上
- 🔧 **自定义规则**: 支持通过配置文件自定义脱敏规则
- 🔄 **Flume 集成**: 提供 Flume Sink 和 Interceptor 两种集成方式
- 📊 **性能基准测试**: 内置 DFA vs NFA 性能对比测试

## 技术栈

- Java 8+
- Brics Automaton (DFA 正则引擎)
- Jackson (JSON 解析)
- Dom4j (XML 解析)
- Apache Flume
- Gson

## 快速开始

### 编译项目

```bash
mvn clean package
```

### 运行演示

```bash
java -jar target/log-desensitization-tool-1.0.0-jar-with-dependencies.jar --demo
```

### 命令行使用

```bash
# 处理文本日志（默认使用 DFA 引擎）
java -jar target/log-desensitization-tool-1.0.0-jar-with-dependencies.jar -i input.log -o output.log -f text

# 处理 JSON 日志
java -jar target/log-desensitization-tool-1.0.0-jar-with-dependencies.jar -i input.json -f json

# 扫描敏感信息（不脱敏，仅发现）
java -jar target/log-desensitization-tool-1.0.0-jar-with-dependencies.jar -i input.log --scan

# 以管理员角色处理（不脱敏）
java -jar target/log-desensitization-tool-1.0.0-jar-with-dependencies.jar -i input.log -r ADMIN

# 以操作员角色处理（部分脱敏）
java -jar target/log-desensitization-tool-1.0.0-jar-with-dependencies.jar -i input.log -r OPERATOR

# 输出审计日志到文件
java -jar target/log-desensitization-tool-1.0.0-jar-with-dependencies.jar -i input.log --audit audit.log

# 查看审计统计
java -jar target/log-desensitization-tool-1.0.0-jar-with-dependencies.jar --audit-stats
```

### 命令行选项

| 选项 | 说明 |
|------|------|
| `-i, --input <文件>` | 输入日志文件路径 |
| `-o, --output <文件>` | 输出文件路径（可选，默认输出到控制台） |
| `-f, --format <格式>` | 日志格式: text, json, xml（默认: text） |
| `-c, --config <文件>` | 配置文件路径 |
| `-d, --demo` | 运行演示示例 |
| `-l, --list-rules` | 列出所有脱敏规则（按优先级排序） |
| `-b, --benchmark [N]` | 运行性能基准测试（迭代N次，默认1000） |
| `-s, --scan` | 扫描敏感信息（不脱敏，仅发现） |
| `-r, --role <角色>` | 访问角色: ADMIN, OPERATOR, VIEWER, ANONYMOUS |
| `--audit <文件>` | 审计日志输出文件路径 |
| `--audit-stats` | 查看审计统计 |
| `--dfa` | 使用 DFA 正则引擎（默认，高性能） |
| `--nfa` | 使用 NFA 正则引擎（兼容模式） |
| `-h, --help` | 显示帮助信息 |

## 敏感信息发现

扫描日志中发现未脱敏的敏感数据，生成风险等级报告：

```java
LogDesensitizationService service = new LogDesensitizationService();
DiscoveryReport report = service.scan("日志内容 13812345678 身份证号...");

// 获取扫描结果
boolean hasSensitive = report.hasSensitiveData();
boolean hasCritical = report.hasCriticalData();
RiskLevel risk = report.getRiskLevel();  // NONE, LOW, MEDIUM, HIGH, CRITICAL

// 查看详细信息
List<SensitiveDataItem> items = report.getItems();
for (SensitiveDataItem item : items) {
    System.out.println(item.getTypeName() + " " + item.getLevel() + " @" + item.getStartPosition());
}

// 生成文本报告
System.out.println(report.toTextReport());
```

**扫描报告示例**:
```
╔══════════════════════════════════════════════════╗
║           敏感信息扫描报告                       ║
╠══════════════════════════════════════════════════╣
║ 风险等级: 严重风险                               ║
╠══════════════════════════════════════════════════╣
║   严重: 2   高危: 1   中危: 1   低危: 0         ║
╚══════════════════════════════════════════════════╝
```

**支持的敏感类型**:

| 类型 | 风险等级 | 说明 |
|------|----------|------|
| 密码凭据 | 严重 | password, pwd, passwd |
| 身份证号 | 严重 | 18位身份证号 |
| API密钥 | 严重 | api_key, secret_key, token |
| 银行卡号 | 高危 | 16-19位银行卡号 |
| 手机号码 | 高危 | 11位手机号 |
| 电子邮箱 | 中危 | 邮箱地址 |
| 地址信息 | 中危 | 地址/addr |
| IP地址 | 低危 | IPv4地址 |

## 动态脱敏

根据访问者权限动态调整脱敏程度，支持三种策略：

| 策略 | 说明 | 手机号示例 |
|------|------|-----------|
| `COMPLETE` | 完全脱敏 | `****` |
| `PARTIAL` | 部分脱敏 | `138****5678` |
| `FULL` | 不脱敏 | `13812345678` |

**内置角色**:

| 角色 | 权限 | 脱敏策略 |
|------|------|----------|
| ADMIN | `sensitive:full` | 不脱敏 |
| OPERATOR | `sensitive:partial` | 部分脱敏 |
| VIEWER | `sensitive:view_type` | 部分脱敏（受限） |
| ANONYMOUS | 无权限 | 完全脱敏 |

```java
LogDesensitizationService service = new LogDesensitizationService();
String log = "用户: 张三, 手机号: 13812345678, 身份证: 110101199001011234";

// 管理员 - 不脱敏
AccessContext admin = AccessContext.admin("admin1");
String adminResult = service.maskDynamic(log, admin);

// 操作员 - 部分脱敏
AccessContext operator = AccessContext.operator("op1");
String opResult = service.maskDynamic(log, operator);

// 匿名用户 - 完全脱敏
AccessContext anon = AccessContext.anonymous();
String anonResult = service.maskDynamic(log, anon);

// 自定义权限
AccessContext custom = AccessContext.of("user1", "CUSTOM");
custom.addPermission("sensitive:partial:phone");  // 手机号部分可见
String customResult = service.maskDynamic(log, custom);
```

## 脱敏审计

记录所有脱敏操作和原因，支持审计追溯：

```java
LogDesensitizationService service = new LogDesensitizationService();

// 设置审计存储（持久化到文件）
service.setAuditStorage(new FileAuditStorage("/var/log/audit/mask-audit.log"));

// 执行脱敏操作（自动记录审计）
service.maskDynamic("手机号: 13812345678", AccessContext.anonymous());
service.scan("日志内容...");

// 查看审计统计
AuditStatistics stats = service.getAuditStatistics();
System.out.println(stats.toTextReport());

// 按操作人查询
List<AuditRecord> adminOps = service.getAuditLogger().getRecordsByOperator("admin1");

// 按操作类型查询
List<AuditRecord> discoveries = service.getAuditLogger().getRecordsByAction(MaskAction.DISCOVER);

// 导出审计记录
String export = service.getAuditLogger().exportAsText();
service.getAuditLogger().exportToFile("audit-export.txt");
```

**审计操作类型**:

| 操作 | 说明 | 自动触发场景 |
|------|------|-------------|
| MASK_COMPLETE | 完全脱敏 | 匿名用户访问 |
| MASK_PARTIAL | 部分脱敏 | 操作员访问 |
| MASK_DYNAMIC | 动态脱敏 | 任何动态脱敏操作 |
| DISCOVER | 敏感发现 | 扫描发现敏感数据 |
| RULE_ADD | 规则新增 | 添加自定义规则 |
| RULE_REMOVE | 规则删除 | 删除规则 |
| RULE_MODIFY | 规则修改 | 修改规则配置 |

## 支持的敏感信息类型（按优先级排序）

| 优先级 | 类型 | 示例 | 脱敏结果 |
|--------|------|------|----------|
| 100 | 密码 | `password=123456` | `password=******` |
| 90 | 身份证号 | `110101199001011234` | `110101********1234` |
| 85 | 银行卡号 | `6222021234567890123` | `6222********0123` |
| 80 | 手机号 | `13812345678` | `138****5678` |
| 70 | 邮箱 | `test@example.com` | `***@example.com` |
| 60 | 姓名 | `姓名=张三` | `姓名=*张三` |

> **优先级说明**: 数字越大优先级越高，高优先级规则先执行。

## DFA vs NFA 性能对比

| 特性 | DFA 引擎 | NFA 引擎 |
|------|----------|----------|
| 大日志处理 | 快 10-100 倍 | 标准速度 |
| 内存使用 | 预编译，低 | 动态匹配，较高 |
| 正则复杂度 | 支持简单正则 | 支持完整正则语法 |
| 回溯问题 | 无回溯 | 可能存在回溯 |
| 适用场景 | 大日志批量处理 | 复杂正则匹配 |

## Flume 集成

### 使用 Interceptor

```properties
agent.sources.source1.interceptors = masking
agent.sources.source1.interceptors.masking.type = com.log.mask.flume.MaskingInterceptor$Builder
agent.sources.source1.interceptors.masking.log.format = text
agent.sources.source1.interceptors.masking.config.file = mask-config.properties
```

### 使用 Sink

```properties
agent.sinks.sink1.type = com.log.mask.flume.MaskingSink
agent.sinks.sink1.log.format = json
agent.sinks.sink1.config.file = mask-config.properties
```

## 自定义脱敏规则

在 `mask-config.properties` 中添加自定义规则：

```properties
log.format=text
rules.default.enable=true
regex.engine=dfa

# 自定义规则（带优先级）
rules.custom.1.name=orderNo
rules.custom.1.regex=orderNo[=:]['\"]?(\d{8,16})['\"]?
rules.custom.1.groupIndex=1
rules.custom.1.replacement=***
rules.custom.1.priority=50
rules.custom.1.enabled=true
```

## Java API 完整使用

```java
LogDesensitizationService service = new LogDesensitizationService();

// 基础脱敏
String masked = service.mask("用户: 张三, 电话: 13812345678", "text");

// 动态脱敏
String dynamicMasked = service.maskDynamic(log, AccessContext.operator("user1"));

// 敏感信息扫描
DiscoveryReport report = service.scan(logContent);

// 审计配置
service.setAuditStorage(new FileAuditStorage("/var/log/audit.log"));
AuditStatistics stats = service.getAuditStatistics();

// 添加自定义规则（带优先级）
service.addCustomRule(new MaskRule("custom", "custom=(\\w+)", 1, "***", 50));

// 引擎切换
service.getRuleEngine().getMaskEngine().setUseDFA(true);  // DFA 高性能
service.getRuleEngine().getMaskEngine().setUseDFA(false); // NFA 兼容模式

// 性能测试
String report = service.getRuleEngine().getMaskEngine()
    .getPerformanceReport(bigLog, 1000);
```

## 项目结构

```
src/main/java/com/log/mask/
├── core/                        # 核心脱敏引擎
│   ├── dfa/
│   │   └── DFAMatcher.java      # DFA 正则匹配器
│   ├── MaskPattern.java         # 预设脱敏模式（含优先级）
│   ├── MaskRule.java            # 脱敏规则类（含优先级）
│   └── RegexMaskEngine.java     # 正则脱敏引擎（支持 DFA/NFA）
├── parser/                      # 日志解析器
│   ├── LogParser.java           # 解析器接口
│   ├── TextLogParser.java       # 文本解析器
│   ├── JsonLogParser.java       # JSON 解析器（完整递归遍历）
│   ├── XmlLogParser.java        # XML 解析器
│   └── LogParserFactory.java    # 解析器工厂
├── discovery/                   # 敏感信息发现
│   ├── SensitiveDataFinder.java # 敏感数据扫描引擎
│   ├── SensitivePattern.java    # 扫描模式定义
│   ├── SensitiveLevel.java      # 风险等级枚举
│   ├── SensitiveDataItem.java   # 发现项数据模型
│   └── DiscoveryReport.java     # 扫描报告（含风险等级）
├── dynamic/                     # 动态脱敏
│   ├── AccessContext.java       # 访问上下文（角色+权限）
│   ├── MaskPolicy.java          # 脱敏策略枚举
│   ├── DynamicMaskEngine.java   # 动态脱敏引擎
│   └── DataTypeMaskConfig.java  # 数据类型脱敏配置
├── audit/                       # 脱敏审计
│   ├── AuditLogger.java         # 审计日志记录器
│   ├── AuditRecord.java         # 审计记录模型
│   ├── AuditStorage.java        # 审计存储接口
│   ├── FileAuditStorage.java    # 文件审计存储实现
│   ├── AuditStatistics.java     # 审计统计报告
│   └── MaskAction.java          # 审计操作类型枚举
├── rule/                        # 规则引擎
│   └── RuleEngine.java          # 规则管理引擎（按优先级排序）
├── config/                      # 配置模块
│   └── MaskConfig.java          # 配置类
├── flume/                       # Flume 集成
│   ├── MaskingSink.java         # 脱敏 Sink
│   └── MaskingInterceptor.java  # 脱敏 Interceptor
├── LogDesensitizationService.java # 服务门面类
└── Main.java                    # 命令行入口
```

## 许可证

MIT License
