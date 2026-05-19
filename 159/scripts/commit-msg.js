const fs = require('fs');
const path = require('path');
const chalk = require('chalk');

const configPath = path.resolve(process.cwd(), 'commitlint.config.js');
let userConfig = {};

if (fs.existsSync(configPath)) {
  userConfig = require(configPath);
}

const DEFAULT_CONFIG = {
  types: [
    'feat',
    'fix',
    'docs',
    'style',
    'refactor',
    'perf',
    'test',
    'build',
    'ci',
    'chore',
    'revert'
  ],
  typeEmojis: {
    feat: '✨',
    fix: '🐛',
    docs: '📝',
    style: '💄',
    refactor: '♻️',
    perf: '⚡',
    test: '✅',
    build: '📦',
    ci: '🤖',
    chore: '🔧',
    revert: '⏪'
  },
  maxLength: 100,
  minLength: 10,
  pattern: /^(\w+)(\(.+\))?: .{1,}$/,
  typeDescriptions: {
    feat: '新功能',
    fix: '修复bug',
    docs: '文档更新',
    style: '代码格式调整',
    refactor: '代码重构',
    perf: '性能优化',
    test: '测试相关',
    build: '构建系统',
    ci: '持续集成',
    chore: '其他修改',
    revert: '回滚提交'
  }
};

const CONFIG = { ...DEFAULT_CONFIG, ...userConfig };
const TYPE_DESCRIPTIONS = CONFIG.typeDescriptions || DEFAULT_CONFIG.typeDescriptions;
const TYPE_EMOJIS = CONFIG.typeEmojis || DEFAULT_CONFIG.typeEmojis;

function normalizeLineEndings(text) {
  return text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
}

function getCommitMessage() {
  const commitMsgFile = process.argv[2];
  if (!commitMsgFile) {
    console.error(chalk.red('❌ 错误: 未找到commit message文件'));
    process.exit(1);
  }

  const commitMsgPath = path.resolve(commitMsgFile);
  if (!fs.existsSync(commitMsgPath)) {
    console.error(chalk.red('❌ 错误: commit message文件不存在'));
    process.exit(1);
  }

  let message = fs.readFileSync(commitMsgPath, 'utf-8');
  message = normalizeLineEndings(message);
  message = message.split('\n')[0];
  return message.trim();
}

function validateType(type) {
  return CONFIG.types.includes(type);
}

function validateLength(message) {
  return message.length >= CONFIG.minLength && message.length <= CONFIG.maxLength;
}

function validateFormat(message) {
  return CONFIG.pattern.test(message);
}

function showErrorHeader(message) {
  console.log('\n');
  console.log(chalk.bgRed.white.bold('  COMMIT MESSAGE 检查失败  '));
  console.log(chalk.red('═'.repeat(50)));
  console.log(chalk.yellow('📝 提交信息: ') + chalk.white.bold(message));
  console.log(chalk.red('═'.repeat(50)));
}

function showSuccess(type) {
  const emoji = TYPE_EMOJIS[type] || '✅';
  console.log(chalk.bgGreen.white.bold(`  ${emoji} COMMIT MESSAGE 检查通过  `));
}

function showErrorWithSuggestion(error, suggestion) {
  console.log(chalk.red(`  ❌ ${error}`));
  if (suggestion) {
    console.log(chalk.cyan(`     💡 建议: ${suggestion}`));
  }
}

function showRules() {
  console.log('\n' + chalk.bgBlue.white.bold('  提交信息格式规范  ') + '\n');
  console.log(chalk.cyan('  格式: ') + chalk.white.bold('<type>(<scope>): <subject>'));
  console.log(chalk.gray('  ──────────────────────────────────────────────'));
  console.log('\n' + chalk.cyan('📋 可用的 type 类型:') + '\n');
  
  CONFIG.types.forEach(type => {
    const emoji = TYPE_EMOJIS[type] || '';
    const desc = TYPE_DESCRIPTIONS[type] || '';
    console.log(chalk.green(`    ${emoji} ${type.padEnd(10)}`) + chalk.gray(`- ${desc}`));
  });

  console.log('\n' + chalk.cyan('📏 长度要求:') + '\n');
  console.log(chalk.gray(`    最小长度: ${CONFIG.minLength} 字符`));
  console.log(chalk.gray(`    最大长度: ${CONFIG.maxLength} 字符`));
  console.log('\n' + chalk.cyan('✨ 正确示例:') + '\n');
  console.log(chalk.green(`    ✨ feat(user): 添加用户登录功能`));
  console.log(chalk.green(`    🐛 fix(api): 修复用户信息获取接口`));
  console.log(chalk.green(`    📝 docs: 更新README文档`));
  console.log('\n' + chalk.magenta('❌ 错误示例:') + '\n');
  console.log(chalk.red('    ❌ fix:修复bug        ') + chalk.gray('(冒号后缺少空格)'));
  console.log(chalk.red('    ❌ xxx: 错误类型      ') + chalk.gray('(type不在允许列表)'));
  console.log(chalk.red('    ❌ feat: a            ') + chalk.gray('(内容过短)'));
  console.log('\n');
}

function main() {
  const message = getCommitMessage();

  if (!message) {
    showErrorHeader('(空消息)');
    showErrorWithSuggestion('提交信息不能为空', '请输入有意义的提交描述');
    showRules();
    process.exit(1);
  }

  const errors = [];
  let detectedType = null;

  if (!validateFormat(message)) {
    errors.push({
      error: '格式不正确，必须符合: <type>(<scope>): <subject>',
      suggestion: '请确保type后面有冒号和空格，例如: feat: 添加新功能'
    });
  }

  const match = message.match(CONFIG.pattern);
  if (match) {
    const type = match[1];
    detectedType = type;
    if (!validateType(type)) {
      errors.push({
        error: `type "${type}" 不在允许的类型列表中`,
        suggestion: `请使用以下类型之一: ${CONFIG.types.map(t => `${TYPE_EMOJIS[t] || ''} ${t}`).join(', ')}`
      });
    }
  }

  if (!validateLength(message)) {
    if (message.length < CONFIG.minLength) {
      errors.push({
        error: `内容过短，当前 ${message.length} 字符，至少需要 ${CONFIG.minLength} 个字符`,
        suggestion: '请提供更详细的提交描述，便于代码审查和版本追踪'
      });
    } else {
      errors.push({
        error: `内容过长，当前 ${message.length} 字符，不能超过 ${CONFIG.maxLength} 个字符`,
        suggestion: '请精简描述，详细信息可以写在commit message的body部分'
      });
    }
  }

  if (errors.length > 0) {
    showErrorHeader(message);
    console.log('\n' + chalk.red.bold('  发现的问题:') + '\n');
    errors.forEach((item, index) => {
      showErrorWithSuggestion(`${index + 1}. ${item.error}`, item.suggestion);
    });
    showRules();
    process.exit(1);
  }

  showSuccess(detectedType);
  process.exit(0);
}

main();
