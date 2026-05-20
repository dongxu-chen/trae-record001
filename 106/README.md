# 分布式任务调度中心

基于 Spring Boot + Quartz + MySQL 实现的分布式任务调度中心后端服务。

## 技术栈

- Spring Boot 2.7.x
- Quartz 2.3.x (持久化JobStore)
- MySQL 8.x
- Spring Data JPA
- **Raft 一致性协议** (Leader选举 + 高可用)

## 核心架构

### Raft分布式调度架构
```
┌─────────────────────────────────────────────────────────────────────┐
│                        Raft Cluster (3+ Nodes)                        │
├──────────────┬──────────────┬──────────────┬──────────────┬─────────┤
│   Node 1     │   Node 2     │   Node 3     │   Node N     │         │
│  [LEADER]    │ [FOLLOWER]   │ [FOLLOWER]   │ [FOLLOWER]   │         │
│  ┌────────┐  │  ┌────────┐  │  ┌────────┐  │  ┌────────┐  │         │
│  │Quartz  │  │  │Quartz  │  │  │Quartz  │  │  │Quartz  │  │         │
│  │Active  │  │  │Paused  │  │  │Paused  │  │  │Paused  │  │         │
│  └────────┘  │  └────────┘  │  └────────┘  │  └────────┘  │         │
└──────────────┴──────────────┴──────────────┴──────────────┴─────────┘
                                    │
                                    ▼
                        ┌──────────────────────┐
                        │   MySQL (JobStore)   │
                        │   任务持久化存储       │
                        └──────────────────────┘
```

### 核心特性：
1. **Leader 选举**: 基于Raft协议自动选举，只有Leader执行调度
2. **自动故障转移**: Leader故障时自动重新选举，任务不丢失
3. **请求转发**: Follower节点自动转发所有任务请求到Leader
4. **动态扩缩容**: 支持节点动态加入/退出集群

## 功能特性

1. **定时任务CRUD接口**
   - 创建任务（Job名、Cron表达式、执行类）
   - 修改任务Cron表达式
   - 删除任务
   - 查询任务列表和详情

2. **任务依赖管理（DAG）**
   - 支持设置任务前置依赖
   - 前置任务执行成功后才触发当前任务
   - 支持复杂的任务依赖链

3. **失败重试策略**
   - 支持配置重试次数（默认0次）
   - 支持配置重试间隔（默认30秒）
   - 自动记录重试历史

4. **任务超时控制**
   - 支持设置任务超时时间
   - 超时自动标记任务状态

5. **任务触发执行记录存储**
   - 自动记录每次任务执行情况
   - 记录执行状态、结果、完整异常堆栈、耗时
   - 支持分页查询执行记录

6. **手动触发任务接口**
   - 支持立即手动触发任务执行

7. **暂停/恢复任务接口**
   - 支持暂停任务调度
   - 支持恢复已暂停的任务

8. **任务依赖关系可视化**
   - 提供图结构数据接口
   - 展示任务节点和依赖边
   - 方便前端绘制DAG图

9. **Raft分布式高可用**
   - ⭐ **Leader选举**: 自动选举调度节点，避免脑裂
   - ⭐ **任务不丢失**: Leader故障自动转移，任务调度不中断
   - ⭐ **请求自动转发**: Follower接收请求自动转发到Leader
   - ⭐ **动态集群管理**: 支持节点动态加入/退出

## 项目结构

```
src/main/java/com/scheduler/
├── TaskSchedulerApplication.java      # 启动类
├── common/
│   └── Result.java                    # 统一返回结果
├── config/
│   ├── QuartzConfig.java              # Quartz配置
│   ├── GlobalExceptionHandler.java    # 全局异常处理
│   ├── LeaderForwardInterceptor.java  # 请求转发拦截器
│   └── WebConfig.java                 # Web配置
├── controller/
│   ├── ClusterController.java         # 集群管理接口
│   ├── JobController.java             # 任务管理接口
│   └── JobExecuteRecordController.java # 执行记录接口
├── dto/
│   ├── JobDTO.java                    # 任务数据传输对象
│   └── JobDependencyGraph.java        # 任务依赖图
├── entity/
│   ├── JobConfig.java                 # 任务配置（重试、超时、依赖）
│   ├── JobExecuteRecord.java          # 执行记录实体
│   └── JobRetryRecord.java            # 重试记录实体
├── job/
│   ├── BaseJob.java                   # 任务基类（自动记录执行）
│   ├── SampleJob.java                 # 示例任务
│   └── TestErrorJob.java              # 测试异常任务
├── raft/
│   ├── RaftNode.java                  # Raft节点核心
│   ├── RaftMessage.java               # Raft消息定义
│   ├── RaftLogEntry.java              # Raft日志条目
│   ├── RaftLog.java                   # Raft日志管理
│   ├── SchedulerManager.java          # 调度器管理器
│   ├── ClusterManager.java            # 集群管理器
│   └── LeaderForwarder.java           # Leader请求转发器
├── repository/
│   ├── JobConfigRepository.java
│   ├── JobExecuteRecordRepository.java
│   └── JobRetryRecordRepository.java
├── service/
│   ├── JobService.java                # 任务服务
│   └── JobExecuteRecordService.java   # 执行记录服务
└── util/
    ├── CronUtils.java                 # Cron表达式校验
    └── QuartzManager.java             # Quartz工具类
```

