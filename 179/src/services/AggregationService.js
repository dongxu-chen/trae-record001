const cron = require('node-cron');
const axios = require('axios');
const Message = require('../models/Message');
const AggregationLog = require('../models/AggregationLog');
const UserPreference = require('../models/UserPreference');
const config = require('../config');
const logger = require('../utils/logger');

class AggregationService {
  constructor() {
    this.scheduledTasks = new Map();
    this.urgentNotificationCooldown = new Map();
    this.cooldownPeriod = 60000;
  }

  async start() {
    if (!config.aggregation.enabled) {
      logger.info('Aggregation service is disabled');
      return;
    }

    logger.info('Starting aggregation service');

    await this.scheduleDefaultTask();
    await this.scheduleMessageFetchTask();
    await this.scheduleUrgentCheckTask();

    logger.info('Aggregation service started');
  }

  async scheduleDefaultTask() {
    const cronExpression = config.aggregation.cron;

    if (this.scheduledTasks.has('default')) {
      this.scheduledTasks.get('default').stop();
    }

    const task = cron.schedule(cronExpression, async () => {
      logger.info('Running default aggregation task');
      await this.runAggregation('default');
    }, {
      scheduled: true,
      timezone: 'Asia/Shanghai'
    });

    this.scheduledTasks.set('default', task);
    logger.info(`Scheduled default aggregation task with cron: ${cronExpression}`);
  }

  async scheduleMessageFetchTask() {
    const cronExpression = '*/60 * * * * *';

    if (this.scheduledTasks.has('fetch')) {
      this.scheduledTasks.get('fetch').stop();
    }

    const task = cron.schedule(cronExpression, async () => {
      logger.debug('Running scheduled message fetch');
      const messageService = require('./MessageService');
      try {
        await messageService.fetchFromAllChannels();
      } catch (error) {
        logger.error('Scheduled message fetch failed:', error);
      }
    }, {
      scheduled: true,
      timezone: 'Asia/Shanghai'
    });

    this.scheduledTasks.set('fetch', task);
    logger.info('Scheduled message fetch task (every 60 seconds)');
  }

  async scheduleUrgentCheckTask() {
    const cronExpression = '*/30 * * * * *';

    if (this.scheduledTasks.has('urgent')) {
      this.scheduledTasks.get('urgent').stop();
    }

    const task = cron.schedule(cronExpression, async () => {
      logger.debug('Running urgent message check');
      try {
        await this.checkAndSendUrgentMessages();
      } catch (error) {
        logger.error('Urgent message check failed:', error);
      }
    }, {
      scheduled: true,
      timezone: 'Asia/Shanghai'
    });

    this.scheduledTasks.set('urgent', task);
    logger.info('Scheduled urgent message check task (every 30 seconds)');
  }

  async checkAndSendUrgentMessages() {
    const urgentMessages = await Message.find({
      isRead: false,
      isArchived: false,
      category: 'alert',
      priority: { $in: ['high', 'urgent'] },
      urgentNotified: { $ne: true }
    }).sort({ createdAt: -1 }).limit(50).lean();

    if (urgentMessages.length === 0) {
      return;
    }

    const userPref = await UserPreference.getByUserId('default');

    for (const message of urgentMessages) {
      const now = Date.now();
      const cooldownKey = `urgent:${message.messageId}`;
      
      if (this.urgentNotificationCooldown.has(cooldownKey)) {
        const lastSent = this.urgentNotificationCooldown.get(cooldownKey);
        if (now - lastSent < this.cooldownPeriod) {
          continue;
        }
      }

      try {
        await this.sendUrgentNotification(userPref, message);
        await Message.updateOne(
          { messageId: message.messageId },
          { $set: { urgentNotified: true, urgentNotifiedAt: new Date() } }
        );
        this.urgentNotificationCooldown.set(cooldownKey, now);
        
        logger.info(`Urgent notification sent for message: ${message.messageId}`);
      } catch (error) {
        logger.error(`Failed to send urgent notification for ${message.messageId}:`, error);
      }
    }
  }

