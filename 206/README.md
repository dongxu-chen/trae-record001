# 智能会议室预订系统后端

基于 Spring Boot + MyBatis + MySQL 实现的智能会议室预订系统后端。

## 功能特性

- ✅ 会议室查询（按时间、人数、设备筛选）
- ✅ 预订申请（冲突检测）
- ✅ 预订确认/取消
- ✅ 预订历史查询
- ✅ 重复预订规则（每周固定时间）
- ✅ 高并发下的预订冲突处理

## 技术栈

- Spring Boot 2.7.18
- MyBatis 2.3.1
- MySQL 8.x
- Redis（用于分布式锁）
- Quartz（定时任务调度）
- Lombok
- HikariCP 连接池

## 数据库设计

### 核心表结构

1. **user** - 用户表
2. **meeting_room** - 会议室表
3. **equipment** - 设备表
4. **meeting_room_equipment** - 会议室设备关联表
5. **booking** - 预订表

## 快速开始

### 1. 初始化数据库

```bash
mysql -u root -p < src/main/resources/sql/schema.sql
```

### 2. 配置数据库连接

修改 `src/main/resources/application.yml`:

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/meeting_booking
    username: root
    password: your_password
```

### 3. 启动项目

```bash
mvn clean install
mvn spring-boot:run
```

服务启动后访问: `http://localhost:8080`

## API 接口文档

### 会议室接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/rooms/{id}` | 获取会议室详情 |
| GET | `/api/rooms` | 查询会议室列表 |
| GET | `/api/rooms/available` | 查询可用会议室（按时间筛选） |
| POST | `/api/rooms` | 新增会议室 |
| PUT | `/api/rooms` | 更新会议室 |
| DELETE | `/api/rooms/{id}` | 删除会议室 |

#### 查询可用会议室示例

```
GET /api/rooms/available?startTime=2024-01-15 09:00:00&endTime=2024-01-15 11:00:00&minCapacity=10&equipmentTypes=PROJECTOR,WHITEBOARD
```

### 预订接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/bookings/{id}` | 获取预订详情 |
| GET | `/api/bookings` | 查询预订列表 |
| GET | `/api/bookings/user/{userId}` | 查询用户预订 |
| GET | `/api/bookings/recurring/{parentId}` | 查询重复预订系列 |
| POST | `/api/bookings` | 创建预订 |
| PUT | `/api/bookings/{id}` | 更新预订 |
| POST | `/api/bookings/{id}/confirm` | 确认预订 |
| POST | `/api/bookings/{id}/cancel` | 取消预订 |

#### 创建单次预订

```json
POST /api/bookings
{
  "roomId": 1,
  "userId": 1,
  "title": "技术周会",
  "startTime": "2024-01-15T09:00:00",
  "endTime": "2024-01-15T10:00:00",
  "attendees": 10,
  "description": "讨论本周技术进展",
  "isRecurring": false
}
```

#### 创建重复预订（每周）

```json
POST /api/bookings
{
  "roomId": 2,
  "userId": 1,
  "title": "周一站会",
  "startTime": "2024-01-15T09:00:00",
  "endTime": "2024-01-15T09:30:00",
  "attendees": 5,
  "isRecurring": true,
  "recurringRule": "WEEKLY",
  "recurringDays": [1, 3, 5],
  "recurringEndDate": "2024-06-30"
}
```

#### 取消预订

```
POST /api/bookings/{id}/cancel?cancelAllRecurring=true
```

### 设备接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/equipments/{id}` | 获取设备详情 |
| GET | `/api/equipments` | 获取所有设备 |
| GET | `/api/equipments/room/{roomId}` | 获取会议室设备 |
| POST | `/api/equipments` | 新增设备 |
| PUT | `/api/equipments` | 更新设备 |
| DELETE | `/api/equipments/{id}` | 删除设备 |

## 高并发冲突处理方案

### 1. 悲观锁（Pessimistic Locking）

在查询冲突预订时使用 `FOR UPDATE` 行级锁：

```sql
SELECT ... FROM booking b WHERE ... FOR UPDATE
```

确保在事务中检查冲突时，其他并发请求无法修改相同时间段的预订。

### 2. 乐观锁（Optimistic Locking）

使用 `version` 字段实现乐观锁：

```sql
UPDATE booking SET status = ?, version = version + 1 WHERE id = ? AND version = ?
```

如果更新影响行数为0，说明数据已被其他请求修改，抛出异常提示用户重试。

### 3. 数据库事务

所有写操作使用 `@Transactional` 注解确保数据一致性。

### 4. 唯一索引约束

通过数据库层面的唯一索引（时间区间逻辑）防止极端情况下的重复预订。

## 预订状态

| 状态码 | 说明 |
|--------|------|
| 0 | 已取消 |
| 1 | 待确认 |
| 2 | 已确认 |
| 3 | 已完成 |

## 设备类型

- `PROJECTOR` - 投影仪
- `WHITEBOARD` - 白板
- `TV` - 电视
- `MIC` - 麦克风
- `CAMERA` - 摄像头

## 重复规则

- `WEEKLY` - 每周
- `DAILY` - 每天

重复日期使用 1-7 表示周一到周日。

## 响应格式

### 成功响应

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

### 错误响应

```json
{
  "code": 500,
  "message": "该时间段已被预订",
  "data": null
}
```
