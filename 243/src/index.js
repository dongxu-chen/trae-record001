const express = require('express');
const bodyParser = require('body-parser');
const winston = require('winston');
const path = require('path');
const yaml = require('yaml');

const config = require('./config');
const WebhookServer = require('./webhook/server');
const PipelineEngine = require('./pipeline/engine');
const CacheManager = require('./cache/manager');
const ArchiveManager = require('./archive/manager');
const DockerExecutor = require('./executors/docker');
const JenkinsIntegration = require('./integrations/jenkins');
const TemplateManager = require('./templates/manager');

const logger = winston.createLogger({
  level: config.logLevel || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'logs/pipeline.log' })
  ]
});

class CICDSystem {
  constructor() {
    this.app = express();
    this.logger = logger;
    this.config = config;
    
    this.pipelineEngine = new PipelineEngine({ logger, config });
    this.cacheManager = new CacheManager({ logger, config });
    this.archiveManager = new ArchiveManager({ logger, config });
    this.dockerExecutor = new DockerExecutor({ logger, config });
    this.jenkinsIntegration = new JenkinsIntegration({ logger, config });
    this.templateManager = new TemplateManager({ logger, config });
    this.webhookServer = new WebhookServer({
      logger,
      config,
      onPipelineTrigger: this.handlePipelineTrigger.bind(this)
    });
  }

  async initialize() {
    this.logger.info('初始化CI/CD系统...');
    
    await this.cacheManager.initialize();
    await this.archiveManager.initialize();
    await this.dockerExecutor.initialize();
    await this.jenkinsIntegration.initialize();
    await this.templateManager.initialize();
    
    this.setupMiddleware();
    this.setupRoutes();
    
    this.logger.info('CI/CD系统初始化完成');
  }

  setupMiddleware() {
    this.app.use(bodyParser.json({ limit: '10mb' }));
    this.app.use(bodyParser.urlencoded({ extended: true }));
    
    this.app.use(express.static(path.join(__dirname, '..', 'public')));
    
    this.app.use((req, res, next) => {
      this.logger.info(`${req.method} ${req.path}`);
      next();
    });
  }

