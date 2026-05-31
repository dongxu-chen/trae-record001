# 分布式ID生成器压力测试工具

一个用于测试分布式ID生成算法性能的全栈工具，支持高并发场景下的QPS、延迟和唯一性测试。

## ✨ 功能特性

### 核心功能
- ✅ **多算法支持**: 雪花算法(Snowflake)、号段模式、随机ID
- ⚡ **高并发测试**: 支持多线程并发压力测试
- 📊 **实时监控**: WebSocket实时推送QPS、延迟等指标
- 📈 **可视化图表**: ECharts展示QPS趋势和延迟分位统计
- 📄 **报告导出**: 支持JSON/CSV格式导出测试报告
- 🎨 **现代化UI**: React + Ant Design + TailwindCSS

### 🔍 低内存唯一性校验 (布隆过滤器 + 抽样)
- 布隆过滤器进行快速重复检测
- 智能抽样策略，平衡性能与准确性
- 相比全量存储节省 **95%+** 内存
- 支持自定义误判率和抽样数量
- 估计重复率 + 抽样重复率双重校验

### ⏰ 时钟异常场景模拟
- **正常模式**: 使用真实系统时间
- **时钟漂移**: 模拟时钟逐渐偏移场景
- **时钟回拨**: 随机触发时钟回拨事件
- **混合模式**: 同时模拟漂移和回拨
- 完整记录等待次数和恢复时间

### 📋 优化报告结构
- 汇总统计 + 采样详情，减少渲染数据
- 性能分Tab展示（总览/唯一性/时钟/内存/采样数据）
- 延迟统计：P50/P90/P95/P99/P999多维度
- 内存使用统计和优化率展示
- 错误计数和成功率统计

## 🏗️ 技术架构

### 后端
- Java 17+
- Spring Boot 3.2
- WebSocket (STOMP)
- Maven
- 虚拟线程 (Virtual Threads)

### 前端
- React 18
- TypeScript
- Vite
- TailwindCSS 3
- Ant Design 5
- ECharts
- Zustand

## 📁 项目结构

```
id-generator-benchmark/
├── backend/                    # Java后端
│   ├── src/main/java/com/benchmark/
│   │   ├── generator/          # ID生成器实现
│   │   │   ├── BloomFilter.java              # 布隆过滤器
│   │   │   ├── SamplingUniquenessChecker.java # 抽样校验器
│   │   │   ├── SnowflakeIdGenerator.java     # 雪花算法(支持时钟模拟)
│   │   │   ├── SegmentIdGenerator.java       # 号段模式
│   │   │   ├── RandomIdGenerator.java        # 随机ID
│   │   │   └── IdGeneratorFactory.java       # 工厂类
│   │   ├── service/            # 业务服务
│   │   │   └── TestEngineService.java        # 压力测试引擎
│   │   ├── controller/         # REST API
│   │   ├── config/             # 配置类
│   │   ├── dto/                # 数据传输对象
│   │   └── Application.java    # 启动类
│   └── pom.xml
└── frontend/                   # React前端
    ├── src/
    │   ├── components/         # 组件
    │   ├── pages/              # 页面
    │   ├── store/              # 状态管理
    │   ├── utils/              # 工具函数
    │   └── types/              # 类型定义
    └── package.json
```

## 🚀 快速开始

### 前置要求

- JDK 17+
- Maven 3.6+
- Node.js 18+
- npm 9+

### 启动后端服务

```bash
cd backend
mvn clean package
java -jar target/id-generator-benchmark-1.0.0.jar
```

后端服务将在 http://localhost:8080 启动

### 启动前端服务

```bash
cd frontend
npm install
npm run dev
```

前端服务将在 http://localhost:3000 启动

## 📖 使用说明

### 1. 配置测试参数

#### 基础配置
- 选择ID生成算法（雪花/号段/随机）
- 设置并发线程数（1-100）
- 设置测试时长（1-60秒）

#### 雪花算法高级配置
- **Worker ID / Datacenter ID**: 0-31
- **时钟模拟模式**:
  - 正常时钟
  - 时钟漂移（时钟逐渐偏移）
  - 时钟回拨（随机触发回拨）
  - 混合模式（漂移+回拨）
- **时钟偏移量**: 1-1000ms
- **回拨概率**: 0.01%-10%

