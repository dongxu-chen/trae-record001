# git-commitlint (Rust)

高性能 Git 提交消息规范检查工具 - Rust 实现

## ✨ 特性

- 🚀 **毫秒级性能** - Rust 编译为原生二进制，比 Node.js 版本快 50-100 倍
- 📝 **60+ 内置类型** - 涵盖常见的提交类型，每种类型配有专属 emoji
- ⚙️ **TOML 配置** - 支持自定义规则，灵活配置
- 🎨 **彩色输出** - 友好的错误提示和修复建议
- 🔧 **Git Hooks 集成** - 与 Husky 无缝配合
- 🌍 **跨平台** - 支持 Windows、macOS、Linux

## 📦 安装

### 方式一：Cargo 安装

```bash
cargo install --path .
```

### 方式二：从源码编译

```bash
# 克隆项目
git clone <repository-url>
cd git-commitlint

# 编译 release 版本
cargo build --release

# 将二进制文件复制到 PATH
cp target/release/git-commitlint /usr/local/bin/
```

## 🚀 使用

### 检查提交消息

```bash
# 检查文件中的提交消息
git-commitlint check .git/COMMIT_EDITMSG

# 或使用短参数
git-commitlint -f .git/COMMIT_EDITMSG
```

### 列出所有可用类型

```bash
git-commitlint list-types

# 或
git-commitlint --list-types
```

### 生成配置文件

```bash
git-commitlint init

# 或
git-commitlint --init
```

### 使用自定义配置

```bash
git-commitlint check -c /path/to/commitlint.toml .git/COMMIT_EDITMSG
```

### 安静模式（适合 CI）

```bash
git-commitlint check --quiet .git/COMMIT_EDITMSG
```

## 🔧 与 Husky 集成

### 安装 Husky

```bash
# 在 Node.js 项目中
npm install husky --save-dev

# 启用 Git hooks
npx husky install
```

### 添加 commit-msg 钩子

```bash
npx husky add .husky/commit-msg 'git-commitlint check "$1"'
```

### 可选：添加 pre-commit 钩子

```bash
npx husky add .husky/pre-commit << 'EOF'
echo "📋 [pre-commit] 执行代码检查..."

# 检查未暂存的文件
UNSTAGED=$(git diff --name-only --diff-filter=ACM 2>/dev/null | wc -l)
if [ "$UNSTAGED" -gt 0 ]; then
  echo ""
  echo "⚠️  发现 $UNSTAGED 个未暂存的文件:"
  git diff --name-only --diff-filter=ACM 2>/dev/null | while read -r file; do
    echo "   • $file"
  done
  echo ""
  echo "💡 建议: 先执行 'git add' 暂存这些文件，或者确认这是有意的"
  echo ""
fi

echo "✅ [pre-commit] 代码检查完成"
EOF
```

## 📋 配置说明

### 默认配置文件

工具会自动查找以下配置文件：

- `commitlint.toml`
- `.commitlint.toml`
- `commitlintrc.toml`
- `.commitlintrc`

### 配置项

```toml
# 允许的提交类型
types = ["feat", "fix", "docs", "..."]

# 各类型对应的 emoji
[type_emojis]
feat = "✨"
fix = "🐛"

# 各类型的中文描述
[type_descriptions]
feat = "新功能"
fix = "修复Bug"

# 长度限制
min_length = 10
max_length = 100

# 格式校验正则表达式
pattern = "^(\\w+)(\\([^)]+\\))?:\\s*(.+)$"

# 严格模式
strict = true
```

## 📝 提交规范

### 格式

```
<type>(<scope>): <subject>
```

### 示例

```bash
# ✨ 新功能
git commit -m "feat(user): 添加用户登录功能"

# 🐛 Bug修复
git commit -m "fix(api): 修复用户信息获取接口"

# 📝 文档更新
git commit -m "docs: 更新安装说明"

# 💄 代码格式
git commit -m "style: 格式化代码，删除尾随空格"

# ♻️ 代码重构
git commit -m "refactor: 重构用户模块"
```

## 🎯 完整类型列表

| 分类 | 类型 | Emoji | 描述 |
|------|------|-------|------|
| **功能类** | feat | ✨ | 新功能 |
| | fix | 🐛 | 修复Bug |
| | hotfix | 🔥 | 紧急修复 |
| **文档类** | docs | 📝 | 文档更新 |
| | readme | 📖 | README更新 |
| **样式类** | style | 💄 | 代码格式 |
| | format | 🎨 | 格式化 |
| | typo | ✏️ | 拼写错误 |
| **重构类** | refactor | ♻️ | 代码重构 |
| | cleanup | 🧹 | 代码清理 |
| **性能类** | perf | ⚡ | 性能优化 |
| **测试类** | test | ✅ | 测试相关 |
| **构建类** | build | 📦 | 构建系统 |
| **CI/CD** | ci | 🤖 | 持续集成 |
| | deploy | 🚀 | 部署相关 |
| **依赖类** | deps | 📦 | 依赖更新 |
| **其他类** | chore | 🔧 | 日常维护 |
| **回滚类** | revert | ⏪ | 回滚提交 |
| **安全类** | security | 🔒 | 安全修复 |
| **国际化** | i18n | 🌍 | 国际化 |
| **设计类** | design | 🎨 | 设计更新 |
| **数据类** | db | 🗄️ | 数据库 |
| **配置类** | config | ⚙️ | 配置变更 |
| **日志类** | log | 📜 | 日志相关 |

... 以及更多类型，运行 `git-commitlint list-types` 查看完整列表。

## 🔨 开发

### 运行测试

```bash
cargo test
```

### 运行 Clippy

```bash
cargo clippy
```

### 格式化代码

```bash
cargo fmt
```

### 构建 Release 版本

```bash
cargo build --release
```

## 📊 性能对比

| 工具 | 语言 | 平均耗时 |
|------|------|----------|
| git-commitlint | Rust | ~10ms |
| commitlint (Node.js) | Node.js | ~500-1000ms |

**速度提升：50-100 倍** 🚀

## 📄 License

MIT
