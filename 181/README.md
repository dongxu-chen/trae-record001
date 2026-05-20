# 智能排班系统后端

基于 Java + Spring Boot + OptaPlanner + MySQL 实现的智能排班系统，支持员工技能管理、偏好设置、工时约束、自动排班生成、冲突检测和排班调整重算。

## 技术栈

- **Java 17**
- **Spring Boot 3.2.0**
- **OptaPlanner 9.44.0.Final** - 约束满足求解引擎
- **Spring Data JPA** - ORM 框架
- **MySQL 8.0+** - 数据库
- **Lombok** - 简化代码

## 核心功能

### 1. 约束满足求解 (Constraint Satisfaction)
- 基于 OptaPlanner 的约束流 (Constraint Streams) 实现
- 支持硬约束、中约束、软约束三层评分体系
- 自动寻找最优排班方案

### 2. 排班冲突检测 (Conflict Detection)
- 时间重叠检测
- 技能不匹配检测
- 工时超限检测
- 不可用日期检测

### 3. 班次轮换规则 (Shift Rotation)
- 避免员工长期固定同一班次
- 支持班次类型多样化
- 工作负载均衡分配

### 4. 排班调整重算 (Schedule Recalculation)
- 支持手动调整后重新优化
- 锁定已确认的排班不被修改
- 增量式重算，保持稳定性

## 约束规则

### 硬约束 (Hard Constraints) - 必须满足
- 技能匹配：员工必须具备班次要求的技能
- 班次不重叠：同一员工不能同时上两个重叠班次
- 每日工时限制：每天工作不超过 8 小时
- 每周工时限制：每周工作不超过 40 小时
- 不可用日期：不能在员工不可用日期排班

### 中约束 (Medium Constraints) - 尽量满足
- 每周最低工时：每周至少 20 小时
- 班次全覆盖：所有班次需求都要分配到人
- 连续工作天数：不超过 5 天

### 软约束 (Soft Constraints) - 优化目标
- 偏好班次：尽量安排员工偏好的班次
- 避免非偏好班次：尽量不安排员工不喜欢的班次
- 工作负载均衡：员工间工作量均匀
- 班次轮换：避免员工长期上同一类型班次

## 项目结构

```
src/main/java/com/smartschedule/
├── SmartScheduleApplication.java    # 启动类
├── config/
│   ├── OptaPlannerConfig.java       # 求解器配置
│   ├── GlobalExceptionHandler.java  # 全局异常处理
│   └── SampleDataInitializer.java   # 示例数据初始化
├── controller/                      # REST API 控制器
│   ├── EmployeeController.java
│   ├── SkillController.java
│   ├── ShiftTypeController.java
│   └── ScheduleController.java
├── service/                         # 业务逻辑层
│   ├── EmployeeService.java
│   ├── SkillService.java
│   ├── ShiftTypeService.java
│   └── ScheduleService.java
├── repository/                      # 数据访问层
│   ├── EmployeeRepository.java
│   ├── SkillRepository.java
│   ├── ShiftTypeRepository.java
│   ├── ScheduleRepository.java
│   ├── ShiftRequirementRepository.java
│   └── ShiftAssignmentRepository.java
├── entity/                          # 数据库实体
│   ├── Employee.java
│   ├── Skill.java
│   ├── ShiftType.java
│   ├── Schedule.java
│   ├── ShiftRequirement.java
│   └── ShiftAssignment.java
├── planner/                         # OptaPlanner 规划实体
│   ├── ScheduleSolution.java        # 规划解决方案
│   ├── PlannerShiftAssignment.java  # 规划实体
│   └── ScheduleConstraintProvider.java  # 约束规则
└── dto/
    └── ApiResponse.java
```

## 数据库表结构