## 数据库配置

1. 创建数据库：
```sql
CREATE DATABASE IF NOT EXISTS task_scheduler DEFAULT CHARACTER SET utf8mb4;
```

2. 执行数据库初始化脚本：
```
src/main/resources/quartz_tables_mysql.sql
```

3. 修改 `application.yml` 中的数据库连接信息：
```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/task_scheduler?useUnicode=true&characterEncoding=utf8&useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true
    username: root
    password: your_password
```

## API接口文档

### 任务管理接口

#### 1. 创建任务（支持依赖、重试、超时配置）
- **URL**: `POST /api/job`
- **请求体**:
```json
{
  "jobName": "testJob",
  "jobGroup": "DEFAULT",
  "cronExpression": "0/5 * * * * ?",
  "jobClassName": "com.scheduler.job.SampleJob",
  "description": "测试任务",
  "retryCount": 3,
  "retryInterval": 30000,
  "timeoutSeconds": 300,
  "dependsOn": ["jobA:DEFAULT", "jobB:DEFAULT"]
}
```
- **参数说明**:
  - `retryCount`: 失败重试次数，默认0
  - `retryInterval`: 重试间隔（毫秒），默认30000
  - `timeoutSeconds`: 超时时间（秒），默认300
  - `dependsOn`: 依赖的任务列表，格式：`jobName:jobGroup`

#### 2. 修改任务
- **URL**: `PUT /api/job`
- **请求体**: 同上

#### 3. 删除任务
- **URL**: `DELETE /api/job?jobName=testJob&jobGroup=DEFAULT`

#### 4. 暂停任务
- **URL**: `POST /api/job/pause?jobName=testJob&jobGroup=DEFAULT`

#### 5. 恢复任务
- **URL**: `POST /api/job/resume?jobName=testJob&jobGroup=DEFAULT`

#### 6. 手动触发任务
- **URL**: `POST /api/job/trigger?jobName=testJob&jobGroup=DEFAULT`

#### 7. 查询单个任务
- **URL**: `GET /api/job?jobName=testJob&jobGroup=DEFAULT`

#### 8. 查询所有任务
- **URL**: `GET /api/job/list`

#### 9. 获取任务依赖关系图
- **URL**: `GET /api/job/dependency-graph`
- **返回示例**:
```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "nodes": [
      {
        "id": "DEFAULT:testJob",
        "name": "testJob",
        "group": "DEFAULT",
        "status": "NORMAL",
        "cronExpression": "0/5 * * * * ?",
        "retryCount": 3,
        "timeoutSeconds": 300
      }
    ],
    "edges": [
      {
        "source": "DEFAULT:jobA",
        "target": "DEFAULT:testJob",
        "label": "depends on"
      }
    ]
  }
}
```

### 执行记录接口

#### 查询执行记录
- **URL**: `GET /api/job/record/list?jobName=testJob&page=0&size=10`

## Cron表达式说明

常用Cron表达式示例：
- `0 0 12 * * ?`       每天中午12点执行
- `0 0 12 * * ? 2025`  2025年每天中午12点执行
- `0 0/5 12 * * ?`     每天12点到12:55之间每5分钟执行
- `0 0 12 L * ?`       每月最后一天中午12点执行
- `0 0 12 ? * MON-FRI` 每周一至周五中午12点执行

## 自定义任务开发

1. 创建任务类继承 `BaseJob`
2. 实现 `executeInternal` 方法
3. 添加 `@Component` 注解

示例：
```java
@Component
public class MyCustomJob extends BaseJob {
    @Override
    protected String executeInternal(JobExecutionContext context) throws Exception {
        // 业务逻辑
        return "执行成功";
    }
}
```

## 启动项目

```bash
mvn clean install
mvn spring-boot:run
```

项目启动后访问：`http://localhost:8080`

## 集群部署

配置说明：
1. 多个实例连接同一个数据库
2. `application.yml` 中已配置集群模式
3. `instanceId: AUTO` 自动生成实例ID
4. `clusterCheckinInterval: 10000` 集群检查间隔10秒

注意事项：
- 确保所有实例的系统时间同步
- Job类必须在所有实例上存在
