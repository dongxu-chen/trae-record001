use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommitType {
    pub name: String,
    pub emoji: String,
    pub description: String,
    pub category: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    #[serde(default = "default_types")]
    pub types: Vec<String>,
    
    #[serde(default = "default_type_emojis")]
    pub type_emojis: HashMap<String, String>,
    
    #[serde(default = "default_type_descriptions")]
    pub type_descriptions: HashMap<String, String>,
    
    #[serde(default = "default_min_length")]
    pub min_length: usize,
    
    #[serde(default = "default_max_length")]
    pub max_length: usize,
    
    #[serde(default = "default_pattern")]
    pub pattern: String,
    
    #[serde(default = "default_strict")]
    pub strict: bool,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            types: default_types(),
            type_emojis: default_type_emojis(),
            type_descriptions: default_type_descriptions(),
            min_length: default_min_length(),
            max_length: default_max_length(),
            pattern: default_pattern(),
            strict: default_strict(),
        }
    }
}

fn default_min_length() -> usize { 10 }
fn default_max_length() -> usize { 100 }
fn default_pattern() -> String { r"^(\w+)(\([^)]+\))?:\s*.{1,}$".to_string() }
fn default_strict() -> bool { true }

fn default_types() -> Vec<String> {
    vec![
        // 功能类
        "feat".to_string(),
        "fix".to_string(),
        "hotfix".to_string(),
        "feature".to_string(),
        "bugfix".to_string(),
        
        // 文档类
        "docs".to_string(),
        "doc".to_string(),
        "readme".to_string(),
        "comment".to_string(),
        
        // 代码样式
        "style".to_string(),
        "format".to_string(),
        "lint".to_string(),
        "typo".to_string(),
        
        // 重构类
        "refactor".to_string(),
        "rework".to_string(),
        "rewrite".to_string(),
        "cleanup".to_string(),
        
        // 性能类
        "perf".to_string(),
        "performance".to_string(),
        "optimize".to_string(),
        
        // 测试类
        "test".to_string(),
        "tests".to_string(),
        "unittest".to_string(),
        "e2e".to_string(),
        
        // 构建类
        "build".to_string(),
        "bundle".to_string(),
        "compile".to_string(),
        "package".to_string(),
        
        // CI/CD
        "ci".to_string(),
        "cd".to_string(),
        "deploy".to_string(),
        "workflow".to_string(),
        
        // 依赖管理
        "deps".to_string(),
        "deps-dev".to_string(),
        "upgrade".to_string(),
        "downgrade".to_string(),
        
        // 其他
        "chore".to_string(),
        "task".to_string(),
        "misc".to_string(),
        "wip".to_string(),
        
        // 回滚
        "revert".to_string(),
        "rollback".to_string(),
        "revert-feat".to_string(),
        
        // 安全
        "security".to_string(),
        "sec".to_string(),
        "patch".to_string(),
        
        // 国际化
        "i18n".to_string(),
        "l10n".to_string(),
        "translation".to_string(),
        
        // 设计
        "design".to_string(),
        "ui".to_string(),
        "ux".to_string(),
        "theme".to_string(),
        
        // 数据
        "db".to_string(),
        "database".to_string(),
        "migration".to_string(),
        "seed".to_string(),
        
        // 配置
        "config".to_string(),
        "env".to_string(),
        "settings".to_string(),
        
        // 日志
        "log".to_string(),
        "logging".to_string(),
        "debug".to_string(),
        "trace".to_string(),
    ]
}