  async sendUrgentNotification(userPref, message) {
    const priorityEmoji = message.priority === 'urgent' ? '🔴' : '🟠';
    const priorityText = message.priority === 'urgent' ? '紧急告警' : '重要告警';

    const content = `${priorityEmoji} **${priorityText} (${new Date().toLocaleString('zh-CN')}**\n\n` +
      `**标题:** ${message.title}\n` +
      `**优先级:** ${message.priority.toUpperCase()}\n` +
      `**内容:** ${(message.summary || message.content).substring(0, 200)}\n\n` +
      `请立即处理此告警！`;

    const sendResults = await this.sendNotifications(userPref, content, 1, true);

    const log = new AggregationLog({
      userId: userPref.userId,
      type: 'alert',
      title: `${priorityText}: ${message.title.substring(0, 50)}`,
      content,
      messageCount: 1,
      categories: [{ category: 'alert', count: 1 }],
      channels: message.channels.map(c => c.channel),
      status: sendResults.success ? 'sent' : 'failed',
      error: sendResults.error,
      metadata: {
        urgent: true,
        messageId: message.messageId,
        priority: message.priority
      }
    });

    await log.save();

    return sendResults;
  }

  async processNewMessage(message) {
    if (message.category === 'alert' && 
        (message.priority === 'urgent' || message.priority === 'high')) {
      
      const cooldownKey = `urgent:${message.messageId}`;
      const now = Date.now();
      
      if (!this.urgentNotificationCooldown.has(cooldownKey) ||
          now - this.urgentNotificationCooldown.get(cooldownKey) >= this.cooldownPeriod) {
        
        const userPref = await UserPreference.getByUserId('default');
        
        try {
          await this.sendUrgentNotification(userPref, message);
          message.urgentNotified = true;
          message.urgentNotifiedAt = new Date();
          await message.save();
          
          this.urgentNotificationCooldown.set(cooldownKey, now);
          logger.info(`Urgent notification sent immediately for message: ${message.messageId}`);
        } catch (error) {
          logger.error(`Failed to send immediate urgent notification:`, error);
        }
      }
    }
  }

  async runAggregation(type = 'default') {
    try {
      const preferences = await UserPreference.find({ aggregationEnabled: true });

      for (const pref of preferences) {
        await this.sendUserAggregation(pref, type);
      }

      logger.info(`Aggregation completed for ${preferences.length} users`);
    } catch (error) {
      logger.error('Aggregation task failed:', error);
    }
  }

  async sendUserAggregation(userPref, type) {
    try {
      const filters = {
        isRead: false,
        isArchived: false,
        urgentNotified: { $ne: true }
      };

      if (userPref.aggregationCategories && userPref.aggregationCategories.length > 0) {
        filters.category = { $in: userPref.aggregationCategories };
      }

      const messages = await Message.find(filters)
        .sort({ priority: -1, createdAt: -1 })
        .limit(50)
        .lean();

      if (messages.length === 0) {
        logger.debug(`No unread messages for user ${userPref.userId}`);
        return;
      }

      const categoryCount = this.countByCategory(messages);
      const channelCount = this.countByChannel(messages);

      const content = this.buildAggregationContent(messages, categoryCount, channelCount);

      const log = new AggregationLog({
        userId: userPref.userId,
        type: 'digest',
        title: `您有 ${messages.length} 条未读消息`,
        content,
        messageCount: messages.length,
        categories: Object.entries(categoryCount).map(([category, count]) => ({ category, count })),
        channels: Object.keys(channelCount),
        status: 'pending'
      });

      await log.save();

      const sendResults = await this.sendNotifications(userPref, content, messages.length);

      log.status = sendResults.success ? 'sent' : 'failed';
      log.error = sendResults.error;
      await log.save();

      logger.info(`Aggregation sent to user ${userPref.userId}: ${messages.length} messages`);

      return { success: true, messageCount: messages.length };
    } catch (error) {
      logger.error(`Failed to send aggregation for user ${userPref.userId}:`, error);
      return { success: false, error: error.message };
    }
  }

  countByCategory(messages) {
    const counts = {
      notification: 0,
      approval: 0,
      alert: 0,
      other: 0
    };

    for (const msg of messages) {
      counts[msg.category] = (counts[msg.category] || 0) + 1;
    }

    return counts;
  }

  countByChannel(messages) {
    const counts = {};

    for (const msg of messages) {
      for (const channel of msg.channels) {
        counts[channel.channel] = (counts[channel.channel] || 0) + 1;
      }
    }

    return counts;
  }

