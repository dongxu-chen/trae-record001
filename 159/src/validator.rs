use crate::types::Config;
use regex::Regex;
use std::collections::HashSet;

#[derive(Debug, Clone)]
pub enum ValidationError {
    EmptyMessage,
    InvalidFormat,
    InvalidType {
        found: String,
        allowed: Vec<String>,
    },
    TooShort {
        length: usize,
        min: usize,
    },
    TooLong {
        length: usize,
        max: usize,
    },
}

impl ValidationError {
    pub fn to_string(&self) -> String {
        match self {
            ValidationError::EmptyMessage => "提交消息不能为空".to_string(),
            ValidationError::InvalidFormat => "格式不正确，必须符合: <type>(<scope>): <subject>".to_string(),
            ValidationError::InvalidType { found, allowed } => {
                format!("类型 '{}' 不在允许的列表中，可用类型: {}", found, allowed.join(", "))
            }
            ValidationError::TooShort { length, min } => {
                format!("内容过短，当前 {} 字符，至少需要 {} 个字符", length, min)
            }
            ValidationError::TooLong { length, max } => {
                format!("内容过长，当前 {} 字符，不能超过 {} 个字符", length, max)
            }
        }
    }

    pub fn suggestion(&self) -> String {
        match self {
            ValidationError::EmptyMessage => "请输入有意义的提交描述".to_string(),
            ValidationError::InvalidFormat => {
                "请确保type后面有冒号和空格，例如: feat: 添加新功能".to_string()
            }
            ValidationError::InvalidType { .. } => {
                "请从上面的可用类型列表中选择一个合适的类型".to_string()
            }
            ValidationError::TooShort { .. } => {
                "请提供更详细的提交描述，便于代码审查和版本追踪".to_string()
            }
            ValidationError::TooLong { .. } => {
                "请精简描述，详细信息可以写在commit message的body部分".to_string()
            }
        }
    }
}

#[derive(Debug, Clone)]
pub struct ParseResult {
    pub r#type: String,
    pub scope: Option<String>,
    pub subject: String,
}

pub struct Validator {
    config: Config,
    allowed_types: HashSet<String>,
    pattern: Regex,
}

impl Validator {
    pub fn new(config: Config) -> Self {
        let allowed_types: HashSet<String> = config.types.iter().cloned().collect();
        let pattern = Regex::new(&config.pattern).expect("Invalid regex pattern");
        
        Self {
            config,
            allowed_types,
            pattern,
        }
    }

    pub fn normalize_message(&self, message: &str) -> String {
        let normalized = message
            .replace("\r\n", "\n")
            .replace("\r", "\n");
        
        normalized
            .split('\n')
            .next()
            .unwrap_or("")
            .trim()
            .to_string()
    }

    pub fn parse_message(&self, message: &str) -> Option<ParseResult> {
        let caps = self.pattern.captures(message)?;
        
        let r#type = caps.get(1)?.as_str().to_string();
        let scope = caps.get(2).map(|m| {
            let s = m.as_str();
            s[1..s.len()-1].to_string()
        });
        let subject = caps.get(3)?.as_str().to_string();
        
        Some(ParseResult { r#type, scope, subject })
    }

    pub fn validate(&self, message: &str) -> Vec<ValidationError> {
        let mut errors = Vec::new();
        let normalized = self.normalize_message(message);

        if normalized.is_empty() {
            errors.push(ValidationError::EmptyMessage);
            return errors;
        }

        if !self.pattern.is_match(&normalized) {
            errors.push(ValidationError::InvalidFormat);
        }

        if let Some(parsed) = self.parse_message(&normalized) {
            if !self.allowed_types.contains(&parsed.r#type) {
                errors.push(ValidationError::InvalidType {
                    found: parsed.r#type,
                    allowed: self.config.types.clone(),
                });
            }
        }

        let len = normalized.len();
        if len < self.config.min_length {
            errors.push(ValidationError::TooShort {
                length: len,
                min: self.config.min_length,
            });
        }

        if len > self.config.max_length {
            errors.push(ValidationError::TooLong {
                length: len,
                max: self.config.max_length,
            });
        }

        errors
    }

    pub fn is_valid(&self, message: &str) -> bool {
        self.validate(message).is_empty()
    }

    pub fn get_type_emoji(&self, typ: &str) -> Option<&String> {
        self.config.type_emojis.get(typ)
    }

    pub fn get_type_description(&self, typ: &str) -> Option<&String> {
        self.config.type_descriptions.get(typ)
    }

    pub fn config(&self) -> &Config {
        &self.config
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalize_message() {
        let validator = Validator::new(Config::default());
        
        assert_eq!(validator.normalize_message("feat: test\r\nsecond line"), "feat: test");
        assert_eq!(validator.normalize_message("fix: test\rsecond"), "fix: test");
        assert_eq!(validator.normalize_message("  docs: test  \n"), "docs: test");
    }

    #[test]
    fn test_validate_valid_message() {
        let validator = Validator::new(Config::default());
        
        assert!(validator.is_valid("feat: 添加用户登录功能"));
        assert!(validator.is_valid("fix(auth): 修复登录bug"));
        assert!(validator.is_valid("docs(readme): 更新安装说明"));
    }

    #[test]
    fn test_validate_empty_message() {
        let validator = Validator::new(Config::default());
        
        let errors = validator.validate("");
        assert!(!errors.is_empty());
        assert!(matches!(errors[0], ValidationError::EmptyMessage));
    }

    #[test]
    fn test_validate_invalid_format() {
        let validator = Validator::new(Config::default());
        
        let errors = validator.validate("feat修复bug");
        assert!(!errors.is_empty());
        assert!(matches!(errors[0], ValidationError::InvalidFormat));
    }

    #[test]
    fn test_validate_invalid_type() {
        let validator = Validator::new(Config::default());
        
        let errors = validator.validate("invalid: 测试");
        assert!(!errors.is_empty());
        assert!(matches!(errors[0], ValidationError::InvalidType { .. }));
    }

    #[test]
    fn test_validate_too_short() {
        let validator = Validator::new(Config::default());
        
        let errors = validator.validate("feat: a");
        assert!(!errors.is_empty());
        assert!(matches!(errors[0], ValidationError::TooShort { .. }));
    }

    #[test]
    fn test_parse_message() {
        let validator = Validator::new(Config::default());
        
        let result = validator.parse_message("feat(auth): 测试消息").unwrap();
        assert_eq!(result.r#type, "feat");
        assert_eq!(result.scope, Some("auth".to_string()));
        assert_eq!(result.subject, "测试消息");
        
        let result = validator.parse_message("fix: 没有scope").unwrap();
        assert_eq!(result.r#type, "fix");
        assert_eq!(result.scope, None);
        assert_eq!(result.subject, "没有scope");
    }
}
