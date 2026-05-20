const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const inquirer = require('inquirer');
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
const TYPE_EMOJIS = CONFIG.typeEmojis || DEFAULT_CONFIG.typeEmojis;
const TYPE_DESCRIPTIONS = CONFIG.typeDescriptions || DEFAULT_CONFIG.typeDescriptions;

console.log('\n' + chalk.bgCyan.white.bold('  🚀 交互式 Git 提交向导  ') + '\n');

function checkStagedFiles() {
  try {
    const stagedFiles = execSync('git diff --cached --name-only --diff-filter=ACM', { encoding: 'utf-8' }).trim();
    if (!stagedFiles) {
      console.log(chalk.yellow('⚠️  没有暂存任何文件'));
      console.log(chalk.cyan('💡 请先执行 ') + chalk.white('git add') + chalk.cyan(' 暂存要提交的文件\n'));
      process.exit(0);
    }
    console.log(chalk.green('📁 已暂存的文件:\n'));
    stagedFiles.split('\n').forEach(file => {
      console.log(chalk.gray(`   • ${file}`));
    });
    console.log('');
  } catch (error) {
    console.log(chalk.red('❌ 检查暂存文件失败'));
    process.exit(1);
  }
}

function getScopeChoices() {
  try {
    const stagedFiles = execSync('git diff --cached --name-only --diff-filter=ACM', { encoding: 'utf-8' }).trim();
    const scopes = new Set(['none']);
    
    stagedFiles.split('\n').forEach(file => {
      const parts = file.split('/');
      if (parts.length > 1) {
        scopes.add(parts[0]);
      }
      const ext = path.extname(file);
      if (ext) {
        scopes.add(path.basename(file, ext));
      }
    });
    
    return Array.from(scopes).map(scope => ({
      name: scope === 'none' ? '无 scope' : scope,
      value: scope === 'none' ? '' : scope
    }));
  } catch (error) {
    return [{ name: '无 scope', value: '' }];
  }
}

async function runCommitWizard() {
  checkStagedFiles();

  const typeChoices = CONFIG.types.map(type => ({
    name: `${TYPE_EMOJIS[type] || '•'} ${type.padEnd(10)} - ${TYPE_DESCRIPTIONS[type] || ''}`,
    value: type
  }));

  const scopeChoices = getScopeChoices();

  const answers = await inquirer.prompt([
    {
      type: 'list',
      name: 'type',
      message: '📋 请选择提交类型:',
      choices: typeChoices,
      pageSize: 12
    },
    {
      type: 'list',
      name: 'scope',
      message: '🎯 请选择影响范围 (scope):',
      choices: scopeChoices
    },
    {
      type: 'input',
      name: 'subject',
      message: '📝 请输入简短描述 (subject):',
      validate: (input) => {
        if (!input || input.trim().length === 0) {
          return '描述不能为空';
        }
        if (input.length < CONFIG.minLength - 5) {
          return `描述至少需要 ${CONFIG.minLength - 5} 个字符`;
        }
        if (input.length > CONFIG.maxLength - 10) {
          return `描述不能超过 ${CONFIG.maxLength - 10} 个字符`;
        }
        return true;
      }
    },
    {
      type: 'input',
      name: 'body',
      message: '📄 请输入详细描述 (body，可选，按回车跳过):\n'
    },
    {
      type: 'confirm',
      name: 'breaking',
      message: '⚠️  是否包含破坏性变更 (BREAKING CHANGE)?',
      default: false
    }
  ]);

  let commitMessage = `${answers.type}`;
  if (answers.scope) {
    commitMessage += `(${answers.scope})`;
  }
  commitMessage += `: ${answers.subject}`;

  if (answers.breaking) {
    commitMessage = 'BREAKING CHANGE: ' + commitMessage;
  }

  if (answers.body && answers.body.trim()) {
    commitMessage += '\n\n' + answers.body;
  }

  console.log('\n' + chalk.cyan('📝 生成的提交信息:\n'));
  console.log(chalk.white(commitMessage));
  console.log('');

  const confirmAnswer = await inquirer.prompt([
    {
      type: 'confirm',
      name: 'confirm',
      message: '✅ 确认提交?',
      default: true
    }
  ]);

  if (confirmAnswer.confirm) {
    try {
      const tempFile = path.resolve(__dirname, '.commit-msg.tmp');
      fs.writeFileSync(tempFile, commitMessage);
      
      execSync(`git commit -F "${tempFile}"`, { stdio: 'inherit' });
      
      fs.unlinkSync(tempFile);
      
      console.log('\n' + chalk.bgGreen.white.bold('  🎉 提交成功！  ') + '\n');
      
      const generateChangelog = await inquirer.prompt([
        {
          type: 'confirm',
          name: 'generate',
          message: '📋 是否生成 CHANGELOG.md?',
          default: true
        }
      ]);

      if (generateChangelog.generate) {
        console.log(chalk.cyan('📝 正在生成 CHANGELOG.md...\n'));
        execSync('node scripts/generate-changelog.js', { stdio: 'inherit' });
      }
    } catch (error) {
      console.log(chalk.red('\n❌ 提交失败，请检查错误信息\n'));
      process.exit(1);
    }
  } else {
    console.log(chalk.yellow('\n⚠️  已取消提交\n'));
  }
}

runCommitWizard().catch(error => {
  console.error(chalk.red('❌ 发生错误:'), error);
  process.exit(1);
});
