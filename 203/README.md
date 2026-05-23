# 自动化数据备份工具

一个功能完整的Python自动化数据备份工具，支持定期将指定目录的文件备份到远程SFTP服务器。

## ✨ 功能特性

- ✅ **全量备份**：备份目录下所有文件
- ✅ **增量备份**：从SFTP获取最新备份时间，基于文件修改时间只备份变更文件
- ✅ **流式压缩上传**：边压缩边上传，解决大文件占用磁盘空间问题
- ✅ **SFTP上传**：支持上传到远程SFTP服务器
- ✅ **定时调度**：使用Cron表达式配置备份时间
- ✅ **任务暂停/恢复**：支持运行时暂停和恢复备份任务
- ✅ **多任务配置**：支持定义多个备份任务
- ✅ **版本保留**：自动保留最近N天的备份版本（默认30天）
- ✅ **邮件通知**：备份完成后发送邮件通知（成功/失败），包含详细统计
- ✅ **文件排除**：支持配置排除特定文件模式
- ✅ **日志记录**：完整的日志记录，支持日志轮转

## 📁 项目结构

```
backup_tool/
├── main.py              # 主程序入口
├── config_loader.py     # 配置文件加载模块
├── backup_engine.py     # 备份逻辑引擎
├── compressor.py        # 文件压缩模块（支持流式压缩）
├── sftp_uploader.py     # SFTP上传模块（支持流式上传）
├── email_notifier.py    # 邮件通知模块
├── task_scheduler.py    # 任务调度模块（支持暂停/恢复）
├── config.yaml          # 配置文件
├── requirements.txt     # 依赖包列表
└── README.md            # 使用说明
```

## 🚀 安装依赖

```bash
pip install -r requirements.txt
```

## ⚙️ 配置说明

编辑 `config.yaml` 配置文件：

### 全局配置

```yaml
global:
  log_level: INFO          # 日志级别: DEBUG, INFO, WARNING, ERROR
  log_file: backup.log     # 日志文件路径
  temp_dir: ./temp         # 临时文件目录
```

### 邮件通知配置

```yaml
email:
  enabled: true
  smtp_server: smtp.example.com
  smtp_port: 587
  smtp_username: your_email@example.com
  smtp_password: your_password
  use_tls: true
  sender: your_email@example.com
  recipients:
    - admin@example.com
```

### SFTP服务器配置

```yaml
sftp:
  host: sftp.example.com
  port: 22
  username: backup_user
  password: your_sftp_password
  remote_base_dir: /backups
```

### 备份任务配置

支持配置多个备份任务：

```yaml
backup_tasks:
  - name: documents_backup
    enabled: true
    source_dir: /path/to/documents
    backup_type: incremental  # full 或 incremental
    cron: "0 2 * * *"          # 每天凌晨2点执行
    compression: true
    retention_days: 30
    exclude_patterns:
      - "*.tmp"
      - "*.log"
      - "__pycache__"
```

#### Cron表达式说明

Cron表达式格式：`分 时 日 月 周`

常用示例：
- `0 2 * * *` - 每天凌晨2点
- `0 3 * * 0` - 每周日凌晨3点
- `0 0 1 * *` - 每月1日凌晨0点
- `0 */6 * * *` - 每6小时
- `30 2 * * 1-5` - 工作日（周一到周五）凌晨2:30

## 🎯 使用方法

### 1. 列出所有备份任务

```bash
python main.py --list
# 或
python main.py -l
```

### 2. 立即执行指定备份任务

```bash
python main.py --run documents_backup
# 或
python main.py -r documents_backup
```

### 3. 启动定时任务调度器

```bash
python main.py --schedule
# 或
python main.py -s
```

### 4. 暂停指定备份任务

```bash
python main.py --pause documents_backup
```

### 5. 恢复指定备份任务

```bash
python main.py --resume documents_backup
```

### 6. 显示调度器状态

```bash
python main.py --status
```

### 7. 指定配置文件路径

```bash
python main.py -c /path/to/config.yaml -s
```

## 🎮 调度器交互式命令

启动调度器后（`-s` 模式），可以使用以下交互式命令：

- `list` 或 `status` - 显示当前任务状态
- `pause <任务名>` - 暂停指定任务
- `resume <任务名>` - 恢复指定任务
- `quit` - 退出调度器

示例：
```
> list
> pause documents_backup
> resume documents_backup
> quit
```

## 🔄 工作流程

1. **SFTP连接**：连接到远程SFTP服务器，获取最新备份时间
2. **备份准备**
   - 检查源目录是否存在
   - 根据备份类型（全量/增量）筛选需要备份的文件
   - 增量备份对比SFTP上的最新备份时间判断文件变更
3. **流式压缩上传**
   - 内存中压缩文件为tar.gz格式
   - 边压缩边上传到SFTP服务器
   - 不占用本地磁盘空间（流式处理）
4. **清理旧备份**
   - 自动删除超过保留天数的备份文件
   - 只保留最近N天的备份版本
5. **发送通知**
   - 备份成功：发送包含详细统计的邮件
   - 备份失败：发送包含错误信息的邮件
6. **关闭连接**：断开SFTP连接

## 📊 邮件通知内容

### 成功通知包含：
- 任务名称和备份类型
- 📊 文件统计：总文件数、已备份文件数、未变更文件数
- 压缩包大小
- 🗑️ 旧备份清理：清理数量、释放空间
- 源目录和备份时间

### 失败通知包含：
- 任务名称和备份类型
- 详细错误信息
- 错误排查建议

## 📝 备份文件命名格式

```
{任务名称}_{备份类型}_{时间戳}.tar.gz
```

示例：
- `documents_backup_FULL_20240115_020000.tar.gz`
- `documents_backup_INC_20240116_020000.tar.gz`

## 🔧 技术改进

### 1. 增量备份优化
- **之前**：依赖本地记录的备份时间，本地状态丢失会导致全量备份
- **现在**：从SFTP获取最新备份文件时间作为基准，更可靠

### 2. 流式压缩上传
- **之前**：先压缩到本地磁盘，再上传，占用大量磁盘空间
- **现在**：内存中压缩后直接流式上传，不占用本地磁盘空间

### 3. 任务调度增强
- **新增**：支持暂停和恢复备份任务
- **新增**：交互式命令行控制
- **新增**：实时显示任务状态

### 4. 邮件通知优化
- **修复**：HTML格式问题
- **新增**：详细的文件数量统计
- **新增**：旧备份清理统计
- **优化**：更美观的CSS样式

## ⚠️ 注意事项

1. **权限问题**：确保程序对源目录有读取权限
2. **内存使用**：流式压缩会占用一定内存，超大文件建议有足够内存
3. **网络连接**：确保可以正常连接到SFTP服务器
4. **密码安全**：生产环境建议使用SSH密钥认证替代密码
5. **首次增量备份**：首次执行增量备份时会执行全量备份

## 🔍 故障排查

### 1. SFTP连接失败
- 检查SFTP服务器地址和端口是否正确
- 检查用户名和密码是否正确
- 检查网络连接和防火墙设置

### 2. 邮件发送失败
- 检查SMTP服务器配置
- 检查邮箱是否开启了SMTP服务
- 部分邮箱需要使用授权码而非登录密码

### 3. 备份文件过大
- 合理配置排除模式，排除不必要的文件
- 考虑增加全量备份的间隔，使用增量备份

### 4. 增量备份每次都全量
- 检查SFTP上是否有历史备份文件
- 检查本地文件修改时间是否正确
- 查看日志确认获取的最新备份时间

## 📄 许可证

MIT License
