# 校园心理健康预约系统

基于 Flask + SQLAlchemy + Bootstrap 的校园心理健康预约系统。

## 功能特性

1. **咨询师预约** - 查看专业咨询师列表并进行预约
2. **SCL-90量表测评** - 90道题目的专业心理测评，自动计算10个因子分
3. **匿名倾诉** - 安全的匿名倾诉空间，支持回复功能
4. **预约记录管理** - 查看和管理所有预约记录，支持状态更新

## 技术栈

- 后端: Flask 2.3.3
- 数据库: SQLAlchemy + SQLite
- 前端: Bootstrap 5.3
- 表单: Flask-WTF

## 安装运行

1. 安装依赖:
```bash
pip install -r requirements.txt
```

2. 运行应用:
```bash
python app.py
```

3. 访问: http://localhost:5000

## 项目结构

```
├── app.py                 # 主应用文件
├── requirements.txt       # 依赖文件
├── mental_health.db       # SQLite数据库（自动创建）
├── templates/             # 模板目录
│   ├── base.html          # 基础布局
│   ├── index.html         # 首页
│   ├── counselors.html    # 咨询师列表
│   ├── book.html          # 预约表单
│   ├── appointments.html  # 预约记录
│   ├── scl90.html         # SCL-90测评
│   ├── scl90_result.html  # 测评结果
│   └── confessions.html   # 匿名倾诉
└── README.md
```

## SCL-90量表说明

SCL-90包含90个项目，涵盖10个因子：
- 躯体化
- 强迫症状
- 人际关系敏感
- 抑郁
- 焦虑
- 敌对
- 恐怖
- 偏执
- 精神病性
- 其他

评分说明：
- 1分：没有
- 2分：很轻
- 3分：中等
- 4分：偏重
- 5分：严重

因子分≥2.5表示存在轻度到中度症状，≥3表示存在中度到重度症状。

## 默认咨询师

系统初始化时会自动创建4位咨询师：
- 张医生 - 青少年心理、情绪管理
- 李医生 - 人际关系、学业压力
- 王医生 - 焦虑抑郁、职业规划
- 赵医生 - 家庭关系、自我成长
