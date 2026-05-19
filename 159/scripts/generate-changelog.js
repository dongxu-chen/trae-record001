const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
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

console.log(chalk.bgBlue.white.bold('  📝 生成 CHANGELOG.md  ') + '\n');

function getGitCommits() {
  try {
    const output = execSync('git log --pretty=format:"%H|%ad|%s|%an" --date=format:"%Y-%m-%d" --no-merges', {
      encoding: 'utf-8'
    });
    return output.trim().split('\n').filter(line => line).map(line => {
      const [hash, date, subject, author] = line.split('|');
      return { hash, date, subject, author };
    });
  } catch (error) {
    console.log(chalk.yellow('⚠️  无法获取Git提交记录，可能是没有初始化Git仓库'));
    return [];
  }
}

function parseCommit(subject) {
  const match = subject.match(/^(\w+)(?:\(([^)]+)\))?:\s*(.+)$/);
  if (match) {
    return {
      type: match[1],
      scope: match[2] || '',
      message: match[3]
    };
  }
  return { type: 'other', scope: '', message: subject };
}

function generateChangelog() {
  const commits = getGitCommits();
  
  if (commits.length === 0) {
    console.log(chalk.yellow('⚠️  没有找到Git提交记录'));
    return;
  }

  console.log(chalk.cyan(`📊 共找到 ${commits.length} 条提交记录\n`));

  const groupedByDate = {};
  commits.forEach(commit => {
    if (!groupedByDate[commit.date]) {
      groupedByDate[commit.date] = [];
    }
    groupedByDate[commit.date].push(commit);
  });

  let changelog = '# CHANGELOG\n\n';
  changelog += '> 本文件由 `npm run changelog` 自动生成\n\n';

  const sortedDates = Object.keys(groupedByDate).sort().reverse();
  
  sortedDates.forEach(date => {
    changelog += `## ${date}\n\n`;
    
    const dayCommits = groupedByDate[date];
    const groupedByType = {};
    
    dayCommits.forEach(commit => {
      const parsed = parseCommit(commit.subject);
      if (!groupedByType[parsed.type]) {
        groupedByType[parsed.type] = [];
      }
      groupedByType[parsed.type].push({ ...commit, parsed });
    });

    const typeOrder = ['feat', 'fix', 'docs', 'refactor', 'perf', 'style', 'test', 'build', 'ci', 'chore', 'revert', 'other'];
    
    typeOrder.forEach(type => {
      if (groupedByType[type] && groupedByType[type].length > 0) {
        const emoji = TYPE_EMOJIS[type] || '•';
        const desc = TYPE_DESCRIPTIONS[type] || type;
        changelog += `### ${emoji} ${desc}\n\n`;
        
        groupedByType[type].forEach(commit => {
          const scope = commit.parsed.scope ? `**${commit.parsed.scope}:** ` : '';
          const shortHash = commit.hash.substring(0, 7);
          changelog += `- ${scope}${commit.parsed.message} (${shortHash})\n`;
        });
        
        changelog += '\n';
      }
    });
  });

  changelog += '---\n\n';
  changelog += '## 提交类型说明\n\n';
  CONFIG.types.forEach(type => {
    const emoji = TYPE_EMOJIS[type] || '';
    const desc = TYPE_DESCRIPTIONS[type] || '';
    changelog += `- ${emoji} \`${type}\` - ${desc}\n`;
  });

  const changelogPath = path.resolve(process.cwd(), 'CHANGELOG.md');
  fs.writeFileSync(changelogPath, changelog, 'utf-8');
  
  console.log(chalk.green('✅ CHANGELOG.md 生成成功！'));
  console.log(chalk.gray(`📍 保存位置: ${changelogPath}\n`));
}

generateChangelog();
