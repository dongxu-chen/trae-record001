require('dotenv').config();

const { connect: connectMongo } = require('../src/db/mongoose');
const Channel = require('../src/models/Channel');
const config = require('../src/config');
const logger = require('../src/utils/logger');

const defaultChannels = [
  {
    type: 'email',
    name: '邮件',
    isEnabled: true,
    config: {
      host: config.email.imap.host,
      port: config.email.imap.port,
      tls: config.email.imap.tls,
      user: config.email.imap.user,
      password: config.email.imap.password
    },
    syncInterval: 60000
  },
  {
    type: 'dingtalk',
    name: '钉钉',
    isEnabled: true,
    config: {
      appKey: config.dingtalk.appKey,
      appSecret: config.dingtalk.appSecret,
      userId: config.dingtalk.userId
    },
    syncInterval: 60000
  },
  {
    type: 'wework',
    name: '企业微信',
    isEnabled: true,
    config: {
      corpId: config.wework.corpId,
      agentId: config.wework.agentId,
      secret: config.wework.secret,
      userId: config.wework.userId
    },
    syncInterval: 60000
  },
  {
    type: 'slack',
    name: 'Slack',
    isEnabled: true,
    config: {
      botToken: config.slack.botToken,
      userId: config.slack.userId
    },
    syncInterval: 60000
  }
];

const initChannels = async () => {
  try {
    await connectMongo();
    logger.info('Initializing default channels...');

    for (const channelConfig of defaultChannels) {
      const existing = await Channel.findOne({ type: channelConfig.type });

      if (existing) {
        logger.info(`Channel ${channelConfig.type} already exists, updating...`);
        Object.assign(existing, channelConfig);
        await existing.save();
      } else {
        logger.info(`Creating channel ${channelConfig.type}...`);
        const channel = new Channel(channelConfig);
        await channel.save();
      }
    }

    logger.info('Channels initialized successfully');
    process.exit(0);
  } catch (error) {
    logger.error('Failed to initialize channels:', error);
    process.exit(1);
  }
};

initChannels();