  buildAggregationContent(messages, categoryCount, channelCount) {
    const urgentMessages = messages.filter(m => m.priority === 'urgent' || m.priority === 'high');
    const recentMessages = messages.slice(0, 10);

    let content = `📊 **消息汇总 (${new Date().toLocaleString('zh-CN')}**\n\n`;

    content += `**总计: ${messages.length} 条未读消息**\n\n`;

    content += '📁 **按分类统计:**\n';
    if (categoryCount.alert > 0) content += `  🔴 告警: ${categoryCount.alert} 条\n`;
    if (categoryCount.approval > 0) content += `  🟡 审批: ${categoryCount.approval} 条\n`;
    if (categoryCount.notification > 0) content += `  🔵 通知: ${categoryCount.notification} 条\n`;
    if (categoryCount.other > 0) content += `  ⚪ 其他: ${categoryCount.other} 条\n`;

    content += '\n📱 **按渠道统计:**\n';
    for (const [channel, count] of Object.entries(channelCount)) {
      const channelNames = {
        email: '📧 邮件',
        dingtalk: '💬 钉钉',
        wework: '🏢 企业微信',
        slack: '🎯 Slack'
      };
      content += `  ${channelNames[channel] || channel}: ${count} 条\n`;
    }

    if (urgentMessages.length > 0) {
      content += `\n⚠️ **重要消息 (${urgentMessages.length} 条):**\n`;
      for (const msg of urgentMessages.slice(0, 5)) {
        const priorityIcon = msg.priority === 'urgent' ? '🔴' : '🟠';
        content += `  ${priorityIcon} [${msg.priority.toUpperCase()}] ${msg.title.substring(0, 50)}...\n`;
      }
    }

    content += `\n📝 **最新消息:**\n`;
    for (const msg of recentMessages) {
      const time = new Date(msg.createdAt).toLocaleString('zh-CN');
      content += `  • ${time} - ${msg.title.substring(0, 30)}...\n`;
    }

    return content;
  }

  async sendNotifications(userPref, content, messageCount, isUrgent = false) {
    const results = [];
    const notificationConfig = userPref.notificationConfig || {};

    if (isUrgent) {
      if (notificationConfig.dingtalk?.enabled && notificationConfig.dingtalk.webhook) {
        try {
          await this.sendUrgentToDingTalk(notificationConfig.dingtalk.webhook, content, messageCount);
          results.push({ channel: 'dingtalk', success: true });
        } catch (error) {
          results.push({ channel: 'dingtalk', success: false, error: error.message });
        }
      }

      if (notificationConfig.wework?.enabled && notificationConfig.wework.webhook) {
        try {
          await this.sendUrgentToWeWork(notificationConfig.wework.webhook, content, messageCount);
          results.push({ channel: 'wework', success: true });
        } catch (error) {
          results.push({ channel: 'wework', success: false, error: error.message });
        }
      }

      if (notificationConfig.slack?.enabled && notificationConfig.slack.webhook) {
        try {
          await this.sendToSlack(notificationConfig.slack.webhook, content, messageCount);
          results.push({ channel: 'slack', success: true });
        } catch (error) {
          results.push({ channel: 'slack', success: false, error: error.message });
        }
      }

      if (notificationConfig.email?.enabled && notificationConfig.email.address) {
        try {
          await this.sendToEmail(notificationConfig.email.address, content, messageCount);
          results.push({ channel: 'email', success: true });
        } catch (error) {
          results.push({ channel: 'email', success: false, error: error.message });
        }
      }
    } else {
      if (notificationConfig.dingtalk?.enabled && notificationConfig.dingtalk.webhook) {
        try {
          await this.sendToDingTalk(notificationConfig.dingtalk.webhook, content, messageCount);
          results.push({ channel: 'dingtalk', success: true });
        } catch (error) {
          results.push({ channel: 'dingtalk', success: false, error: error.message });
        }
      }

      if (notificationConfig.wework?.enabled && notificationConfig.wework.webhook) {
        try {
          await this.sendToWeWork(notificationConfig.wework.webhook, content, messageCount);
          results.push({ channel: 'wework', success: true });
        } catch (error) {
          results.push({ channel: 'wework', success: false, error: error.message });
        }
      }

      if (notificationConfig.slack?.enabled && notificationConfig.slack.webhook) {
        try {
          await this.sendToSlack(notificationConfig.slack.webhook, content, messageCount);
          results.push({ channel: 'slack', success: true });
        } catch (error) {
          results.push({ channel: 'slack', success: false, error: error.message });
        }
      }

      if (notificationConfig.email?.enabled && notificationConfig.email.address) {
        try {
          await this.sendToEmail(notificationConfig.email.address, content, messageCount);
          results.push({ channel: 'email', success: true });
        } catch (error) {
          results.push({ channel: 'email', success: false, error: error.message });
        }
      }
    }

    const successCount = results.filter(r => r.success).length;
    return {
      success: successCount > 0,
      results,
      error: successCount === 0 ? 'All notifications failed' : null
    };
  }

