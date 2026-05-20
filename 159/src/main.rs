use clap::Parser;
use colored::*;
use std::collections::HashMap;
use std::fs;
use std::process;

mod config;
mod types;
mod validator;

use config::{load_config, load_config_from, generate_default_config};
use types::get_all_commit_types;
use validator::Validator;

#[derive(Parser, Debug)]
#[command(
    name = "git-commitlint",
    author = "Your Name",
    version = "1.0.0",
    about = "高性能Git提交消息规范检查工具 - Rust实现",
    long_about = None
)]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,

    /// 提交消息文件路径
    #[arg(short, long)]
    file: Option<String>,

    /// 使用的配置文件路径
    #[arg(short, long)]
    config: Option<String>,

    /// 显示所有可用的提交类型
    #[arg(long)]
    list_types: bool,

    /// 生成默认配置文件
    #[arg(long)]
    init: bool,

    /// 安静模式，不输出详细信息
    #[arg(short, long)]
    quiet: bool,
}

#[derive(Parser, Debug)]
enum Commands {
    /// 检查提交消息
    Check {
        /// 提交消息文件路径
        file: String,
    },
    /// 列出所有可用的提交类型
    ListTypes,
    /// 生成默认配置文件
    Init,
    /// 验证配置文件
    ValidateConfig,
}

fn main() {
    let cli = Cli::parse();

    if cli.init {
        if let Err(e) = generate_default_config("commitlint.toml") {
            eprintln!("{} 生成配置文件失败: {}", "❌".red(), e);
            process::exit(1);
        }
        println!("{} 配置文件已生成: {}", "✅".green(), "commitlint.toml".cyan());
        return;
    }

    if cli.list_types {
        print_type_list();
        return;
    }

    let config = if let Some(config_path) = cli.config {
        match load_config_from(&config_path) {
            Ok(c) => c,
            Err(e) => {
                eprintln!("{} 加载配置文件失败 {}: {}", "❌".red(), config_path, e);
                process::exit(1);
            }
        }
    } else {
        load_config().unwrap_or_default()
    };

    let validator = Validator::new(config);

    if let Some(command) = cli.command {
        match command {
            Commands::Check { file } => {
                check_commit_file(&validator, &file, cli.quiet);
            }
            Commands::ListTypes => {
                print_type_list();
            }
            Commands::Init => {
                if let Err(e) = generate_default_config("commitlint.toml") {
                    eprintln!("{} 生成配置文件失败: {}", "❌".red(), e);
                    process::exit(1);
                }
                println!("{} 配置文件已生成: {}", "✅".green(), "commitlint.toml".cyan());
            }
            Commands::ValidateConfig => {
                println!("{} 配置文件验证成功", "✅".green());
            }
        }
    } else if let Some(file) = cli.file {
        check_commit_file(&validator, &file, cli.quiet);
    } else {
        eprintln!("{} 请提供提交消息文件路径", "❌".red());
        eprintln!("使用 --help 查看帮助信息");
        process::exit(1);
    }
}

fn check_commit_file(validator: &Validator, file_path: &str, quiet: bool) {
    let message = match fs::read_to_string(file_path) {
        Ok(m) => m,
        Err(e) => {
            eprintln!("{} 读取文件失败 {}: {}", "❌".red(), file_path, e);
            process::exit(1);
        }
    };

    let normalized = validator.normalize_message(&message);
    let errors = validator.validate(&message);

    if errors.is_empty() {
        if !quiet {
            let parsed = validator.parse_message(&normalized);
            let emoji = parsed
                .as_ref()
                .and_then(|p| validator.get_type_emoji(&p.r#type))
                .map(|s| s.as_str())
                .unwrap_or("✅");

            println!("\n{}", " COMMIT MESSAGE 检查通过 ".on_green().white().bold());
            println!("{} 提交信息: {}", "📝".yellow(), normalized.green());
            println!("{} 检查通过，共检查 {} 种类型\n", emoji.green(), validator.config().types.len());
        }
        process::exit(0);
    } else {
        if !quiet {
            println!("\n{}", " COMMIT MESSAGE 检查失败 ".on_red().white().bold());
            println!("{}", "═".repeat(50).red());
            println!("{} 提交信息: {}", "📝".yellow(), normalized.white());
            println!("{}", "═".repeat(50).red());
            println!("\n{} 发现的问题:\n", "❌".red().bold());

            for (i, error) in errors.iter().enumerate() {
                println!("  {}. {}", i + 1, error.to_string().red());
                println!("     {} {}\n", "💡".cyan(), error.suggestion().dimmed());
            }

            print_format_guide(validator);
        }
        process::exit(1);
    }
}

fn print_type_list() {
    let all_types = get_all_commit_types();
    let mut grouped: HashMap<&str, Vec<_>> = HashMap::new();

    for t in &all_types {
        grouped.entry(&t.category).or_default().push(t);
    }

    println!("\n{}", " 可用的提交类型列表 ".on_blue().white().bold());
    println!();

    let categories = [
        "功能类", "文档类", "样式类", "重构类", "性能类", "测试类",
        "构建类", "CI/CD", "依赖类", "其他类", "回滚类", "安全类",
        "国际化", "设计类", "数据类", "配置类", "日志类", "其他",
    ];

    for category in &categories {
        if let Some(types) = grouped.get(*category) {
            println!("{} {}", "📂".blue(), category.bold());
            for t in types {
                println!(
                    "  {} {:<14} {}",
                    t.emoji.green(),
                    t.name.cyan(),
                    t.description.dimmed()
                );
            }
            println!();
        }
    }

    println!("共 {} 种提交类型\n", all_types.len());
}

fn print_format_guide(validator: &Validator) {
    println!("{}", " 提交信息格式规范 ".on_blue().white().bold());
    println!();
    println!("  格式: {}", "<type>(<scope>): <subject>".white().bold());
    println!();
    println!("{} 示例:", "✨".green());
    println!("  {} feat(user): 添加用户登录功能", "✅".green());
    println!("  {} fix(api): 修复用户信息获取接口", "✅".green());
    println!("  {} docs: 更新README文档", "✅".green());
    println!();
    println!("{} 常用类型:", "📋".yellow());
    
    let common_types = ["feat", "fix", "docs", "style", "refactor", "perf", "test"];
    for t in &common_types {
        let emoji = validator.get_type_emoji(t).map(|s| s.as_str()).unwrap_or("");
        let desc = validator.get_type_description(t).map(|s| s.as_str()).unwrap_or("");
        println!("  {} {:<10} {}", emoji.green(), t.cyan(), desc.dimmed());
    }
    println!();
}
