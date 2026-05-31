# 用户签到奖励系统

一个功能完整的用户签到奖励系统，支持多周期签到、连续签到奖励、补签卡、累计签到宝箱等功能。

## 技术栈

### 后端
- **Spring Boot 2.7.18** - Web框架
- **Spring Data JPA** - ORM框架
- **Spring Data Redis** - 缓存
- **MySQL 8.x** - 关系型数据库
- **Lombok** - 代码简化

### 前端
- **React 18** - UI框架
- **Vite** - 构建工具
- **Axios** - HTTP客户端
- **Day.js** - 日期处理

## 功能特性

### 1. 多周期签到
- ✅ 日签到 (DAILY)
- ✅ 周签到 (WEEKLY)
- ✅ 月签到 (MONTHLY)

### 2. 签到奖励系统
- ✅ 连续签到奖励（可配置）
- ✅ 积分奖励
- ✅ 补签卡奖励

### 3. 补签功能
- ✅ 补签卡机制
- ✅ 每月补签次数限制
- ✅ 点击日历日期补签

### 4. 累计签到宝箱
- ✅ 累计签到天数里程碑
- ✅ 宝箱奖励领取
- ✅ 奖励状态追踪

### 5. 数据统计
- ✅ 连续签到天数
- ✅ 累计签到天数
- ✅ 补签次数统计

### 6. 奖励配置动态化
- ✅ 签到奖励可配置
- ✅ 宝箱奖励可配置
- ✅ 支持多种奖励类型

### 7. 表达式引擎
- ✅ 支持JavaScript表达式动态计算奖励
- ✅ 条件表达式判定签到资格
- ✅ 黑名单机制禁止危险关键字
- ✅ 执行超时保护（5秒）

### 8. 签到提醒推送
- ✅ 每日签到提醒
- ✅ 连续签到临期提醒
- ✅ 宝箱达成提醒
- ✅ 自定义提醒时间和推送方式
- ✅ 定时任务自动推送

### 9. 社交分享
- ✅ 多平台分享（微信、微博、QQ等）
- ✅ 每日分享奖励（20积分/天）
- ✅ 每周分享额外奖励（100积分）
- ✅ 分享数据统计（浏览、点赞）
- ✅ 分享历史记录

### 10. 签到数据分析
- ✅ 个人签到分析（签到率、星期分布）
- ✅ 流失点分析（高风险天数识别）
- ✅ 签到率趋势分析
- ✅ 用户流失分析
- ✅ 运营建议生成

## 项目结构

```
checkin-system/
├── backend/                    # Spring Boot后端
│   ├── src/main/java/com/checkin/
│   │   ├── CheckinApplication.java    # 启动类
│   │   ├── common/                    # 通用类
│   │   ├── config/                    # 配置类
│   │   ├── controller/                # 控制器
│   │   ├── dto/                       # 数据传输对象
│   │   ├── entity/                    # 实体类
│   │   ├── repository/                # 数据访问层
│   │   └── service/                   # 业务逻辑层
│   ├── src/main/resources/
│   │   ├── application.yml            # 应用配置
│   │   └── schema.sql                 # 初始化SQL
│   └── pom.xml                        # Maven配置
│
└── frontend/                   # React前端
    ├── src/
    │   ├── components/               # 组件
    │   ├── pages/                    # 页面
    │   ├── styles/                   # 样式
    │   ├── App.jsx                   # 主应用
    │   └── main.jsx                  # 入口文件
    ├── index.html
    ├── vite.config.js
    └── package.json
```

## 数据库设计

### 核心表结构

1. **user** - 用户表
2. **checkin_record** - 签到记录表
3. **checkin_config** - 签到奖励配置表
4. **checkin_treasure** - 宝箱配置表
5. **user_treasure** - 用户宝箱领取记录表
6. **checkin_stats** - 签到统计表

## 快速开始

### 环境要求
- JDK 1.8+
- Node.js 16+
- MySQL 8.x
- Redis 5.x

### 后端启动

1. 创建数据库
```sql
CREATE DATABASE checkin_system DEFAULT CHARACTER SET utf8mb4;
```

2. 修改配置文件 `backend/src/main/resources/application.yml`
```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/checkin_system
    username: your_username
    password: your_password
  redis:
    host: localhost
    port: 6379
```

3. 启动后端
```bash
cd backend
mvn spring-boot:run
```

后端启动后会自动初始化默认的奖励配置。

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

## API接口

### 用户相关
- `POST /api/user/register` - 用户注册
- `POST /api/user/login` - 用户登录
- `GET /api/user/{id}` - 获取用户信息
- `PUT /api/user/{id}` - 更新用户信息

### 签到相关
- `POST /api/checkin` - 签到
- `GET /api/checkin/calendar` - 获取签到日历
- `POST /api/checkin/recheck` - 补签
- `POST /api/checkin/treasure/{id}` - 领取宝箱
- `GET /api/checkin/stats` - 获取统计数据

