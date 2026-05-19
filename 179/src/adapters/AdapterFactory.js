const EmailAdapter = require('./EmailAdapter');
const DingTalkAdapter = require('./DingTalkAdapter');
const WeWorkAdapter = require('./WeWorkAdapter');
const SlackAdapter = require('./SlackAdapter');
const logger = require('../utils/logger');

const adapterMap = {
  email: EmailAdapter,
  dingtalk: DingTalkAdapter,
  wework: WeWorkAdapter,
  slack: SlackAdapter
};

class AdapterFactory {
  constructor() {
    this.adapters = new Map();
  }

  createAdapter(channelConfig) {
    const AdapterClass = adapterMap[channelConfig.type];
    if (!AdapterClass) {
      throw new Error(`No adapter found for channel type: ${channelConfig.type}`);
    }

    const adapter = new AdapterClass(channelConfig);
    this.adapters.set(channelConfig._id.toString(), adapter);
    return adapter;
  }

  getAdapter(channelId) {
    return this.adapters.get(channelId.toString());
  }

  getAdapterByType(channelType) {
    for (const adapter of this.adapters.values()) {
      if (adapter.getChannelType() === channelType) {
        return adapter;
      }
    }
    return null;
  }

  async createAdapters(channelConfigs) {
    const adapters = [];
    for (const config of channelConfigs) {
      try {
        const adapter = this.createAdapter(config);
        adapters.push(adapter);
      } catch (error) {
        logger.error(`Failed to create adapter for ${config.type}:`, error);
      }
    }
    return adapters;
  }

  async connectAll() {
    const results = [];
    for (const adapter of this.adapters.values()) {
      try {
        const success = await adapter.connect();
        results.push({ adapter, success });
      } catch (error) {
        logger.error(`Failed to connect adapter ${adapter.getChannelType()}:`, error);
        results.push({ adapter, success: false, error });
      }
    }
    return results;
  }

  async disconnectAll() {
    for (const adapter of this.adapters.values()) {
      try {
        await adapter.disconnect();
      } catch (error) {
        logger.error(`Failed to disconnect adapter ${adapter.getChannelType()}:`, error);
      }
    }
  }

  getAllAdapters() {
    return Array.from(this.adapters.values());
  }

  removeAdapter(channelId) {
    const adapter = this.adapters.get(channelId.toString());
    if (adapter) {
      adapter.disconnect();
      this.adapters.delete(channelId.toString());
    }
  }

  clear() {
    this.disconnectAll();
    this.adapters.clear();
  }
}

module.exports = new AdapterFactory();
module.exports.AdapterFactory = AdapterFactory;