  setupRoutes() {
    this.app.use('/webhook', this.webhookServer.router);
    
    this.app.get('/', (req, res) => {
      res.sendFile(path.join(__dirname, '..', 'public', 'index.html'));
    });
    
    this.app.get('/health', (req, res) => {
      res.json({ status: 'healthy', timestamp: new Date().toISOString() });
    });
    
    this.app.get('/pipelines', (req, res) => {
      res.json({ pipelines: this.pipelineEngine.getActivePipelines() });
    });
    this.app.get('/pipelines/:id', (req, res) => {
      const pipeline = this.pipelineEngine.getPipelineStatus(req.params.id);
      res.json(pipeline || { error: 'Pipeline not found' });
    });
    
    this.app.get('/queue', (req, res) => {
      const { group } = req.query;
      res.json({ queues: this.pipelineEngine.getQueueStatus(group) });
    });
    this.app.delete('/queue/:pipelineId', (req, res) => {
      const cancelled = this.pipelineEngine.cancelQueuedPipeline(req.params.pipelineId);
      res.json({ cancelled });
    });
    
    this.app.get('/cache/stats', async (req, res) => {
      res.json(this.cacheManager.getCacheStats());
    });
    this.app.get('/cache/:repository/:branch', async (req, res) => {
      const { repository, branch } = req.params;
      res.json({
        caches: await this.cacheManager.listCachesByBranch(repository, branch)
      });
    });
    
    this.app.get('/api/templates', async (req, res) => {
      const { category, search } = req.query;
      res.json({
        templates: this.templateManager.getTemplates(category, search),
        categories: this.templateManager.getCategories()
      });
    });
    
    this.app.get('/api/templates/:id', async (req, res) => {
      const template = this.templateManager.getTemplate(req.params.id);
      if (template) {
        res.json(template);
      } else {
        res.status(404).json({ error: 'Template not found' });
      }
    });
    
    this.app.post('/api/templates', async (req, res) => {
      try {
        const template = await this.templateManager.saveUserTemplate(req.body);
        res.json(template);
      } catch (err) {
        res.status(400).json({ error: err.message });
      }
    });
    
    this.app.delete('/api/templates/:id', async (req, res) => {
      const deleted = await this.templateManager.deleteUserTemplate(req.params.id);
      res.json({ deleted });
    });
    
    this.app.post('/api/templates/:id/generate', async (req, res) => {
      try {
        const configObj = this.templateManager.generateConfigFromTemplate(
          req.params.id,
          req.body
        );
        const yamlConfig = yaml.stringify(configObj);
        res.json({
          config: configObj,
          yaml: yamlConfig
        });
      } catch (err) {
        res.status(400).json({ error: err.message });
      }
    });
    
    this.app.post('/api/editor/export', async (req, res) => {
      try {
        const { pipeline, format = 'yaml' } = req.body;
        const configObj = this.convertEditorToConfig(pipeline);
        
        if (format === 'json') {
          res.json(configObj);
        } else {
          const yamlConfig = yaml.stringify(configObj);
          res.setHeader('Content-Type', 'text/yaml');
          res.send(yamlConfig);
        }
      } catch (err) {
        res.status(400).json({ error: err.message });
      }
    });
    
    this.app.get('/api/editor/stage-types', async (req, res) => {
      res.json({
        types: [
          { id: 'checkout', name: '代码检出', icon: 'git-branch', color: '#61afef' },
          { id: 'install', name: '依赖安装', icon: 'package', color: '#98c379' },
          { id: 'build', name: '编译构建', icon: 'hammer', color: '#e5c07b' },
          { id: 'test', name: '测试运行', icon: 'check-circle', color: '#56b6c2' },
          { id: 'quality', name: '质量检查', icon: 'shield', color: '#c678dd' },
          { id: 'package', name: '打包归档', icon: 'archive', color: '#d19a66' },
          { id: 'deploy', name: '部署发布', icon: 'rocket', color: '#e06c75' },
          { id: 'custom', name: '自定义脚本', icon: 'terminal', color: '#5c6370' }
        ]
      });
    });
  }

  convertEditorToConfig(editorData) {
    const stages = editorData.stages.map(stage => {
      const config = {
        name: stage.name,
        script: stage.script || []
      };

      if (stage.image) {
        config.image = stage.image;
      }

      if (stage.parallel && stage.tasks) {
        config.parallel = true;
        config.tasks = stage.tasks;
      }

      if (stage.cache) {
        config.cache = stage.cache;
      }

      if (stage.artifacts) {
        config.artifacts = stage.artifacts;
      }

      if (stage.condition) {
        config.condition = stage.condition;
      }

      if (stage.qualityGate) {
        config.qualityGate = stage.qualityGate;
      }

      if (stage.retry !== undefined) {
        config.retry = stage.retry;
      }

      if (stage.volumes) {
        config.volumes = stage.volumes;
      }

      return config;
    });

    return {
      name: editorData.name || 'My Pipeline',
      repository: editorData.repository || '',
      branch: editorData.branch || 'main',
      stages
    };
  }

  async handlePipelineTrigger(triggerData) {
    this.logger.info('收到流水线触发请求', { repo: triggerData.repository, branch: triggerData.branch });
    
    const result = await this.pipelineEngine.createPipeline({
      ...triggerData,
      cacheManager: this.cacheManager,
      archiveManager: this.archiveManager,
      dockerExecutor: this.dockerExecutor,
      jenkinsIntegration: this.jenkinsIntegration
    });

    return {
      pipelineId: result.pipelineId,
      status: result.queuePosition > 1 ? 'queued' : 'pending',
      queuePosition: result.queuePosition
    };
  }

  async start() {
    await this.initialize();
    
    const port = this.config.port || 3000;
    this.app.listen(port, () => {
      this.logger.info(`CI/CD服务器运行在端口 ${port}`);
      this.logger.info(`Webhook端点: /webhook/github 和 /webhook/gitlab`);
    });
  }
}

if (require.main === module) {
  const system = new CICDSystem();
  system.start().catch(err => {
    console.error('启动失败:', err);
    process.exit(1);
  });
}

module.exports = CICDSystem;