### 配置相关
- `GET /api/config/checkin/{periodType}` - 获取签到奖励配置
- `POST /api/config/checkin` - 保存签到奖励配置
- `DELETE /api/config/checkin/{id}` - 删除签到奖励配置
- `GET /api/config/treasure/{periodType}` - 获取宝箱配置
- `POST /api/config/treasure` - 保存宝箱配置
- `DELETE /api/config/treasure/{id}` - 删除宝箱配置

### 安全沙箱相关
- `POST /api/sandbox/validate` - 验证表达式安全性
- `POST /api/sandbox/execute` - 执行表达式
- `POST /api/sandbox/calculate-reward` - 计算奖励
- `GET /api/sandbox/forbidden-keywords` - 获取禁止关键字列表

### 签到提醒相关
- `GET /api/reminder/user/{userId}` - 获取用户提醒设置
- `POST /api/reminder` - 保存提醒设置
- `DELETE /api/reminder/{id}` - 删除提醒设置
- `GET /api/reminder/status/{userId}` - 获取提醒状态
- `GET /api/reminder/history/{userId}` - 获取推送历史
- `GET /api/reminder/types` - 获取提醒类型列表
- `GET /api/reminder/channels` - 获取推送渠道列表

### 社交分享相关
- `POST /api/share/create` - 创建分享
- `POST /api/share/claim/{shareId}` - 领取分享奖励
- `GET /api/share/history/{userId}` - 获取分享历史
- `GET /api/share/stats/{userId}` - 获取分享统计
- `POST /api/share/{shareId}/action` - 更新分享数据（浏览/点赞）
- `GET /api/share/platforms` - 获取分享平台列表
- `GET /api/share/rewards` - 获取分享奖励规则

### 数据分析相关
- `GET /api/analysis/dashboard` - 获取仪表板统计
- `GET /api/analysis/{periodType}` - 获取分析数据
- `POST /api/analysis/generate/{periodType}` - 生成分析数据
- `GET /api/analysis/user/{userId}` - 获取用户分析
- `GET /api/analysis/churn/{periodType}` - 获取流失分析
- `GET /api/analysis/trend/{periodType}` - 获取趋势分析
- `GET /api/analysis/report` - 获取完整分析报告

## 默认配置

系统启动后会自动初始化以下默认配置：

### 日签到奖励
- 第1天：10积分
- 第2天：15积分
- 第3天：20积分
- 第4天：25积分
- 第5天：30积分
- 第6天：35积分
- 第7天：1张补签卡
- 第14天：100积分
- 第21天：200积分
- 第30天：3张补签卡

### 累计签到宝箱
- 7天：周签到宝箱（100积分）
- 14天：双周签到宝箱（200积分）
- 21天：三周签到宝箱（2张补签卡）
- 28天：月签到大宝箱（500积分）

## 表达式使用说明

系统支持使用JavaScript表达式动态计算奖励。配置在`rewardExpression`字段中。

### 可用变量
- `continuousDays` - 连续签到天数
- `totalDays` - 累计签到天数
- `points` - 用户当前积分
- `recheckCount` - 补签次数

### 表达式示例
```javascript
// 基础递增奖励
10 + continuousDays * 5

// 阶梯奖励
continuousDays <= 7 ? 10 : continuousDays <= 14 ? 20 : 30

// 每周额外奖励
Math.floor(totalDays / 7) * 50

// 封顶递增
continuousDays > 3 ? Math.min(continuousDays * 10, 100) : 10

// 条件表达式（用于conditionExpression）
totalDays >= 7 && recheckCount < 3
```

### 安全限制
禁止使用以下危险操作：
- 文件操作（File, IO）
- 网络操作（Socket, URL）
- 系统操作（Runtime, Process, exec, exit）
- 反射操作（Class, forName, setAccessible）
- 线程操作（Thread, Executor）
- 类加载器操作

## 使用说明

1. 注册/登录账号
2. 选择签到周期（日/周/月）
3. 点击"立即签到"按钮完成当日签到
4. 查看连续签到奖励进度
5. 累计签到达到条件可领取宝箱
6. 错过签到可使用补签卡补签（仅限过去7天内）

## 重要改进说明

### 1. UTC时间断签判定
- 所有日期计算统一使用UTC时区
- 通过`DateUtils.getUtcToday()`获取服务端UTC日期
- 消除不同时区用户的签到时间判定误差
- 断签判定基于UTC日期，确保公平性

### 2. 7天补签限制
- 补签仅允许补签过去7天内的日期
- 服务端通过`DateUtils.isWithinRecheckWindow()`校验
- 前端同时校验，提升用户体验
- 仍保留每月最多5次补签的限制

### 3. 安全沙箱执行
- 所有表达式通过`SafeSandbox`工具类执行
- 黑名单机制禁止危险关键字
- Nashorn引擎执行前禁用危险API
- 5秒超时保护防止死循环
- 执行环境隔离，禁止访问Java API

## 扩展建议

- 添加签到提醒功能
- 添加更多奖励类型（优惠券、实物奖品等）
- 添加排行榜功能
- 添加签到分享功能
- 优化移动端体验
