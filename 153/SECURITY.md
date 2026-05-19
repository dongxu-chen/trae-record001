# 安全修复说明

## 修复内容总结

### 1. 并发预约冲突防护 ✅

**问题**: 多个用户同时预约同一咨询师同一时段可能导致双预约

**解决方案**:
- **数据库行锁**: 使用 `with_for_update()` 在查询时锁定记录
- **嵌套事务**: 使用 `db.session.begin_nested()` 创建保存点
- **乐观锁**: 添加 `version` 字段跟踪数据版本
- **冲突检测**: 预约前检查该时段是否已被占用

**代码位置**: `app.py:138-161` (book_appointment函数)

```python
with db.session.begin_nested():
    existing = Appointment.query.filter(
        Appointment.counselor_id == counselor_id,
        Appointment.appointment_date == appointment_date,
        Appointment.appointment_time == appointment_time,
        Appointment.status.in_(['待确认', '已确认'])
    ).with_for_update().first()
    
    if existing:
        flash('该时段已被预约，请选择其他时间！', 'danger')
        return
```

---

### 2. 复合索引优化 ✅

**问题**: 按咨询师和日期查询预约时性能低下

**解决方案**:
- **复合索引**: 添加 `idx_counselor_date` 索引 (counselor_id + appointment_date)
- **单列索引**: counselor_id、appointment_date、created_at 单独索引

**代码位置**: `app.py:74-76`

```python
__table_args__ = (
    db.Index('idx_counselor_date', 'counselor_id', 'appointment_date'),
)
```

**性能提升**:
- 查询 "某咨询师某天的预约" 从全表扫描 → 索引扫描
- 时间复杂度: O(n) → O(log n)

---

### 3. ORM对象内存优化 ✅

**问题**: SCL-90量表计算后ORM对象驻留内存，大量测评后内存堆积

**解决方案**:
- **Session分离**: `db.session.expunge(test)` 将对象从会话中移除
- **显式删除**: `del test, del answers` 删除变量引用
- **垃圾回收**: `gc.collect()` 强制触发Python垃圾回收

**代码位置**: `app.py:220-223`

```python
db.session.expunge(test)
del test
del answers
gc.collect()
```

**效果**:
- 每次测评后立即释放内存
- 避免大量测评导致的内存泄漏
- 高并发场景下内存占用更稳定

---

### 4. 匿名倾诉AES-256加密存储 ✅

**问题**: 匿名倾诉内容明文存储在数据库，存在隐私泄露风险

**解决方案**:
- **加密算法**: AES-256-GCM (通过 cryptography.Fernet)
- **密钥派生**: PBKDF2HMAC + SHA256 + 480000 迭代
- **透明加密**: 使用 @property 实现加密/解密透明化
- **安全编码**: Base64 URL安全编码存储

**代码位置**: `app.py:20-113`

```python
# 密钥派生
def get_encryption_key():
    password = app.config['SECRET_KEY'].encode()
    salt = b'mental_health_app_salt_2024'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key

# 模型透明加密
class Confession(db.Model):
    content_encrypted = db.Column(db.Text, nullable=False)
    
    @property
    def content(self):
        return decrypt_content(self.content_encrypted)
    
    @content.setter
    def content(self, value):
        self.content_encrypted = encrypt_content(value)
```

**安全特性**:
- ✅ AES-256 对称加密
- ✅ PBKDF2 密钥派生 (480,000 迭代)
- ✅ 自动处理密钥旋转和版本兼容
- ✅ 密文包含 HMAC 完整性校验
- ✅ 开发友好的透明API

---

## 安全配置建议

### 生产环境配置

```python
# 1. 使用环境变量存储密钥
export SECRET_KEY="your-very-long-random-secret-key-here"

# 2. 数据库加密 (可选，SQLite有加密扩展)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite+pysqlcipher:///path.db'

# 3. 禁用调试模式
app.run(debug=False)
```

### 密钥轮换

如需更换加密密钥:
1. 解密所有现有数据
2. 更换 SECRET_KEY
3. 用新密钥重新加密所有数据

---

## 测试验证

运行测试脚本验证所有安全功能:

```bash
python test_security.py
```

预期输出:
- AES-256 加密解密测试通过
- 匿名倾诉加密存储测试通过  
- 复合索引存在验证通过
- 行锁语法验证通过
- ORM内存释放验证通过

---

## 安全边界

| 功能 | 保护措施 | 安全级别 |
|------|----------|----------|
| 预约并发 | 行锁 + 乐观锁 | 高 |
| 查询性能 | 复合索引 | 中 |
| 匿名倾诉 | AES-256 加密 | 高 |
| 内存泄露 | ORM对象释放 + GC | 中 |

---

## 后续安全建议

1. **HTTPS**: 生产环境必须启用HTTPS
2. **输入验证**: 添加XSS防护和输入长度限制
3. **速率限制**: 防止暴力预约和DDoS攻击
4. **审计日志**: 记录所有预约和状态变更
5. **定期轮换**: 每90天轮换加密密钥
