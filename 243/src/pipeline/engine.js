const { v4: uuidv4 } = require('uuid');
const async = require('async');
const path = require('path');
const fs = require('fs-extra');

const PipelineContext = require('./context');
const StageExecutor = require('./stage');
const PipelineQueue = require('./queue');

class PipelineEngine {
  constructor({ logger, config }) {
    this.logger = logger;
    this.config = config;
    this.pipelines = new Map();
    this.activePipelines = new Set();
    this.queue = new PipelineQueue({ logger, config });
    
    this.setupQueueEvents();
  }

  setupQueueEvents() {
    this.queue.on('queued', ({ pipelineId, groupKey, position }) => {
      const pipeline = this.pipelines.get(pipelineId);
      if (pipeline) {
        pipeline.status = 'queued';
        pipeline.queuePosition = position;
      }
    });

    this.queue.on('dequeued', ({ pipelineId }) => {
      const pipeline = this.pipelines.get(pipelineId);
      if (pipeline) {
        pipeline.status = 'pending';
        pipeline.queuePosition = null;
      }
    });
  }

  async createPipeline(triggerData) {
    const pipelineId = uuidv4();
    const workspace = path.join(this.config.workDir, pipelineId);
    
    const pipeline = {
      id: pipelineId,
      status: 'pending',
      triggerData,
      workspace,
      stages: [],
      startTime: null,
      endTime: null,
      context: null,
      artifacts: [],
      error: null,
      queuePosition: null
    };

    this.pipelines.set(pipelineId, pipeline);
    
    const position = await this.queue.enqueue(
      pipelineId, 
      triggerData,
      async () => {
        await this.executePipeline(pipelineId, triggerData);
      }
    );

    return { pipelineId, queuePosition: position };
  }

  async executePipeline(pipelineId, triggerData) {
    const pipeline = this.pipelines.get(pipelineId);
    if (!pipeline) {
      throw new Error(`流水线 ${pipelineId} 不存在`);
    }

    try {
      pipeline.status = 'running';
      pipeline.startTime = new Date();
      this.activePipelines.add(pipelineId);

      await fs.ensureDir(pipeline.workspace);
      
      pipeline.context = new PipelineContext({
        pipelineId,
        workspace: pipeline.workspace,
        logger: this.logger,
        triggerData
      });

      const repoConfig = this.getRepositoryConfig(triggerData.repository);
      const stages = repoConfig?.stages || this.getDefaultStages();

      pipeline.stages = stages.map(stage => ({
        name: typeof stage === 'string' ? stage : stage.name,
        status: 'pending',
        startTime: null,
        endTime: null,
        error: null
      }));

      for (let i = 0; i < pipeline.stages.length; i++) {
        const stageConfig = typeof stages[i] === 'string' 
          ? { name: stages[i] } 
          : stages[i];
        
        const maxRetries = stageConfig.retry ?? this.config.pipeline?.defaultRetries ?? 3;
        const stageResult = await this.executeStageWithRetry(pipeline, stageConfig, i, maxRetries);
        
        if (!stageResult.success && stageConfig.required !== false) {
          pipeline.status = 'failed';
          pipeline.error = `阶段 ${stageConfig.name} 执行失败（重试${stageResult.attempts}次后仍然失败）`;
          break;
        }
      }

      if (pipeline.status === 'running') {
        pipeline.status = 'success';
      }

    } catch (err) {
      pipeline.status = 'failed';
      pipeline.error = err.message;
      this.logger.error('流水线执行异常', { pipelineId, error: err.stack });
    } finally {
      pipeline.endTime = new Date();
      this.activePipelines.delete(pipelineId);
      
      const duration = pipeline.endTime - pipeline.startTime;
      this.logger.info('流水线执行完成', { 
        pipelineId, 
        status: pipeline.status, 
        duration: `${duration}ms` 
      });
    }
  }

  async executeStageWithRetry(pipeline, stageConfig, stageIndex, maxRetries) {
    const stage = pipeline.stages[stageIndex];
    let lastResult = null;
    let attempts = 0;

    while (attempts <= maxRetries) {
      attempts++;
      
      if (attempts > 1) {
        const retryDelay = Math.min(1000 * Math.pow(2, attempts - 2), 10000);
        this.logger.info(`阶段 ${stage.name} 第 ${attempts} 次重试（最大 ${maxRetries + 1} 次）`, {
          pipelineId: pipeline.id,
          stage: stage.name,
          attempt: attempts,
          maxAttempts: maxRetries + 1,
          delay: retryDelay
        });
        await this.sleep(retryDelay);
      }

      stage.attempts = attempts;
      lastResult = await this.executeStage(pipeline, stageConfig, stageIndex);

      if (lastResult.success) {
        if (attempts > 1) {
          this.logger.info(`阶段 ${stage.name} 重试成功`, {
            pipelineId: pipeline.id,
            stage: stage.name,
            attempts
          });
        }
        return { ...lastResult, attempts };
      }

      if (!this.shouldRetry(stageConfig, lastResult)) {
        break;
      }
    }

    this.logger.warn(`阶段 ${stage.name} 重试失败`, {
      pipelineId: pipeline.id,
      stage: stage.name,
      attempts
    });

    return { ...lastResult, attempts };
  }

