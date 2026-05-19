const axios = require('axios');
const BaseAdapter = require('./BaseAdapter');
const logger = require('../utils/logger');

class DingTalkAdapter extends BaseAdapter {
  constructor(channelConfig) {
    super(channelConfig);
    this.accessToken = null;
    this.tokenExpiresAt = null;
  }

  async connect() {
    try {
      await this.getAccessToken();
      this.isConnected = true;
      logger.info('DingTalk adapter connected successfully');
      return true;
    } catch (error) {
      logger.error('DingTalk adapter connection failed:', error);
      throw error;
    }
  }

  async disconnect() {
    this.isConnected = false;
    this.accessToken = null;
  }

  async getAccessToken() {
    if (this.accessToken && Date.now() < this.tokenExpiresAt) {
      return this.accessToken;
    }

    const response = await axios.get('https://oapi.dingtalk.com/gettoken', {
      params: {
        appkey: this.config.appKey,
        appsecret: this.config.appSecret
      }
    });

    if (response.data.errcode !== 0) {
      throw new Error(`Failed to get access token: ${response.data.errmsg}`);
    }

    this.accessToken = response.data.access_token;
    this.tokenExpiresAt = Date.now() + (response.data.expires_in - 300) * 1000;
    return this.accessToken;
  }

  async fetchMessages(since = null) {
    if (!this.isConnected) {
      await this.connect();
    }

    try {
      const accessToken = await this.getAccessToken();

      const response = await axios.post(
        'https://oapi.dingtalk.com/topapi/message/list',
        {
          userid: this.config.userId,
          start_time: since ? new Date(since).getTime() : 0,
          end_time: Date.now(),
          cursor: 0,
          size: 50
        },
        {
          params: { access_token: accessToken }
        }
      );

      if (response.data.errcode !== 0) {
        throw new Error(`Failed to fetch messages: ${response.data.errmsg}`);
      }

      const messages = response.data.result?.list || [];
      return messages.map(msg => this.normalizeMessage(msg));
    } catch (error) {
      logger.error('DingTalk fetch messages failed:', error);
      throw error;
    }
  }

  async markAsRead(messageIds) {
    if (!this.isConnected) {
      await this.connect();
    }

    try {
      const accessToken = await this.getAccessToken();

      const response = await axios.post(
        'https://oapi.dingtalk.com/topapi/message/mark_read',
        {
          userid: this.config.userId,
          message_ids: messageIds
        },
        {
          params: { access_token: accessToken }
        }
      );

      if (response.data.errcode !== 0) {
        throw new Error(`Failed to mark as read: ${response.data.errmsg}`);
      }

      return true;
    } catch (error) {
      logger.error('DingTalk mark as read failed:', error);
      throw error;
    }
  }

  async markAsUnread(messageIds) {
    return true;
  }

  normalizeMessage(rawMessage) {
    const messageId = rawMessage.msg_id || rawMessage.messageId;
    const title = rawMessage.title || rawMessage.subject || '(无主题)';
    const content = rawMessage.text || rawMessage.content || rawMessage.message || '';

    return {
      channel: 'dingtalk',
      channelMessageId: messageId,
      title,
      content,
      summary: content.substring(0, 200),
      sender: {
        name: rawMessage.sender_name || rawMessage.from,
        avatar: rawMessage.sender_avatar
      },
      recipients: rawMessage.recipients || [],
      attachments: rawMessage.attachments || [],
      receivedAt: new Date(rawMessage.create_time || rawMessage.timestamp || Date.now()),
      dedupKey: this.generateDedupKey({ title, content }),
      raw: rawMessage
    };
  }
}

module.exports = DingTalkAdapter;