fn default_type_emojis() -> HashMap<String, String> {
    let mut m = HashMap::new();
    
    // 功能类
    m.insert("feat".to_string(), "✨".to_string());
    m.insert("feature".to_string(), "✨".to_string());
    m.insert("fix".to_string(), "🐛".to_string());
    m.insert("bugfix".to_string(), "🐛".to_string());
    m.insert("hotfix".to_string(), "🔥".to_string());
    
    // 文档类
    m.insert("docs".to_string(), "📝".to_string());
    m.insert("doc".to_string(), "📝".to_string());
    m.insert("readme".to_string(), "📖".to_string());
    m.insert("comment".to_string(), "💬".to_string());
    
    // 代码样式
    m.insert("style".to_string(), "💄".to_string());
    m.insert("format".to_string(), "🎨".to_string());
    m.insert("lint".to_string(), "🔍".to_string());
    m.insert("typo".to_string(), "✏️".to_string());
    
    // 重构类
    m.insert("refactor".to_string(), "♻️".to_string());
    m.insert("rework".to_string(), "🔄".to_string());
    m.insert("rewrite".to_string(), "📝".to_string());
    m.insert("cleanup".to_string(), "🧹".to_string());
    
    // 性能类
    m.insert("perf".to_string(), "⚡".to_string());
    m.insert("performance".to_string(), "⚡".to_string());
    m.insert("optimize".to_string(), "🚀".to_string());
    
    // 测试类
    m.insert("test".to_string(), "✅".to_string());
    m.insert("tests".to_string(), "✅".to_string());
    m.insert("unittest".to_string(), "🧪".to_string());
    m.insert("e2e".to_string(), "🔬".to_string());
    
    // 构建类
    m.insert("build".to_string(), "📦".to_string());
    m.insert("bundle".to_string(), "📦".to_string());
    m.insert("compile".to_string(), "🔨".to_string());
    m.insert("package".to_string(), "📦".to_string());
    
    // CI/CD
    m.insert("ci".to_string(), "🤖".to_string());
    m.insert("cd".to_string(), "🚀".to_string());
    m.insert("deploy".to_string(), "🚀".to_string());
    m.insert("workflow".to_string(), "🔄".to_string());
    
    // 依赖管理
    m.insert("deps".to_string(), "📦".to_string());
    m.insert("deps-dev".to_string(), "🔧".to_string());
    m.insert("upgrade".to_string(), "⬆️".to_string());
    m.insert("downgrade".to_string(), "⬇️".to_string());
    
    // 其他
    m.insert("chore".to_string(), "🔧".to_string());
    m.insert("task".to_string(), "📋".to_string());
    m.insert("misc".to_string(), "📌".to_string());
    m.insert("wip".to_string(), "🚧".to_string());
    
    // 回滚
    m.insert("revert".to_string(), "⏪".to_string());
    m.insert("rollback".to_string(), "⏪".to_string());
    m.insert("revert-feat".to_string(), "⏪✨".to_string());
    
    // 安全
    m.insert("security".to_string(), "🔒".to_string());
    m.insert("sec".to_string(), "🔒".to_string());
    m.insert("patch".to_string(), "🩹".to_string());
    
    // 国际化
    m.insert("i18n".to_string(), "🌍".to_string());
    m.insert("l10n".to_string(), "🌐".to_string());
    m.insert("translation".to_string(), "📚".to_string());
    
    // 设计
    m.insert("design".to_string(), "🎨".to_string());
    m.insert("ui".to_string(), "🖼️".to_string());
    m.insert("ux".to_string(), "🎯".to_string());
    m.insert("theme".to_string(), "🎭".to_string());
    
    // 数据
    m.insert("db".to_string(), "🗄️".to_string());
    m.insert("database".to_string(), "🗄️".to_string());
    m.insert("migration".to_string(), "📊".to_string());
    m.insert("seed".to_string(), "🌱".to_string());
    
    // 配置
    m.insert("config".to_string(), "⚙️".to_string());
    m.insert("env".to_string(), "🌿".to_string());
    m.insert("settings".to_string(), "⚙️".to_string());
    
    // 日志
    m.insert("log".to_string(), "📜".to_string());
    m.insert("logging".to_string(), "📜".to_string());
    m.insert("debug".to_string(), "🔍".to_string());
    m.insert("trace".to_string(), "🔍".to_string());
    
    m
}

