# 用户流失预警系统 (User Churn Prediction System)

基于生存分析模型（Cox回归）的实时用户流失预警系统，整合Kafka、Flink、Redis、Spark等大数据组件，实现高风险用户识别、智能触达策略推荐和A/B测试闭环。

## 系统架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Kafka Producer │────▶│  Flink Stream   │────▶│  Cox PH Model   │
│  (事件生成器)   │     │  Processing     │     │  (生存分析)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
          │                        │                        │
          ▼                        ▼                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  User Events    │     │  Redis Cache    │     │  High Risk      │
│  Topics         │     │  (用户画像)     │◀────│  User Tagging   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                 │                        │
                                 ▼                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Spark Batch    │     │  Recommendation │     │  A/B Testing    │
│  Feature Eng.   │◀────│  Engine         │────▶│  Framework      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 核心功能

### 1. 实时数据处理 (Kafka + Flink)
- **Kafka事件生产者**：模拟生成用户行为事件（登录、浏览、购买、点击、退出、错误等）
- **Flink流处理**：实时聚合多时间窗口特征，计算用户活跃度指标
- **多窗口分析**：支持1天、7天、14天、30天滑动窗口统计

### 2. 生存分析模型 (Lifelines + Cox回归)
- **Cox比例风险模型**：基于生存分析预测用户流失风险
- **输出指标**：
  - 流失概率 (Churn Probability)
  - 风险等级 (Risk Level: high/medium/low)
  - 预计剩余天数 (Expected Days to Churn)
  - 风险比 (Hazard Ratio)
  - 生存分位数 (Survival Quantiles)

### 3. 批量特征工程 (Spark)
- 自动生成合成训练数据
- 多维度特征提取（行为特征、用户属性、活跃度指标）
- 特征预处理（标准化、编码）
- 5折交叉验证评估模型性能

### 4. 用户画像与缓存 (Redis)
- 用户画像存储（等级、地区、渠道、消费金额）
- 风险评分实时缓存
- 高风险用户标记集合
- 触达动作历史记录
- 通知队列管理
- 支持内存回退模式（无需Redis即可运行）

### 5. 触达策略推荐引擎
- **风险分层**：根据流失概率分为高、中、低风险
- **智能推荐**：基于用户特征和历史效果选择最优策略
- **多渠道触达**：支持推送、邮件、短信、应用内消息
- **渠道ROI优化**：基于历史效果选择最佳触达渠道
- **动作冷却机制**：防止过度打扰用户

### 6. A/B测试框架
- 实验创建与管理（草稿/运行/暂停/完成）
- 确定性用户分流（哈希算法保证一致性）
- 多指标跟踪（转化率、留存率、参与度）
- 统计显著性检验（卡方检验、Z检验）
- 置信区间计算
- 优胜变体自动识别

## 目录结构

