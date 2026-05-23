const fs = require('fs');
const path = require('path');
const yaml = require('yaml');

const DEFAULT_CONFIG = {
  port: 3000,
  logLevel: 'info',
  workDir: path.join(process.cwd(), 'workspace'),
  cacheDir: path.join(process.cwd(), 'cache'),
  archiveDir: path.join(process.cwd(), 'archives'),
  
  webhook: {
    github: {
      secret: process.env.GITHUB_WEBHOOK_SECRET || 'github-secret',
      enabled: true
    },
    gitlab: {
      secret: process.env.GITLAB_WEBHOOK_SECRET || 'gitlab-secret',
      enabled: true
    }
  },
  
  docker: {
    socketPath: '/var/run/docker.sock',
    defaultImage: 'node:18-alpine',
    network: 'cicd-network',
    timeout: 3600000
  },
  
  jenkins: {
    url: process.env.JENKINS_URL || 'http://localhost:8080',
    username: process.env.JENKINS_USERNAME || 'admin',
    apiToken: process.env.JENKINS_API_TOKEN || 'admin-token',
    enabled: false
  },
  
  repositories: [],
  
  cache: {
    enabled: true,
    ttl: 86400000,
    maxSize: '10GB'
  },
  
  pipeline: {
    defaultStages: ['compile', 'test', 'build', 'deploy'],
    timeout: 7200000,
    maxParallel: 4
  }
};

function loadConfig() {
  const configPath = path.join(process.cwd(), 'config.yaml');
  let userConfig = {};
  
  if (fs.existsSync(configPath)) {
    try {
      const fileContent = fs.readFileSync(configPath, 'utf8');
      userConfig = yaml.parse(fileContent);
    } catch (err) {
      console.warn('配置文件解析失败，使用默认配置:', err.message);
    }
  }
  
  return mergeConfigs(DEFAULT_CONFIG, userConfig);
}

function mergeConfigs(defaults, user) {
  const merged = { ...defaults };
  
  for (const key in user) {
    if (typeof user[key] === 'object' && user[key] !== null && !Array.isArray(user[key])) {
      merged[key] = mergeConfigs(defaults[key] || {}, user[key]);
    } else {
      merged[key] = user[key];
    }
  }
  
  return merged;
}

module.exports = loadConfig();
