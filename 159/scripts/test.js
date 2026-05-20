const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const chalk = require('chalk');

const configPath = path.resolve(process.cwd(), 'commitlint.config.js');
let config = {};

if (fs.existsSync(configPath)) {
  config = require(configPath);
}

const DEFAULT_CONFIG = {
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
  }
};

const testTypes = config.types || [
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
];

const TYPE_EMOJIS = config.typeEmojis || DEFAULT_CONFIG.typeEmojis;

const testCases = [
  {
    name: '格式正确的commit消息',
    message: 'feat(user): 添加用户登录功能',
    shouldPass: true
  },
  {
    name: '没有scope的commit消息',
    message: 'docs: 更新README文档',
    shouldPass: true
  },
  {
    name: '格式错误 - 缺少冒号空格',
    message: 'feat:修复bug',
    shouldPass: false
  },
  {
    name: '类型错误 - 不在允许的类型中',
    message: 'invalid: 错误的类型',
    shouldPass: false
  },
  {
    name: '内容过短',
    message: 'fix: 短',
    shouldPass: false
  },
  {
    name: '内容过长',
    message: 'feat: ' + 'a'.repeat(100),
    shouldPass: false
  },
  {
    name: '空消息',
    message: '',
    shouldPass: false
  },
  {
    name: '包含CRLF换行符的消息',
    message: 'fix(api): 修复接口问题\r\n这是第二行内容',
    shouldPass: true
  },
  {
    name: '包含CR换行符的消息',
    message: 'style: 格式化代码\r第二行',
    shouldPass: true
  }
];

const tempFile = path.resolve(__dirname, 'test-commit-msg.txt');

console.log(chalk.bgCyan.white.bold('  🧪 开始测试 commit-msg 检查脚本  ') + '\n');
console.log(chalk.cyan(`📋 配置文件中定义了 ${testTypes.length} 种提交类型:\n`));

testTypes.forEach(type => {
  const emoji = TYPE_EMOJIS[type] || '';
  console.log(chalk.gray(`   ${emoji} ${type}`));
});

console.log('\n');

let passed = 0;
let failed = 0;

testCases.forEach((testCase, index) => {
  fs.writeFileSync(tempFile, testCase.message);
  
  try {
    execSync(`node ${path.resolve(__dirname, 'commit-msg.js')} ${tempFile}`, {
      stdio: 'pipe',
      encoding: 'utf-8'
    });
    
    if (testCase.shouldPass) {
      console.log(chalk.green(`✅ 测试 ${index + 1}: ${testCase.name}`));
      passed++;
    } else {
      console.log(chalk.red(`❌ 测试 ${index + 1}: ${testCase.name} - 预期失败但通过了`));
      failed++;
    }
  } catch (error) {
    if (!testCase.shouldPass) {
      console.log(chalk.green(`✅ 测试 ${index + 1}: ${testCase.name}`));
      passed++;
    } else {
      console.log(chalk.red(`❌ 测试 ${index + 1}: ${testCase.name} - 预期通过但失败了`));
      console.log(chalk.gray(`   错误输出: ${error.stdout?.substring(0, 100) || ''}...`));
      failed++;
    }
  }
});

fs.unlinkSync(tempFile);

console.log('\n' + chalk.gray('═'.repeat(50)));
console.log(`\n${chalk.bold('测试结果:')} ${chalk.green(`${passed} 通过`)}, ${chalk.red(`${failed} 失败`)}`);

if (failed === 0) {
  console.log(chalk.green('\n🎉 所有测试通过！'));
} else {
  console.log(chalk.yellow('\n⚠️  部分测试失败，请检查代码。'));
}

console.log('\n' + chalk.cyan('📌 可用命令:\n'));
console.log(chalk.gray('   • ') + chalk.white('npm run commit') + chalk.gray('    - 交互式提交向导'));
console.log(chalk.gray('   • ') + chalk.white('npm run changelog') + chalk.gray(' - 自动生成CHANGELOG'));
console.log(chalk.gray('   • ') + chalk.white('npm test') + chalk.gray('           - 运行测试套件'));
console.log('\n');