```
record001/339/
├── config/
│   └── config.yaml              # 系统配置文件
├── src/
│   ├── __init__.py
│   ├── main.py                   # 系统入口
│   ├── common/
│   │   ├── __init__.py
│   │   ├── logger.py             # 日志模块
│   │   └── utils.py              # 工具函数
│   ├── kafka/
│   │   ├── __init__.py
│   │   ├── event_producer.py     # 事件生产者
│   │   └── event_consumer.py     # 事件消费者
│   ├── flink/
│   │   ├── __init__.py
│   │   └── stream_processor.py   # 流处理引擎
│   ├── spark/
│   │   ├── __init__.py
│   │   └── feature_engineering.py # 特征工程
│   ├── model/
│   │   ├── __init__.py
│   │   └── cox_model.py          # Cox回归模型
│   ├── redis/
│   │   ├── __init__.py
│   │   └── cache_manager.py      # 缓存管理器
│   ├── strategy/
│   │   ├── __init__.py
│   │   └── recommendation_engine.py # 推荐引擎
│   └── ab_testing/
│       ├── __init__.py
│       └── ab_test_manager.py    # A/B测试管理器
├── data/                         # 数据目录
├── models/                       # 模型目录
└── logs/                         # 日志目录
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行完整演示

无需任何外部依赖即可运行（使用内存回退模式）：

```bash
cd src
python main.py --mode demo
```

演示将自动完成以下步骤：
1. 生成合成用户数据（100用户，5000事件，30%流失率）
2. 提取并预处理特征
3. 训练Cox比例风险模型
4. 模拟实时预测
5. 创建并运行A/B测试
6. 展示系统统计信息

### 3. 训练模型

```bash
cd src
python main.py --mode train --num-users 1000 --num-events 50000
```

### 4. 单用户预测

```bash
cd src
python main.py --mode predict
```

### 5. 完整系统（需要Kafka）

```bash
cd src
python main.py --mode full --events-per-second 50
```

### 6. 使用Redis

```bash
# 确保Redis服务运行在 localhost:6379
cd src
python main.py --mode demo --use-redis
```

## 模型说明

### Cox比例风险模型

Cox模型是生存分析中最常用的半参数模型，用于分析多个协变量对生存时间的影响。

**风险函数**：
```
h(t|X) = h₀(t) * exp(Xβ)
```

其中：
- `h₀(t)` 是基准风险函数
- `Xβ` 是协变量的线性组合
- `exp(βᵢ)` 是风险比（Hazard Ratio）

**模型输出解释**：
- **流失概率**：预测窗口内（默认30天）用户流失的概率
- **风险比**：用户相对于基准用户的相对风险
- **预计剩余天数**：基于生存曲线计算的期望生存时间
- **生存分位数**：25%、50%、75%分位的生存时间

### 模型评估指标

- **C-index (Concordance Index)**：衡量模型预测排序准确性，范围[0.5, 1.0]，值越大越好
- **Log-Rank检验**：检验组间生存曲线差异的显著性
- **5折交叉验证**：评估模型的泛化能力

## 触达策略矩阵

| 风险等级 | 策略类型 | 推荐动作 | 优先级 |
|---------|---------|---------|--------|
| 高风险 | 积极干预 | 专属优惠、个性化折扣、客服回访 | 10-8 |
| 中风险 | 常规运营 | 精选内容、新功能介绍、积分提醒 | 7-5 |
| 低风险 | 信息触达 | 系统公告、新功能通知 | 4-3 |

## 配置说明

主要配置项位于 `config/config.yaml`：

```yaml
model:
  high_risk_threshold: 0.7      # 高风险阈值
  medium_risk_threshold: 0.4    # 中风险阈值
  prediction_window_days: 30    # 预测窗口

strategy:
  action_cooldown_hours: 48     # 动作冷却时间
  notification_channels: ["push", "email", "sms", "in_app"]

ab_testing:
  confidence_level: 0.95        # 统计显著性水平
  min_sample_size: 100          # 最小样本量
```

## 各模块独立运行

### Kafka事件生产者

```bash
cd src/kafka
python event_producer.py
```

### Cox模型训练

```bash
cd src/model
python cox_model.py
```

### 推荐引擎

```bash
cd src/strategy
python recommendation_engine.py
```

### A/B测试管理

```bash
cd src/ab_testing
python ab_test_manager.py
```

### 缓存管理

```bash
cd src/redis
python cache_manager.py
```

## 生产部署建议

1. **Kafka集群**：至少3个节点，配置复制因子为3
2. **Flink集群**：配置检查点和状态后端
3. **Redis集群**：使用哨兵或集群模式保证高可用
4. **Spark集群**：按需分配资源进行批量特征计算
5. **监控告警**：
   - 监控Kafka消息堆积
   - 监控模型预测延迟
   - 监控高风险用户数量异常波动
   - 设置A/B测试显著性告警

## 数据隐私与合规

- 所有用户数据支持加密存储
- 支持数据脱敏处理
- 触达策略遵循最小必要原则
- 提供用户数据导出和删除接口

## 技术栈

| 组件 | 版本要求 | 用途 |
|------|---------|------|
| Python | 3.8+ | 开发语言 |
| Lifelines | 0.27+ | 生存分析 |
| Kafka | 2.8+ | 消息队列 |
| Apache Flink | 1.15+ | 流处理 |
| Redis | 6.0+ | 缓存 |
| Spark | 3.3+ | 批处理 |
| scikit-learn | 1.0+ | 特征预处理 |
| pandas | 1.3+ | 数据处理 |

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交Issue。
