# Jimmer ORM - PHP实现

基于Java Jimmer设计理念的PHP ORM框架，专为多租户SaaS系统打造。

## 核心特性

### 1. 动态表结构支持
- 运行时创建/修改表结构
- 租户级隔离表自动生成
- 注解驱动的DDL生成

### 2. DSL查询引擎
- 流畅的查询构建器API
- 谓词组合系统（AND/OR/NOT）
- 类型安全的条件表达式
- 复杂查询支持

### 3. 关联查询自动优化
- 预加载策略（Eager Loading）
- N+1查询问题自动解决
- 关联抓取配置
- 批量数据加载优化

### 4. 租户数据自动加密
- AES-256-CBC透明加密
- HMAC完整性验证
- 字段级加密控制
- 多类型数据支持

---

## 快速开始

### 1. 配置服务提供者

在 `config/app.php` 中添加：

```php
'providers' => [
    // ...
    App\Providers\JimmerServiceProvider::class,
],
```

### 2. 环境配置

在 `.env` 中添加：

```env
JIMMER_ENCRYPTION_KEY=your-32-byte-encryption-key-here
```

生成加密密钥：

```php
use App\Jimmer\Encryption\EncryptionManager;
echo EncryptionManager::generateKey();
```

---

## 实体定义示例

### 基本实体

```php
<?php

namespace App\Jimmer\Entity;

use App\Jimmer\Entity\EntityInterface;

/**
 * @Table(name="forms")
 * @TenantAware
 * @RepositoryClass("App\Repository\FormRepository")
 */
class Form implements EntityInterface
{
    /**
     * @Id
     * @GeneratedValue
     * @Column(type="bigint")
     */
    protected $id;
    
    /**
     * @Column(type="string", length=255)
     */
    protected $name;
    
    /**
     * @Column(type="text", nullable=true)
     * @Encrypted
     */
    protected $description;
    
    /**
     * @Column(type="json", nullable=true)
     */
    protected $schema;
    
    /**
     * @Column(type="boolean")
     */
    protected $isActive = true;
    
    /**
     * @Column(type="string", length=100)
     * @TenantId
     */
    protected $tenantId;
    
    // Getters and Setters...
}
```

### 注解说明

| 注解 | 作用域 | 说明 |
|------|--------|------|
| `@Table(name="xxx")` | 类 | 指定表名 |
| `@TenantAware` | 类 | 标记为租户感知实体 |
| `@RepositoryClass("...")` | 类 | 指定自定义仓库类 |
| `@Id` | 属性 | 标记为主键 |
| `@GeneratedValue` | 属性 | 标记为自动生成值 |
| `@Column(type="xxx", ...)` | 属性 | 定义列属性 |
| `@Encrypted` | 属性 | 标记字段需要加密 |
| `@TenantId` | 属性 | 标记为租户ID字段 |

---

## 查询API使用

### 基本查询

```php
use App\Jimmer\EntityManager;
use App\Jimmer\Entity\Form;

$em = app(EntityManager::class);

// 按ID查找
$form = $em->find(Form::class, 1);

// 查找所有
$forms = $em->findAll(Form::class);

// 条件查询
$forms = $em->createQueryBuilder(Form::class)
    ->where('isActive', '=', true)
    ->andWhere('name', 'LIKE', '%test%')
    ->orderBy('createdAt', 'desc')
    ->limit(10)
    ->get();
```

### DSL谓词查询

```php
use App\Jimmer\Query\Predicate;

$forms = $em->createQueryBuilder(Form::class)
    ->predicate(
        Predicate::and(
            Predicate::eq('isActive', true),
            Predicate::or(
                Predicate::like('name', '%test%'),
                Predicate::between('createdAt', $startDate, $endDate)
            ),
            Predicate::not(Predicate::isNull('description'))
        )
    )
    ->get();
```

### 可用谓词

- `Predicate::eq($column, $value)` - 等于
- `Predicate::ne($column, $value)` - 不等于
- `Predicate::gt($column, $value)` - 大于
- `Predicate::gte($column, $value)` - 大于等于
- `Predicate::lt($column, $value)` - 小于
- `Predicate::lte($column, $value)` - 小于等于
- `Predicate::like($column, $value)` - LIKE匹配
- `Predicate::in($column, $values)` - IN查询
- `Predicate::notIn($column, $values)` - NOT IN查询
- `Predicate::between($column, $min, $max)` - BETWEEN查询
- `Predicate::notBetween($column, $min, $max)` - NOT BETWEEN
- `Predicate::isNull($column)` - IS NULL
- `Predicate::isNotNull($column)` - IS NOT NULL
- `Predicate::raw($sql, $bindings)` - 原始SQL

### 关联预加载

```php
// 预加载关联，避免N+1查询
$forms = $em->createQueryBuilder(Form::class)
    ->fetch('submissions')  // 预加载submissions关联
    ->fetch('createdBy')    // 预加载createdBy关联
    ->where('isActive', '=', true)
    ->get();
```