- `skills` - 技能表
- `employees` - 员工表
- `employee_skills` - 员工技能关联表
- `employee_preferred_shifts` - 员工偏好班次
- `employee_unavailable_days` - 员工不可用日期
- `employee_unwanted_shifts` - 员工非偏好班次
- `shift_types` - 班次类型表
- `schedules` - 排班计划表
- `shift_requirements` - 班次需求表
- `shift_assignments` - 排班分配结果表

## 快速开始

### 1. 数据库准备

创建 MySQL 数据库：

```sql
CREATE DATABASE smart_schedule CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 配置数据库连接

修改 `src/main/resources/application.yml`：

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/smart_schedule?useSSL=false&serverTimezone=Asia/Shanghai
    username: your_username
    password: your_password
```

### 3. 运行应用

```bash
mvn spring-boot:run
```

应用启动后会自动创建数据库表结构。

### 4. 初始化示例数据

激活 `demo` profile 自动加载示例数据：

```bash
mvn spring-boot:run -Dspring-boot.run.profiles=demo
```

或者手动执行 `src/main/resources/data.sql` 中的 SQL 脚本。

## API 接口

### 员工管理

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/employees` | 创建员工 |
| GET | `/api/employees` | 获取所有员工 |
| GET | `/api/employees/{id}` | 获取单个员工 |
| GET | `/api/employees/active` | 获取所有在职员工 |
| PUT | `/api/employees/{id}` | 更新员工信息 |
| DELETE | `/api/employees/{id}` | 删除员工 |

### 技能管理

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/skills` | 创建技能 |
| GET | `/api/skills` | 获取所有技能 |
| GET | `/api/skills/{id}` | 获取单个技能 |
| PUT | `/api/skills/{id}` | 更新技能 |
| DELETE | `/api/skills/{id}` | 删除技能 |

### 班次类型管理

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/shift-types` | 创建班次类型 |
| GET | `/api/shift-types` | 获取所有班次类型 |
| GET | `/api/shift-types/active` | 获取所有启用的班次类型 |
| PUT | `/api/shift-types/{id}` | 更新班次类型 |
| DELETE | `/api/shift-types/{id}` | 删除班次类型 |

### 排班管理

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/schedules` | 创建排班计划 |
| GET | `/api/schedules` | 获取所有排班计划 |
| GET | `/api/schedules/{id}` | 获取单个排班计划 |
| DELETE | `/api/schedules/{id}` | 删除排班计划 |
| POST | `/api/schedules/{id}/requirements` | 添加班次需求 |
| GET | `/api/schedules/{id}/requirements` | 获取班次需求列表 |
| POST | `/api/schedules/{id}/generate` | 自动生成排班 |
| GET | `/api/schedules/{id}/assignments` | 获取排班分配结果 |
| PUT | `/api/schedules/assignments/{id}` | 手动调整排班分配 |
| PUT | `/api/schedules/assignments/{id}/lock` | 锁定/解锁排班 |
| POST | `/api/schedules/{id}/lock-before` | 锁定指定日期之前的排班 |
| POST | `/api/schedules/{id}/recalculate` | 重新计算排班 |
| POST | `/api/schedules/{id}/incremental-recalculate` | 增量重算（保留锁定） |
| POST | `/api/schedules/{id}/publish` | 发布排班并推送通知 |
| GET | `/api/schedules/{id}/statistics` | 获取排班统计信息 |

### 日历视图

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/calendar/schedule/{id}` | 获取排班日历视图数据 |
| GET | `/api/calendar/validate/{id}` | 验证排班调整冲突检测 |

### 满意度分析

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/analysis/schedule/{id}/satisfaction` | 获取排班满意度分析报告 |

### 通知管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/notifications/employee/{id}` | 获取员工通知列表 |
| GET | `/api/notifications/schedule/{id}` | 获取排班相关通知 |
| POST | `/api/notifications/send-pending` | 发送待处理通知 |
| POST | `/api/notifications/test/{id}` | 发送测试通知 |

## 使用示例

### 1. 创建排班计划

