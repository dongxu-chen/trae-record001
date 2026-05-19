const axios = require('axios');
const BaseAdapter = require('./BaseAdapter');
const logger = require('../utils/logger');

class SlackAdapter extends BaseAdapter {
  constructor(channelConfig) {
    super(channelConfig);
  }

  async connect() {
    try {
      await this.testConnection();
      this.isConnected = true;
      logger.info('Slack adapter connected successfully');
      return true;
    } catch (error) {
      logger.error('Slack adapter connection failed:', error);
      throw error;
    }
  }

  async disconnect() {
    this.isConnected = false;
  }

  async testConnection() {
    const response = await axios.get('https://slack.com/api/auth.test', {
      headers: {
        Authorization: `Bearer ${this.config.botToken}`
      }
    });

    if (!response.data.ok) {
      throw new Error(`Slack auth test failed: ${response.data.error}`);
    }

    return response.data;
  }

  async fetchMessages(since = null) {
    if (!this.isConnected) {
      await this.connect();
    }

    try {
      const messages = [];

      const conversationsResponse = await axios.get('https://slack.com/api/users.conversations', {
        headers: {
          Authorization: `Bearer ${this.config.botToken}`
        },
        params: {
          types: 'public_channel,private_channel,im',
          limit: 100
        }
      });

      if (!conversationsResponse.data.ok) {
        throw new Error(`Failed to get conversations: ${conversationsResponse.data.error}`);
      }

      const channels = conversationsResponse.data.channels || [];

      for (const channel of channels) {
        const historyResponse = await axios.get('https://slack.com/api/conversations.history', {
          headers: {
            Authorization: `Bearer ${this.config.botToken}`
          },
          params: {
            channel: channel.id,
            oldest: since ? new Date(since).getTime() / 1000 : 0,
            limit: 50
          }
        });

        if (historyResponse.data.ok) {
          const channelMessages = historyResponse.data.messages || [];
          for (const msg of channelMessages) {
            if (msg.user && msg.user !== 'USLACKBOT') {
              messages.push(this.normalizeMessage(msg, channel));
            }
          }
        }
      }

      return messages;
    } catch (error) {
      logger.error('Slack fetch messages failed:', error);
      throw error;
    }
  }

  async markAsRead(messageIds) {
    return true;
  }

  async markAsUnread(messageIds) {
    return true;
  }

  async getUserInfo(userId) {
    try {
      const response = await axios.get('https://slack.com/api/users.info', {
        headers: {
          Authorization: `Bearer ${this.config.botToken}`
        },
        params: { user: userId }
      });

      if (response.data.ok) {
        return response.data.user;
      }
    } catch (error) {
      logger.error('Failed to get Slack user info:', error);
    }
    return null;
  }

  normalizeMessage(rawMessage, channel) {
    const messageId = rawMessage.client_msg_id || rawMessage.ts;
    const title = channel.is_im ? '直接消息' : channel.name || 'Slack消息';
    const content = rawMessage.text || '';

    return {
      channel: 'slack',
      channelMessageId: messageId,
      title,
      content,
      summary: content.substring(0, 200),
      sender: {
        name: rawMessage.user,
        avatar: rawMessage.icons?.image_48
      },
      recipients: [],
      attachments: rawMessage.attachments?.map(att => ({
        name: att.title,
        url: att.title_link,
        type: 'attachment'
      })) || [],
      receivedAt: new Date(parseFloat(rawMessage.ts) * 1000),
      dedupKey: this.generateDedupKey({ title, content }),
      raw: rawMessage
    };
  }
}

module.exports = SlackAdapter;
