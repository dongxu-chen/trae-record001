const express = require('express');
const crypto = require('crypto');

class WebhookServer {
  constructor({ logger, config, onPipelineTrigger }) {
    this.logger = logger;
    this.config = config;
    this.onPipelineTrigger = onPipelineTrigger;
    this.router = express.Router();
    
    this.setupRoutes();
  }

  setupRoutes() {
    this.router.post('/github', this.handleGithubWebhook.bind(this));
    this.router.post('/gitlab', this.handleGitlabWebhook.bind(this));
  }

  verifyGithubSignature(req, secret) {
    const signature = req.headers['x-hub-signature-256'];
    if (!signature) return false;

    const hmac = crypto.createHmac('sha256', secret);
    const digest = 'sha256=' + hmac.update(JSON.stringify(req.body)).digest('hex');
    
    return crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(digest));
  }

  verifyGitlabToken(req, secret) {
    const token = req.headers['x-gitlab-token'];
    return token === secret;
  }

  async handleGithubWebhook(req, res) {
    try {
      const event = req.headers['x-github-event'];
      const delivery = req.headers['x-github-delivery'];
      
      this.logger.info('收到GitHub Webhook', { event, delivery });

      if (this.config.webhook.github.secret && 
          !this.verifyGithubSignature(req, this.config.webhook.github.secret)) {
        this.logger.warn('GitHub Webhook签名验证失败');
        return res.status(403).json({ error: 'Invalid signature' });
      }

      if (event === 'ping') {
        return res.json({ message: 'pong' });
      }

      if (event !== 'push') {
        return res.json({ message: 'Event ignored' });
      }

      const triggerData = this.parseGithubPayload(req.body);
      const result = await this.onPipelineTrigger(triggerData);
      
      res.json({ status: 'accepted', ...result });
    } catch (err) {
      this.logger.error('处理GitHub Webhook失败', err);
      res.status(500).json({ error: err.message });
    }
  }

  async handleGitlabWebhook(req, res) {
    try {
      const event = req.headers['x-gitlab-event'];
      
      this.logger.info('收到GitLab Webhook', { event });

      if (this.config.webhook.gitlab.secret && 
          !this.verifyGitlabToken(req, this.config.webhook.gitlab.secret)) {
        this.logger.warn('GitLab Webhook令牌验证失败');
        return res.status(403).json({ error: 'Invalid token' });
      }

      if (event === 'Push Hook') {
        const triggerData = this.parseGitlabPayload(req.body);
        const result = await this.onPipelineTrigger(triggerData);
        return res.json({ status: 'accepted', ...result });
      }

      res.json({ message: 'Event ignored' });
    } catch (err) {
      this.logger.error('处理GitLab Webhook失败', err);
      res.status(500).json({ error: err.message });
    }
  }

  parseGithubPayload(payload) {
    const branch = payload.ref?.replace('refs/heads/', '');
    const commit = payload.head_commit?.id;
    const message = payload.head_commit?.message;
    const author = payload.head_commit?.author?.name;
    const repository = payload.repository?.full_name;
    const cloneUrl = payload.repository?.clone_url;
    const sshUrl = payload.repository?.ssh_url;

    return {
      source: 'github',
      repository,
      branch,
      commit,
      message,
      author,
      cloneUrl,
      sshUrl,
      commitUrl: payload.head_commit?.url,
      compareUrl: payload.compare,
      timestamp: new Date().toISOString()
    };
  }

  parseGitlabPayload(payload) {
    const branch = payload.ref?.replace('refs/heads/', '');
    const commit = payload.checkout_sha;
    const message = payload.commits?.[0]?.message;
    const author = payload.commits?.[0]?.author?.name;
    const repository = payload.project?.path_with_namespace;
    const cloneUrl = payload.project?.git_http_url;
    const sshUrl = payload.project?.git_ssh_url;

    return {
      source: 'gitlab',
      repository,
      branch,
      commit,
      message,
      author,
      cloneUrl,
      sshUrl,
      commitUrl: payload.commits?.[0]?.url,
      compareUrl: payload.project?.web_url + '/compare/' + payload.before + '...' + payload.after,
      timestamp: new Date().toISOString()
    };
  }
}

module.exports = WebhookServer;