  shouldRetry(stageConfig, result) {
    if (stageConfig.retryOn) {
      if (Array.isArray(stageConfig.retryOn)) {
        return stageConfig.retryOn.some(condition => {
          if (condition === 'always') return true;
          if (condition === 'failure') return !result.success;
          if (condition === 'timeout') return result.error?.includes('timeout');
          return false;
        });
      }
    }
    return !result.success;
  }

  async executeStage(pipeline, stageConfig, stageIndex) {
    const stage = pipeline.stages[stageIndex];
    stage.status = 'running';
    if (!stage.startTime) {
      stage.startTime = new Date();
    }

    if (pipeline.context.blockDeployment && stageConfig.name === 'deploy') {
      this.logger.warn('质量红线不通过，跳过部署阶段', { 
        pipelineId: pipeline.id, 
        stage: stage.name 
      });
      stage.status = 'skipped';
      stage.endTime = new Date();
      return { success: true, skipped: true, reason: '质量红线阻断部署' };
    }

    this.logger.info('开始执行阶段', { 
      pipelineId: pipeline.id, 
      stage: stage.name,
      attempt: stage.attempts || 1
    });

    const executor = new StageExecutor({
      logger: this.logger,
      config: this.config,
      context: pipeline.context
    });

    try {
      const result = await executor.execute(stageConfig, {
        cacheManager: pipeline.context.cacheManager,
        archiveManager: pipeline.context.archiveManager,
        dockerExecutor: pipeline.context.dockerExecutor,
        jenkinsIntegration: pipeline.context.jenkinsIntegration
      });

      if (result.success) {
        stage.status = 'success';
        stage.endTime = new Date();

        if (stageConfig.qualityGate) {
          const qualityResult = await this.checkQualityGate(
            pipeline, 
            stageConfig, 
            stageIndex
          );
          
          stage.qualityGate = qualityResult;
          
          if (!qualityResult.passed) {
            stage.status = 'quality-gate-failed';
            result.success = false;
            result.qualityGate = qualityResult;
            result.error = qualityResult.error;
            
            if (qualityResult.blockDeployment) {
              pipeline.context.blockDeployment = true;
              this.logger.warn('质量红线阻断后续部署阶段', { pipelineId: pipeline.id });
            }
          }
        }
      }

      if (result.artifacts) {
        pipeline.artifacts.push(...result.artifacts);
      }

      this.logger.info('阶段执行完成', { 
        pipelineId: pipeline.id, 
        stage: stage.name,
        status: stage.status
      });

      return result;
    } catch (err) {
      this.logger.error('阶段执行异常', { 
        pipelineId: pipeline.id, 
        stage: stage.name,
        error: err.message 
      });

      return { success: false, error: err.message };
    }
  }

  async checkQualityGate(pipeline, stageConfig, stageIndex) {
    if (!this.qualityGate) {
      const QualityGate = require('../quality/gate');
      this.qualityGate = new QualityGate({
        logger: this.logger,
        config: this.config
      });
    }

    return this.qualityGate.checkQualityGate(
      stageConfig,
      pipeline.workspace,
      pipeline.context
    );
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  getRepositoryConfig(repoName) {
    return this.config.repositories?.find(
      repo => repo.name === repoName || repo.url?.includes(repoName)
    );
  }

  getDefaultStages() {
    return this.config.pipeline?.defaultStages || [
      'checkout',
      'compile',
      'test',
      'build',
      'deploy'
    ];
  }

  getPipelineStatus(pipelineId) {
    const pipeline = this.pipelines.get(pipelineId);
    if (!pipeline) return null;

    return {
      id: pipeline.id,
      status: pipeline.status,
      triggerData: pipeline.triggerData,
      startTime: pipeline.startTime,
      endTime: pipeline.endTime,
      duration: pipeline.endTime ? pipeline.endTime - pipeline.startTime : null,
      stages: pipeline.stages,
      artifacts: pipeline.artifacts,
      error: pipeline.error,
      queuePosition: pipeline.queuePosition
    };
  }

  getActivePipelines() {
    return Array.from(this.activePipelines).map(id => this.getPipelineStatus(id));
  }

  getPipelineHistory(limit = 100) {
    return Array.from(this.pipelines.values())
      .sort((a, b) => b.startTime - a.startTime)
      .slice(0, limit)
      .map(p => this.getPipelineStatus(p.id));
  }

  getQueueStatus(groupKey) {
    if (groupKey) {
      return this.queue.getQueueStatus(groupKey);
    }
    return this.queue.getAllQueueStatus();
  }

  cancelQueuedPipeline(pipelineId) {
    return this.queue.cancelPipeline(pipelineId);
  }
}

module.exports = PipelineEngine;
