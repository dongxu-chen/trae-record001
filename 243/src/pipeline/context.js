class PipelineContext {
  constructor({ pipelineId, workspace, logger, triggerData }) {
    this.pipelineId = pipelineId;
    this.workspace = workspace;
    this.logger = logger;
    this.triggerData = triggerData;
    this.variables = new Map();
    this.stageResults = new Map();
    this.status = 'running';
  }

  setVariable(key, value) {
    this.variables.set(key, value);
  }

  getVariable(key, defaultValue = null) {
    return this.variables.get(key) || defaultValue;
  }

  setStageResult(stageName, result) {
    this.stageResults.set(stageName, result);
  }

  getStageResult(stageName) {
    return this.stageResults.get(stageName);
  }

  getPreviousStageResults() {
    return Array.from(this.stageResults.values());
  }

  isStageSuccessful(stageName) {
    const result = this.stageResults.get(stageName);
    return result?.success === true;
  }

  hasFailedStages() {
    return Array.from(this.stageResults.values()).some(r => r.success === false);
  }

  getEnvironmentVariables() {
    const env = {
      PIPELINE_ID: this.pipelineId,
      WORKSPACE: this.workspace,
      CI: 'true',
      GIT_BRANCH: this.triggerData.branch || '',
      GIT_COMMIT: this.triggerData.commit || '',
      GIT_REPOSITORY: this.triggerData.repository || '',
      GIT_AUTHOR: this.triggerData.author || ''
    };

    this.variables.forEach((value, key) => {
      env[key] = value;
    });

    return env;
  }
}

module.exports = PipelineContext;