### 分页查询

```php
$result = $em->createQueryBuilder(Form::class)
    ->where('isActive', '=', true)
    ->orderBy('createdAt', 'desc')
    ->paginate(1, 15); // 第1页，每页15条

// 结果包含：
// $result['items'] - 当前页数据
// $result['total'] - 总记录数
// $result['per_page'] - 每页数量
// $result['current_page'] - 当前页码
// $result['last_page'] - 最后页码
```

### 聚合查询

```php
$count = $em->createQueryBuilder(Form::class)
    ->where('isActive', '=', true)
    ->count();

$avg = $em->createQueryBuilder(Form::class)->avg('someField');
$sum = $em->createQueryBuilder(Form::class)->sum('someField');
$min = $em->createQueryBuilder(Form::class)->min('someField');
$max = $em->createQueryBuilder(Form::class)->max('someField');
```

---

## Repository使用

### 基础Repository

```php
use App\Jimmer\Repository;
use App\Jimmer\Entity\Form;

$repo = $em->createRepository(Form::class);

// 常用方法
$form = $repo->find($id);
$forms = $repo->findAll();
$forms = $repo->findBy(['isActive' => true], ['createdAt' => 'desc'], 10);
$form = $repo->findOneBy(['name' => 'Test Form']);
$count = $repo->count(['isActive' => true]);
$exists = $repo->exists(['name' => 'Test Form']);
```

### 自定义Repository

```php
<?php

namespace App\Repository;

use App\Jimmer\Repository;
use App\Jimmer\Query\Predicate;

class FormRepository extends Repository
{
    public function findActiveForms(string $tenantId): array
    {
        return $this->createQueryBuilder()
            ->predicate(
                Predicate::and(
                    Predicate::eq('isActive', true),
                    Predicate::eq('tenantId', $tenantId)
                )
            )
            ->orderBy('createdAt', 'desc')
            ->get();
    }
    
    public function searchForms(string $keyword, string $tenantId): array
    {
        return $this->createQueryBuilder()
            ->predicate(
                Predicate::and(
                    Predicate::eq('tenantId', $tenantId),
                    Predicate::or(
                        Predicate::like('name', "%{$keyword}%"),
                        Predicate::like('description', "%{$keyword}%")
                    )
                )
            )
            ->paginate(1, 20);
    }
}
```

---

## 持久化操作

### 创建实体

```php
use App\Jimmer\Entity\Form;

$form = new Form();
$form->setName('My Form');
$form->setDescription('This is a description'); // 自动加密
$form->setSchema(['fields' => []]);
$form->setTenantId('tenant_001');
$form->setIsActive(true);

$em->persist($form);
$em->flush();

echo $form->getId(); // 新创建的ID
```

### 更新实体

```php
$form = $em->find(Form::class, 1);
$form->setName('Updated Name');
$form->setDescription('Updated description'); // 自动重新加密

$em->flush(); // 自动检测变更
```

### 删除实体

```php
$form = $em->find(Form::class, 1);
$em->remove($form);
$em->flush();
```

### 事务操作

```php
$em->transactional(function ($em) use ($data) {
    $form = new Form();
    $form->setName($data['name']);
    $form->setTenantId($data['tenantId']);
    
    $em->persist($form);
    
    // 更多操作...
    
    // 自动flush，异常时自动回滚
});
```

---

## 多租户表管理

### 创建租户表

```php
$tenantId = 'client_001';
$schemaManager = $em->getSchemaManager();

// 为指定租户创建所有实体表
$schemaManager->createTenantTables($tenantId);

// 或为单个实体创建表
$schemaManager->createTenantTable(Form::class, $tenantId);
```

### 删除租户表

```php
$schemaManager->dropTenantTables($tenantId);
```

### 查询租户数据

```php
// 查询构建器自动支持租户表
$forms = $em->createQueryBuilder(Form::class)
    ->forTenant('client_001')  // 指定租户
    ->where('isActive', '=', true)
    ->get();
```

---

## 数据加密

### 自动加密/解密

```php
// @Encrypted注解的字段自动加密存储
$form->setDescription('Sensitive data'); // 写入时自动AES加密

// 读取时自动解密
$form = $em->find(Form::class, 1);
echo $form->getDescription(); // 自动解密为原始值
```

### 加密管理器直接使用

```php
use App\Jimmer\Encryption\EncryptionManager;

$encryptionManager = $em->getEncryptionManager();

// 加密
$encrypted = $encryptionManager->encrypt('secret data');

// 解密
$decrypted = $encryptionManager->decrypt($encrypted);
```

---

## Schema管理

### 创建表

```php
$schemaManager = $em->getSchemaManager();

// 创建单个表
$schemaManager->createTable(Form::class);

// 创建所有实体表
$schemaManager->createSchema();
```

### 更新表结构

```php
// 添加/修改列（自动检测变更）
$schemaManager->updateTable(Form::class);
```