```bash
curl -X POST http://localhost:8080/api/schedules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "2024年第一周排班",
    "startDate": "2024-01-01",
    "endDate": "2024-01-07",
    "notes": "第一周排班计划"
  }'
```

### 2. 添加班次需求

```bash
curl -X POST http://localhost:8080/api/schedules/1/requirements \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2024-01-01",
    "shiftType": {"id": 1},
    "requiredSkill": {"id": 2},
    "requiredCount": 2
  }'
```

### 3. 自动生成排班

```bash
curl -X POST http://localhost:8080/api/schedules/1/generate
```

### 4. 查看排班结果

```bash
curl http://localhost:8080/api/schedules/1/assignments
```

### 5. 手动调整排班

```bash
curl -X PUT "http://localhost:8080/api/schedules/assignments/1?employeeId=2"
```

### 6. 锁定已确认的排班

```bash
# 锁定单个排班
curl -X PUT "http://localhost:8080/api/schedules/assignments/1/lock?locked=true"

# 锁定指定日期之前的所有排班
curl -X POST "http://localhost:8080/api/schedules/1/lock-before?date=2024-01-03"
```

### 7. 增量重算（只优化未锁定部分）

```bash
curl -X POST http://localhost:8080/api/schedules/1/incremental-recalculate
```

### 8. 调整约束权重（运行时动态调整）

```bash
# 查看所有权重配置
curl http://localhost:8080/api/constraint-weights

# 修改连续夜班的最大允许天数
curl -X PUT "http://localhost:8080/api/constraint-weights/maxConsecutiveNightShiftsLimit?value=3"

# 批量更新权重
curl -X PUT http://localhost:8080/api/constraint-weights \
  -H "Content-Type: application/json" \
  -d '{
    "maxConsecutiveNightShiftsLimit": 3,
    "preferredShiftTypes": 20,
    "balancedWorkload": 8
  }'
```

### 9. 日历视图与拖拽调整

```bash
# 获取排班日历视图数据
curl http://localhost:8080/api/calendar/schedule/1

# 拖拽调整前验证（检测冲突）
curl "http://localhost:8080/api/calendar/validate/1?newEmployeeId=3"
```

### 10. 发布排班（自动推送通知）

```bash
# 发布排班，自动检查完整性和冲突，然后推送通知给所有员工
curl -X POST http://localhost:8080/api/schedules/1/publish
```

### 11. 满意度分析

```bash
# 获取排班满意度分析报告
curl http://localhost:8080/api/analysis/schedule/1/satisfaction
```

### 12. 通知管理

```bash
# 获取员工的通知列表
curl http://localhost:8080/api/notifications/employee/1

# 发送测试通知
curl -X POST "http://localhost:8080/api/notifications/test/1?title=测试通知&content=这是一条测试消息"

# 重新发送待发送的通知
curl -X POST http://localhost:8080/api/notifications/send-pending
```

## 求解器配置

可以在 `OptaPlannerConfig.java` 中调整求解器参数：

```java
.withTerminationConfig(new TerminationConfig()
    .withSecondsSpentLimit(30L)        // 最长求解时间 30 秒
    .withScoreCalculationCountLimit(100000L)  // 最大评分计算次数
    .withBestScoreLimit(HardMediumSoftScore.of(0, 0, 0))  // 目标分数
)
```

## 自定义约束

如需添加新的约束规则，在 `ScheduleConstraintProvider.java` 中添加新方法：

```java
private Constraint customConstraint(ConstraintFactory factory) {
    return factory.forEach(PlannerShiftAssignment.class)
            .filter(assignment -> /* 条件 */)
            .penalize(HardMediumSoftScore.ONE_HARD)
            .asConstraint("自定义约束名称");
}
```

## 注意事项

1. 排班生成是计算密集型操作，建议异步执行
2. 对于大型排班问题（超过 100 个班次），建议增加求解时间
3. 数据库连接池大小需要根据并发需求调整
4. 建议对排班结果进行人工审核后再发布

## 许可证

MIT License