#### 唯一性校验配置
- **采样数量**: 1000-100000
- **布隆过滤器误判率**: 0.01% / 0.1% / 1% / 5%

### 2. 执行测试

点击"开始压力测试"按钮，系统将：
- 启动指定数量的并发线程
- 持续生成ID并收集性能数据
- 通过WebSocket实时推送监控数据
- 布隆过滤器实时检测重复

### 3. 查看监控

在监控页面可以实时查看：
- 当前QPS（每秒查询率）
- 平均延迟、P50/P95/P99分位延迟
- 已生成ID总数
- 测试进度条

### 4. 查看报告

测试完成后，在报告页面可以查看：

#### 📊 总览 Tab
- 性能汇总（生成总数、成功/失败数、QPS统计）
- QPS和延迟趋势图（基于采样数据，最多60点）
- 延迟分位统计（Min/Avg/P50/P90/P95/P99/P999/Max/StdDev）

#### 🔍 唯一性校验 Tab
- 校验结果（通过/失败）
- 布隆过滤器检测重复数
- 抽样检测重复数
- 估计重复率、抽样重复率、调整后重复率
- 内存占用和节省比例
- 重复ID详情列表（最多100个）
- 抽样ID示例（最多50个）

#### ⏰ 时钟模拟 Tab
- 时钟模式展示
- 漂移次数、回拨次数统计
- 总漂移量、总回拨量
- 强制等待次数和总等待时间
- 回拨事件告警

#### 💾 内存使用 Tab
- 峰值内存、平均内存
- 节省内存估算
- 内存优化率进度条

#### 📋 采样数据 Tab
- 性能指标采样数据表（分页）
- 时间、QPS、各分位延迟、进度

## 🔧 API 接口

### REST API

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/test/start | 启动压力测试 |
| GET  | /api/test/stop/{testId} | 停止测试 |
| GET  | /api/test/{testId} | 获取测试报告 |
| GET  | /api/test/list | 获取历史报告列表 |
| GET  | /api/report/{testId}/export | 导出报告 |

### WebSocket

- 连接端点: `/ws`
- 订阅主题: `/topic/test/{testId}/metrics` (实时指标)
- 订阅主题: `/topic/test/{testId}/complete` (测试完成)

## 💡 核心技术说明

### 布隆过滤器原理
使用MurmurHash实现的布隆过滤器，根据预期插入量和误判率自动计算最优bit数组大小和哈希函数数量。

**内存估算公式**:
```
m = -n * ln(p) / (ln(2))²
k = m/n * ln(2)
```
- m: bit数组大小
- n: 预期插入数量
- p: 误判率
- k: 哈希函数数量

### 时钟模拟机制
通过自定义ClockSimulator类包装时间获取，支持：
1. **时钟漂移**: 每生成1000个ID，时钟偏移增加指定量
2. **时钟回拨**: 按概率随机触发时钟回拨
3. **混合模式**: 结合漂移和回拨

### 抽样策略
采用三阶段动态抽样：
1. 早期（<10%样本）: 高密度抽样（10x采样率）
2. 中期（<50%样本）: 中密度抽样（2x采样率）
3. 后期: 等概率随机抽样

## 📊 ID生成算法说明

### 雪花算法 (Snowflake)
- 64位有序ID
- 结构：时间戳(41bit) + 数据中心ID(5bit) + 机器ID(5bit) + 序列号(12bit)
- 优点：有序、高性能、分布式唯一
- 缺点：依赖系统时钟，时钟回拨会产生重复ID

### 号段模式 (Segment)
- 预分配ID号段，内存中递增
- 优点：性能极高，不依赖时钟
- 缺点：ID有序，容易被推测

### 随机ID (Random)
- 基于SecureRandom生成随机数字
- 优点：无序，安全性高
- 缺点：存在理论重复概率

## 📈 性能指标说明

- **QPS**: 每秒生成的ID数量，越高越好
- **延迟**: 单次ID生成耗时，越低越好
- **P50/P90/P95/P99/P999**: 延迟分位数，反映长尾效应
- **唯一性**: 测试期间生成的ID是否全部唯一
- **StdDev**: 标准差，反映数据波动程度

## 📝 许可证

MIT License