fn default_type_descriptions() -> HashMap<String, String> {
    let mut m = HashMap::new();
    
    // 功能类
    m.insert("feat".to_string(), "新功能".to_string());
    m.insert("feature".to_string(), "新功能".to_string());
    m.insert("fix".to_string(), "修复Bug".to_string());
    m.insert("bugfix".to_string(), "修复Bug".to_string());
    m.insert("hotfix".to_string(), "紧急修复".to_string());
    
    // 文档类
    m.insert("docs".to_string(), "文档更新".to_string());
    m.insert("doc".to_string(), "文档更新".to_string());
    m.insert("readme".to_string(), "README更新".to_string());
    m.insert("comment".to_string(), "代码注释".to_string());
    
    // 代码样式
    m.insert("style".to_string(), "代码格式".to_string());
    m.insert("format".to_string(), "格式化".to_string());
    m.insert("lint".to_string(), "Lint修复".to_string());
    m.insert("typo".to_string(), "拼写错误".to_string());
    
    // 重构类
    m.insert("refactor".to_string(), "代码重构".to_string());
    m.insert("rework".to_string(), "代码重写".to_string());
    m.insert("rewrite".to_string(), "重写代码".to_string());
    m.insert("cleanup".to_string(), "代码清理".to_string());
    
    // 性能类
    m.insert("perf".to_string(), "性能优化".to_string());
    m.insert("performance".to_string(), "性能优化".to_string());
    m.insert("optimize".to_string(), "优化代码".to_string());
    
    // 测试类
    m.insert("test".to_string(), "测试相关".to_string());
    m.insert("tests".to_string(), "测试相关".to_string());
    m.insert("unittest".to_string(), "单元测试".to_string());
    m.insert("e2e".to_string(), "端到端测试".to_string());
    
    // 构建类
    m.insert("build".to_string(), "构建系统".to_string());
    m.insert("bundle".to_string(), "打包相关".to_string());
    m.insert("compile".to_string(), "编译相关".to_string());
    m.insert("package".to_string(), "包管理".to_string());
    
    // CI/CD
    m.insert("ci".to_string(), "持续集成".to_string());
    m.insert("cd".to_string(), "持续部署".to_string());
    m.insert("deploy".to_string(), "部署相关".to_string());
    m.insert("workflow".to_string(), "工作流".to_string());
    
    // 依赖管理
    m.insert("deps".to_string(), "依赖更新".to_string());
    m.insert("deps-dev".to_string(), "开发依赖".to_string());
    m.insert("upgrade".to_string(), "升级依赖".to_string());
    m.insert("downgrade".to_string(), "降级依赖".to_string());
    
    // 其他
    m.insert("chore".to_string(), "日常维护".to_string());
    m.insert("task".to_string(), "任务处理".to_string());
    m.insert("misc".to_string(), "杂项".to_string());
    m.insert("wip".to_string(), "开发中".to_string());
    
    // 回滚
    m.insert("revert".to_string(), "回滚提交".to_string());
    m.insert("rollback".to_string(), "代码回滚".to_string());
    m.insert("revert-feat".to_string(), "回滚功能".to_string());
    
    // 安全
    m.insert("security".to_string(), "安全修复".to_string());
    m.insert("sec".to_string(), "安全相关".to_string());
    m.insert("patch".to_string(), "安全补丁".to_string());
    
    // 国际化
    m.insert("i18n".to_string(), "国际化".to_string());
    m.insert("l10n".to_string(), "本地化".to_string());
    m.insert("translation".to_string(), "翻译更新".to_string());
    
    // 设计
    m.insert("design".to_string(), "设计更新".to_string());
    m.insert("ui".to_string(), "界面更新".to_string());
    m.insert("ux".to_string(), "体验优化".to_string());
    m.insert("theme".to_string(), "主题更新".to_string());
    
    // 数据
    m.insert("db".to_string(), "数据库".to_string());
    m.insert("database".to_string(), "数据库".to_string());
    m.insert("migration".to_string(), "数据迁移".to_string());
    m.insert("seed".to_string(), "数据种子".to_string());
    
    // 配置
    m.insert("config".to_string(), "配置变更".to_string());
    m.insert("env".to_string(), "环境变量".to_string());
    m.insert("settings".to_string(), "设置更新".to_string());
    
    // 日志
    m.insert("log".to_string(), "日志相关".to_string());
    m.insert("logging".to_string(), "日志更新".to_string());
    m.insert("debug".to_string(), "调试代码".to_string());
    m.insert("trace".to_string(), "追踪代码".to_string());
    
    m
}

pub fn get_all_commit_types() -> Vec<CommitType> {
    let types = default_types();
    let emojis = default_type_emojis();
    let descriptions = default_type_descriptions();
    
    types.into_iter().map(|name| {
        let emoji = emojis.get(&name).cloned().unwrap_or_default();
        let description = descriptions.get(&name).cloned().unwrap_or_default();
        let category = get_category(&name);
        CommitType { name, emoji, description, category }
    }).collect()
}

fn get_category(typ: &str) -> String {
    match typ {
        "feat" | "feature" | "fix" | "bugfix" | "hotfix" => "功能类",
        "docs" | "doc" | "readme" | "comment" => "文档类",
        "style" | "format" | "lint" | "typo" => "样式类",
        "refactor" | "rework" | "rewrite" | "cleanup" => "重构类",
        "perf" | "performance" | "optimize" => "性能类",
        "test" | "tests" | "unittest" | "e2e" => "测试类",
        "build" | "bundle" | "compile" | "package" => "构建类",
        "ci" | "cd" | "deploy" | "workflow" => "CI/CD",
        "deps" | "deps-dev" | "upgrade" | "downgrade" => "依赖类",
        "chore" | "task" | "misc" | "wip" => "其他类",
        "revert" | "rollback" | "revert-feat" => "回滚类",
        "security" | "sec" | "patch" => "安全类",
        "i18n" | "l10n" | "translation" => "国际化",
        "design" | "ui" | "ux" | "theme" => "设计类",
        "db" | "database" | "migration" | "seed" => "数据类",
        "config" | "env" | "settings" => "配置类",
        "log" | "logging" | "debug" | "trace" => "日志类",
        _ => "其他",
    }.to_string()
}