  async sendToDingTalk(webhook, content, messageCount) {
    const response = await axios.post(webhook, {
      msgtype: 'markdown',
      markdown: {
        title: `消息汇总 - ${messageCount} 条未读`,
        text: content
      }
    });

    if (response.data.errcode !== 0) {
      throw new Error(`DingTalk webhook failed: ${response.data.errmsg}`);
    }

    return true;
  }

  async sendUrgentToDingTalk(webhook, content, messageCount) {
    const response = await axios.post(webhook, {
      msgtype: 'markdown',
      markdown: {
        title: '紧急告警通知',
        text: content
      },
      at: {
        isAtAll: true
      }
    });

    if (response.data.errcode !== 0) {
      throw new Error(`DingTalk webhook failed: ${response.data.errmsg}`);
    }

    return true;
  }

  async sendToWeWork(webhook, content, messageCount) {
    const response = await axios.post(webhook, {
      msgtype: 'markdown',
      markdown: {
        content: content
      }
    });

    if (response.data.errcode !== 0) {
      throw new Error(`WeWork webhook failed: ${response.data.errmsg}`);
    }

    return true;
  }

  async sendUrgentToWeWork(webhook, content, messageCount) {
    const response = await axios.post(webhook, {
      msgtype: 'markdown',
      markdown: {
        content: `<font color=\"warning\">${content}</font>`
      }
    });

    if (response.data.errcode !== 0) {
      throw new Error(`WeWork webhook failed: ${response.data.errmsg}`);
    }

    return true;
  }

  async sendToSlack(webhook, content, messageCount) {
    const response = await axios.post(webhook, {
      text: content
    });

    if (response.data !== 'ok') {
      throw new Error(`Slack webhook failed`);
    }

    return true;
  }

  async sendToEmail(address, content, messageCount) {
    logger.info(`Would send email to ${address} with ${messageCount} messages summary`);
    return true;
  }

  async sendAlertAggregation(userId) {
    const alertMessages = await Message.find({
      userId,
      isRead: false,
      isArchived: false,
      category: 'alert',
      priority: { $in: ['high', 'urgent'] }
    }).sort({ createdAt: -1 }).limit(20).lean();

    if (alertMessages.length === 0) {
      return { success: true, message: 'No alert messages' };
    }

    const userPref = await UserPreference.getByUserId(userId);

    const content = `🚨 **告警汇总 (${new Date().toLocaleString('zh-CN')}**\n\n` +
      `您有 ${alertMessages.length} 条告警消息\n\n` +
      alertMessages.map(msg => {
        const priorityIcon = msg.priority === 'urgent' ? '🔴' : '🟠';
        return `${priorityIcon} [${msg.priority.toUpperCase()}] ${msg.title}\n  ${msg.summary || msg.content.substring(0, 100)}\n`;
      }).join('\n');

    await this.sendNotifications(userPref, content, alertMessages.length, true);

    return { success: true, alertCount: alertMessages.length };
  }

  stop() {
    for (const [name, task] of this.scheduledTasks) {
      task.stop();
      logger.info(`Stopped task: ${name}`);
    }
    this.scheduledTasks.clear();
    this.urgentNotificationCooldown.clear();
    logger.info('Aggregation service stopped');
  }

  async getAggregationLogs(userId, options = {}) {
    const query = userId ? { userId } : {};
    const sort = options.sort || { sentAt: -1 };
    const page = options.page || 1;
    const pageSize = options.pageSize || 20;
    const skip = (page - 1) * pageSize;

    const [logs, total] = await Promise.all([
      AggregationLog.find(query)
        .sort(sort)
        .skip(skip)
        .limit(pageSize)
        .lean(),
      AggregationLog.countDocuments(query)
    ]);

    return {
      logs,
      pagination: {
        page,
        pageSize,
        total,
        totalPages: Math.ceil(total / pageSize)
      }
    };
  }

  getUrgentStats() {
    return {
      cooldownSize: this.urgentNotificationCooldown.size,
      cooldownPeriod: this.cooldownPeriod
    };
  }
}

module.exports = new AggregationService();
module.exports.AggregationService = AggregationService;
