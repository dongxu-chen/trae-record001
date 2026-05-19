const EventEmitter = require('events');

class BaseAdapter extends EventEmitter {
  constructor(channelConfig) {
    super();
    this.channelType = channelConfig.type;
    this.config = channelConfig.config || {};
    this.channelId = channelConfig._id;
    this.isConnected = false;
  }

  async connect() {
    throw new Error('connect() must be implemented by subclass');
  }

  async disconnect() {
    throw new Error('disconnect() must be implemented by subclass');
  }

  async fetchMessages(since = null) {
    throw new Error('fetchMessages() must be implemented by subclass');
  }

  async markAsRead(messageIds) {
    throw new Error('markAsRead() must be implemented by subclass');
  }

  async markAsUnread(messageIds) {
    throw new Error('markAsUnread() must be implemented by subclass');
  }

  normalizeMessage(rawMessage) {
    throw new Error('normalizeMessage() must be implemented by subclass');
  }

  generateDedupKey(message) {
    const content = `${message.title || ''}|${message.content || ''}`;
    const hash = require('crypto').createHash('sha256');
    hash.update(content.toLowerCase().trim());
    return hash.digest('hex').substring(0, 32);
  }

  isConnected() {
    return this.isConnected;
  }

  getChannelType() {
    return this.channelType;
  }
}

module.exports = BaseAdapter;