### 检查表是否存在

```php
$exists = $schemaManager->tableExists('forms');
```

### 原始DDL操作

```php
$schemaManager->addColumnToTable('forms', function ($table) {
    $table->string('new_field')->nullable();
});

$schemaManager->renameTable('old_name', 'new_name');
$schemaManager->dropColumnFromTable('forms', 'unused_field');
```

---

## 性能优化

### 1. 批量处理

```php
$em->createQueryBuilder(Form::class)
    ->chunk(100, function ($forms, $page) {
        foreach ($forms as $form) {
            // 处理每个表单...
        }
    });
```

### 2. 关联预加载

```php
// 避免N+1查询问题
$forms = $em->createQueryBuilder(Form::class)
    ->fetch('submissions')
    ->fetch('createdBy')
    ->get();
```

### 3. 选择列

```php
$forms = $em->createQueryBuilder(Form::class)
    ->select(['id', 'name', 'createdAt']) // 只查询需要的列
    ->get();
```

### 4. 结果缓存

```php
// 启用实体级缓存（配置中开启）
$form = $em->find(Form::class, 1, [], true); // 第二个调用命中缓存
```

---

## 最佳实践

### 1. 仓库模式

始终通过Repository访问数据，保持代码整洁：

```php
// 好的做法
$forms = $formRepository->findActiveForms($tenantId);

// 避免在控制器中直接编写复杂查询
```

### 2. 谓词组合

使用谓词组合复杂条件，保持可读性：

```php
public function findByCriteria(array $criteria): array
{
    $predicates = [];
    
    if (isset($criteria['name'])) {
        $predicates[] = Predicate::like('name', "%{$criteria['name']}%");
    }
    
    if (isset($criteria['active'])) {
        $predicates[] = Predicate::eq('isActive', $criteria['active']);
    }
    
    return $this->createQueryBuilder()
        ->predicate(Predicate::and(...$predicates))
        ->get();
}
```

### 3. 加密敏感字段

对所有PII（个人可识别信息）字段使用`@Encrypted`注解：

```php
/**
 * @Column(type="string")
 * @Encrypted
 */
protected $email;

/**
 * @Column(type="string")
 * @Encrypted
 */
protected $phone;
```

### 4. 租户隔离

确保所有租户感知的实体都标记`@TenantAware`并包含租户ID字段：

```php
/**
 * @Table(name="forms")
 * @TenantAware
 */
class Form implements EntityInterface
{
    /**
     * @Column(type="string")
     * @TenantId
     */
    protected $tenantId;
}
```

---

## 架构概览

```
Jimmer ORM
├── Core
│   ├── EntityManager          - 实体管理器入口
│   ├── UnitOfWork             - 工作单元模式
│   ├── MetadataFactory        - 元数据工厂
│   └── JimmerConfig           - 配置类
├── Mapping
│   ├── EntityMetadata         - 实体元数据
│   ├── FieldMetadata          - 字段元数据
│   └── AssociationMetadata    - 关联元数据
├── Query
│   ├── QueryBuilder           - 查询构建器
│   └── Predicate              - 谓词系统
├── Schema
│   └── SchemaManager          - 结构管理器
├── Encryption
│   └── EncryptionManager      - 加密管理器
└── Entity
    └── EntityInterface        - 实体接口
```

---

## 文件清单

### 核心文件
- `app/Jimmer/EntityManager.php` - 实体管理器
- `app/Jimmer/UnitOfWork.php` - 工作单元
- `app/Jimmer/MetadataFactory.php` - 元数据工厂
- `app/Jimmer/JimmerConfig.php` - 配置类
- `app/Jimmer/Repository.php` - 仓库基类

### 查询系统
- `app/Jimmer/Query/QueryBuilder.php` - 查询构建器
- `app/Jimmer/Query/Predicate.php` - 谓词系统

### Schema管理
- `app/Jimmer/Schema/SchemaManager.php` - Schema管理器

### 加密系统
- `app/Jimmer/Encryption/EncryptionManager.php` - 加密管理器

### 实体与元数据
- `app/Jimmer/Mapping/EntityMetadata.php`
- `app/Jimmer/Mapping/FieldMetadata.php`
- `app/Jimmer/Mapping/AssociationMetadata.php`
- `app/Jimmer/Entity/EntityInterface.php`
- `app/Jimmer/Entity/Form.php` - 示例实体

### 服务提供者
- `app/Providers/JimmerServiceProvider.php`

---

## 后续扩展建议

1. **事件系统** - 添加实体生命周期事件钩子
2. **二级缓存** - 实现Redis二级缓存
3. **审计日志** - 自动记录实体变更历史
4. **软删除** - 软删除功能支持
5. **验证框架** - 实体级数据验证
6. **迁移系统** - 数据库版本迁移
7. **查询日志** - 慢查询分析与优化建议
8. **读写分离** - 主从数据库支持
