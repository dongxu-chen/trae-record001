# 数据库死锁检测分析工具

一个用于捕获、解析和分析MySQL/PostgreSQL死锁日志的Web工具，提供可视化的事务等待关系图和智能优化建议。

## 功能特性

### 🔍 死锁日志解析
- 支持MySQL InnoDB死锁日志（`SHOW ENGINE INNODB STATUS`）
- 支持PostgreSQL死锁日志
- 提取事务ID、状态、等待时间
- 解析持有的锁和等待的锁
- 提取涉及的SQL语句

### 📊 统计分析
- **按表统计**: 统计各表参与死锁的频率
- **按SQL模式统计**: 归一化SQL语句，识别高频死锁SQL模式
- **锁模式统计**: 分析共享锁、排他锁、意向锁的分布
- **时间段统计**: 分析死锁发生的时间分布规律
- **热点表识别**: 识别参与超过30%死锁的热点表

### 📈 事务等待关系图
- 使用NetworkX构建有向图（事务 → 锁 → 事务）
- 使用Cytoscape.js前端可视化
- 支持单死锁视图和全局视图
- 可导出PNG图片
- 点击节点查看详细信息

### 💡 智能优化建议
- **索引优化**: 检测缺少索引的表，建议添加合适索引
- **事务顺序**: 识别不一致的表访问顺序
- **锁模式**: 分析排他锁使用过多的问题
- **长事务**: 检测长时间锁等待
- **热点表**: 提供热点表优化方案
- **SQL优化**: 识别有问题的SQL模式（缺少WHERE条件、不必要的FOR UPDATE等）

## 技术栈

- **后端**: Python 3.8+, Flask
- **死锁解析**: 正则表达式 + sqlparse
- **图分析**: NetworkX
- **前端**: Bootstrap 5 + Cytoscape.js + Chart.js
- **可视化**: 交互式关系图 + 统计图表

## 项目结构

```
├── app.py                          # Flask Web应用主程序
├── requirements.txt                # Python依赖
├── deadlock_parser/                # 死锁日志解析模块
│   ├── __init__.py
│   ├── base_parser.py              # 基础解析类和数据结构
│   ├── mysql_parser.py             # MySQL死锁解析器
│   └── postgresql_parser.py        # PostgreSQL死锁解析器
├── deadlock_analyzer/              # 死锁分析模块
│   ├── __init__.py
│   ├── analyzer.py                 # 统计分析器
│   ├── graph_generator.py          # 关系图生成器（NetworkX）
│   └── optimizer.py                # 优化建议生成器
├── templates/                      # HTML模板
│   └── index.html                  # 主页面
├── static/                         # 静态资源
│   ├── css/style.css               # 样式表
│   └── js/app.js                   # 前端交互逻辑
├── sample_logs/                    # 示例死锁日志
│   ├── mysql_sample.log            # MySQL示例
│   └── postgresql_sample.log       # PostgreSQL示例
└── uploads/                        # 上传文件临时目录
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动应用

```bash
python app.py
```

应用将在 `http://localhost:5000` 启动。

### 3. 使用说明

1. **选择数据库类型**: MySQL或PostgreSQL
2. **输入死锁日志**:
   - 直接粘贴日志内容到文本框
   - 或上传日志文件
   - 或点击顶部按钮加载示例日志
3. **点击"开始分析"**
4. **查看分析结果**:
   - **死锁列表**: 查看每个死锁的事务详情、持有锁、等待锁、SQL语句
   - **等待关系图**: 可视化事务与锁的依赖关系
   - **统计分析**: 按表、时间段、锁模式的统计图表
   - **优化建议**: 智能生成的优化建议，按优先级排序

## 获取死锁日志

### MySQL

执行以下SQL获取InnoDB状态，其中包含最近的死锁信息：

```sql
SHOW ENGINE INNODB STATUS\G
```

确保已开启死锁日志：

```sql
SET GLOBAL innodb_print_all_deadlocks = 1;
```

### PostgreSQL

确保已配置死锁日志（在`postgresql.conf`中）：

```conf
log_error_verbosity = 'verbose'
log_min_messages = 'debug1'
log_statement = 'all'
```

死锁信息会自动记录到服务器日志文件中。

## 核心模块说明

### 数据结构

```python
@dataclass
class Lock:
    lock_type: str           # RECORD, TABLE, RELATION, TUPLE
    lock_mode: str           # X, S, IS, IX, X,GAP等
    table_name: str
    index_name: Optional[str]
    record_info: Optional[str]

@dataclass
class Transaction:
    txn_id: str
    status: str              # WAITING, HOLDING, ACTIVE
    start_time: Optional[datetime]
    wait_time: Optional[int]  # 等待时间（秒）
    sql_statements: List[str]
    holding_locks: List[Lock]
    waiting_lock: Optional[Lock]

@dataclass
class Deadlock:
    timestamp: Optional[datetime]
    transactions: List[Transaction]
    victim_txns: List[str]    # 被选中牺牲的事务ID
    raw_log: str
```

### 图模型说明

- **节点类型**:
  - 🔴 死锁节点（octagon）
  - 🔵 事务节点（roundrectangle），橙色表示被选中牺牲
  - 🟢 锁节点（diamond）

- **边类型**:
  - 灰色：死锁 → 事务（涉及）
  - 蓝色虚线：事务 → 锁（等待）
  - 绿色：锁 → 事务（被持有）
  - 蓝色：事务 → 锁（持有）

## 死锁优化最佳实践

1. **保持事务短小**: 减少锁持有时间
2. **统一访问顺序**: 所有事务按相同顺序访问表
3. **合理使用索引**: 避免全表扫描导致的大范围锁
4. **降低隔离级别**: 业务允许时使用READ COMMITTED
5. **避免大事务**: 拆分为多个小事务
6. **使用NOWAIT/SKIP LOCKED**: 避免不必要的等待
7. **热点表优化**: 分库分表或引入缓存

## License

MIT License
