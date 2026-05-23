const async = require('async');

class StageExecutor {
  constructor({ logger, config, context }) {
    this.logger = logger;
    this.config = config;
    this.context = context;
  }

  async execute(stageConfig, services) {
    this.logger.info('执行阶段配置', { stage: stageConfig.name });

    if (!this.checkCondition(stageConfig)) {
      this.logger.info('阶段条件不满足，跳过执行', { stage: stageConfig.name });
      return { success: true, skipped: true };
    }

    const tasks = stageConfig.parallel 
      ? this.buildParallelTasks(stageConfig, services)
      : this.buildSequentialTasks(stageConfig, services);

    try {
      const results = await this.executeTasks(tasks, stageConfig.parallel);
      
      const success = results.every(r => r.success);
      
      this.context.setStageResult(stageConfig.name, {
        success,
        results,
        completedAt: new Date()
      });

      return {
        success,
        results,
        artifacts: this.collectArtifacts(results)
      };
    } catch (err) {
      this.logger.error('阶段执行失败', { stage: stageConfig.name, error: err.message });
      return { success: false, error: err.message };
    }
  }

  checkCondition(stageConfig) {
    if (!stageConfig.condition) {
      return true;
    }

    const condition = stageConfig.condition;
    
    if (typeof condition === 'string') {
      return this.evaluateConditionString(condition);
    }
    
    if (typeof condition === 'object') {
      if (condition.branch) {
        const currentBranch = this.context.triggerData.branch;
        if (Array.isArray(condition.branch)) {
          return condition.branch.includes(currentBranch);
        }
        return currentBranch === condition.branch;
      }
      
      if (condition.previousStage) {
        return this.context.isStageSuccessful(condition.previousStage);
      }
      
      if (condition.status) {
        const hasFailed = this.context.hasFailedStages();
        if (condition.status === 'success') return !hasFailed;
        if (condition.status === 'failure') return hasFailed;
      }
    }

    return true;
  }

  evaluateConditionString(condition) {
    try {
      const env = this.context.getEnvironmentVariables();
      const fn = new Function(...Object.keys(env), `return ${condition}`);
      return fn(...Object.values(env));
    } catch (err) {
      this.logger.warn('条件评估失败', { condition, error: err.message });
      return false;
    }
  }

  buildParallelTasks(stageConfig, services) {
    const tasks = stageConfig.tasks || [stageConfig];
    return tasks.map(task => async () => {
      return this.executeSingleTask(task, services);
    });
  }

  buildSequentialTasks(stageConfig, services) {
    const tasks = stageConfig.tasks || [stageConfig];
    return tasks.map(task => async () => {
      return this.executeSingleTask(task, services);
    });
  }

  async executeTasks(taskFns, parallel = false) {
    if (parallel) {
      const maxParallel = this.config.pipeline?.maxParallel || 4;
      return async.parallelLimit(taskFns, maxParallel);
    }
    
    const results = [];
    for (const taskFn of taskFns) {
      results.push(await taskFn());
    }
    return results;
  }

  async executeSingleTask(taskConfig, services) {
    const taskName = taskConfig.name || 'task';
    this.logger.info('执行任务', { task: taskName });

    try {
      if (taskConfig.useDocker !== false) {
        return await this.executeDockerTask(taskConfig, services);
      }
      
      if (taskConfig.useJenkins && services.jenkinsIntegration) {
        return await this.executeJenkinsTask(taskConfig, services);
      }

      return await this.executeLocalTask(taskConfig, services);
    } catch (err) {
      this.logger.error('任务执行失败', { task: taskName, error: err.message });
      return { success: false, name: taskName, error: err.message };
    }
  }

  async executeDockerTask(taskConfig, services) {
    const { dockerExecutor, cacheManager } = services;
    
    const cacheKey = taskConfig.cache?.key;
    const cachePaths = taskConfig.cache?.paths || [];
    const repository = this.context.triggerData?.repository || 'default';
    const branch = this.context.triggerData?.branch || 'default';
    
    if (cacheKey && cacheManager) {
      await cacheManager.restoreCache(cacheKey, cachePaths, this.context.workspace, {
        repository,
        branch,
        fallbackToDefaultBranch: taskConfig.cache?.fallbackToDefaultBranch !== false
      });
    }

    const result = await dockerExecutor.execute({
      image: taskConfig.image || this.config.docker.defaultImage,
      commands: Array.isArray(taskConfig.script) ? taskConfig.script : [taskConfig.script],
      workspace: this.context.workspace,
      environment: { ...this.context.getEnvironmentVariables(), ...taskConfig.environment },
      volumes: taskConfig.volumes || [],
      timeout: taskConfig.timeout || this.config.docker.timeout
    });

    if (cacheKey && cacheManager && result.success) {
      await cacheManager.saveCache(cacheKey, cachePaths, this.context.workspace, {
        repository,
        branch
      });
    }

    return {
      ...result,
      name: taskConfig.name || 'docker-task'
    };
  }

  async executeJenkinsTask(taskConfig, services) {
    const { jenkinsIntegration } = services;
    
    if (!jenkinsIntegration) {
      throw new Error('Jenkins集成未配置');
    }

    const result = await jenkinsIntegration.triggerJob({
      jobName: taskConfig.jobName,
      parameters: {
        ...this.context.getEnvironmentVariables(),
        ...taskConfig.parameters
      }
    });

    return {
      ...result,
      name: taskConfig.name || 'jenkins-task'
    };
  }

  async executeLocalTask(taskConfig, services) {
    const { spawn } = require('child_process');
    
    const commands = Array.isArray(taskConfig.script) ? taskConfig.script : [taskConfig.script];
    const env = { ...process.env, ...this.context.getEnvironmentVariables(), ...taskConfig.environment };

    for (const cmd of commands) {
      this.logger.info('执行命令', { command: cmd });
      
      await new Promise((resolve, reject) => {
        const parts = cmd.split(' ');
        const child = spawn(parts[0], parts.slice(1), {
          cwd: this.context.workspace,
          env,
          shell: true
        });

        child.stdout.on('data', data => {
          this.logger.info(data.toString().trim());
        });

        child.stderr.on('data', data => {
          this.logger.warn(data.toString().trim());
        });

        child.on('close', code => {
          if (code === 0) {
            resolve();
          } else {
            reject(new Error(`命令执行失败，退出码: ${code}`));
          }
        });
      });
    }

    return { success: true, name: taskConfig.name || 'local-task' };
  }

  collectArtifacts(results) {
    const artifacts = [];
    results.forEach(result => {
      if (result.artifacts) {
        artifacts.push(...result.artifacts);
      }
    });
    return artifacts;
  }
}

module.exports = StageExecutor;
