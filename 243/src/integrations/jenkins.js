const axios = require('axios');

class JenkinsIntegration {
  constructor({ logger, config }) {
    this.logger = logger;
    this.config = config;
    this.baseUrl = config.jenkins?.url;
    this.username = config.jenkins?.username;
    this.apiToken = config.jenkins?.apiToken;
    this.enabled = config.jenkins?.enabled || false;
  }

  async initialize() {
    if (!this.enabled) {
      this.logger.info('Jenkins集成已禁用');
      return;
    }

    try {
      await this.testConnection();
      this.logger.info('Jenkins连接成功', { url: this.baseUrl });
    } catch (err) {
      this.logger.warn('Jenkins连接失败', { error: err.message });
    }
  }

  async testConnection() {
    const response = await this.makeRequest('get', '/api/json');
    return response.data;
  }

  async makeRequest(method, path, data = null) {
    const url = `${this.baseUrl}${path}`;
    
    const auth = {
      username: this.username,
      password: this.apiToken
    };

    const config = {
      method,
      url,
      auth,
      headers: {
        'Content-Type': 'application/json'
      }
    };

    if (data) {
      config.data = data;
    }

    try {
      return await axios(config);
    } catch (err) {
      this.logger.error('Jenkins API请求失败', { 
        method, 
        path, 
        error: err.response?.data || err.message 
      });
      throw err;
    }
  }

  async triggerJob({ jobName, parameters = {} }) {
    if (!this.enabled) {
      throw new Error('Jenkins集成未启用');
    }

    this.logger.info('触发Jenkins任务', { jobName, parameters });

    try {
      const jobPath = encodeURIComponent(jobName).replace(/%2F/g, '/job/');
      
      let triggerPath;
      let requestData = null;

      if (Object.keys(parameters).length > 0) {
        triggerPath = `/job/${jobPath}/buildWithParameters`;
        requestData = new URLSearchParams(parameters).toString();
      } else {
        triggerPath = `/job/${jobPath}/build`;
      }

      const response = await this.makeRequest('post', triggerPath, requestData);
      
      const queueLocation = response.headers.location;
      const queueId = queueLocation ? queueLocation.match(/\/(\d+)\/?$/)?.[1] : null;

      this.logger.info('Jenkins任务已触发', { jobName, queueId });

      const buildInfo = await this.waitForBuildStart(queueId, jobName);
      
      if (buildInfo) {
        const result = await this.waitForBuildComplete(jobName, buildInfo.number);
        return {
          success: result.result === 'SUCCESS',
          buildNumber: buildInfo.number,
          result: result.result,
          url: result.url,
          queueId
        };
      }

      return {
        success: true,
        queueId,
        message: '任务已加入队列'
      };
    } catch (err) {
      this.logger.error('触发Jenkins任务失败', { jobName, error: err.message });
      return {
        success: false,
        error: err.message
      };
    }
  }

  async waitForBuildStart(queueId, jobName, timeout = 300000) {
    const startTime = Date.now();
    const pollInterval = 2000;

    while (Date.now() - startTime < timeout) {
      try {
        const response = await this.makeRequest('get', `/queue/item/${queueId}/api/json`);
        const queueItem = response.data;

        if (queueItem.cancelled) {
          this.logger.warn('Jenkins任务已取消', { queueId });
          return null;
        }

        if (queueItem.executable) {
          return queueItem.executable;
        }

        await this.sleep(pollInterval);
      } catch (err) {
        this.logger.warn('轮询队列状态失败', { queueId, error: err.message });
        await this.sleep(pollInterval);
      }
    }

    this.logger.warn('等待Jenkins任务启动超时', { queueId });
    return null;
  }

  async waitForBuildComplete(jobName, buildNumber, timeout = 3600000) {
    const startTime = Date.now();
    const pollInterval = 5000;
    const jobPath = encodeURIComponent(jobName).replace(/%2F/g, '/job/');

    while (Date.now() - startTime < timeout) {
      try {
        const response = await this.makeRequest(
          'get', 
          `/job/${jobPath}/${buildNumber}/api/json`
        );
        const buildInfo = response.data;

        if (!buildInfo.building) {
          this.logger.info('Jenkins任务完成', { 
            jobName, 
            buildNumber, 
            result: buildInfo.result 
          });
          return buildInfo;
        }

        await this.sleep(pollInterval);
      } catch (err) {
        this.logger.warn('轮询构建状态失败', { buildNumber, error: err.message });
        await this.sleep(pollInterval);
      }
    }

    throw new Error('等待Jenkins任务完成超时');
  }

  async getJobInfo(jobName) {
    if (!this.enabled) {
      throw new Error('Jenkins集成未启用');
    }

    const jobPath = encodeURIComponent(jobName).replace(/%2F/g, '/job/');
    const response = await this.makeRequest('get', `/job/${jobPath}/api/json`);
    return response.data;
  }

  async getBuildInfo(jobName, buildNumber) {
    if (!this.enabled) {
      throw new Error('Jenkins集成未启用');
    }

    const jobPath = encodeURIComponent(jobName).replace(/%2F/g, '/job/');
    const response = await this.makeRequest(
      'get', 
      `/job/${jobPath}/${buildNumber}/api/json`
    );
    return response.data;
  }

  async getBuildLog(jobName, buildNumber) {
    if (!this.enabled) {
      throw new Error('Jenkins集成未启用');
    }

    const jobPath = encodeURIComponent(jobName).replace(/%2F/g, '/job/');
    const response = await this.makeRequest(
      'get', 
      `/job/${jobPath}/${buildNumber}/consoleText`
    );
    return response.data;
  }

  async listJobs() {
    if (!this.enabled) {
      throw new Error('Jenkins集成未启用');
    }

    const response = await this.makeRequest('get', '/api/json');
    return response.data.jobs || [];
  }

  async createJob(jobName, configXml) {
    if (!this.enabled) {
      throw new Error('Jenkins集成未启用');
    }

    this.logger.info('创建Jenkins任务', { jobName });

    await this.makeRequest(
      'post', 
      `/createItem?name=${encodeURIComponent(jobName)}`,
      configXml
    );

    return { success: true, jobName };
  }

  async deleteJob(jobName) {
    if (!this.enabled) {
      throw new Error('Jenkins集成未启用');
    }

    this.logger.info('删除Jenkins任务', { jobName });

    const jobPath = encodeURIComponent(jobName).replace(/%2F/g, '/job/');
    await this.makeRequest('post', `/job/${jobPath}/doDelete`);

    return { success: true, jobName };
  }

  async getBuildArtifacts(jobName, buildNumber) {
    if (!this.enabled) {
      throw new Error('Jenkins集成未启用');
    }

    const buildInfo = await this.getBuildInfo(jobName, buildNumber);
    return buildInfo.artifacts || [];
  }

  async downloadArtifact(jobName, buildNumber, artifactPath) {
    if (!this.enabled) {
      throw new Error('Jenkins集成未启用');
    }

    const jobPath = encodeURIComponent(jobName).replace(/%2F/g, '/job/');
    const response = await this.makeRequest(
      'get', 
      `/job/${jobPath}/${buildNumber}/artifact/${artifactPath}`,
      null,
      { responseType: 'stream' }
    );

    return response.data;
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

module.exports = JenkinsIntegration;
