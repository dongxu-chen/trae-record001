const Joi = require('joi');
const Channel = require('../models/Channel');
const adapterFactory = require('../adapters/AdapterFactory');
const logger = require('../utils/logger');

const createChannelSchema = Joi.object({
  type: Joi.string().valid('email', 'dingtalk', 'wework', 'slack').required(),
  name: Joi.string().required(),
  isEnabled: Joi.boolean().default(true),
  config: Joi.object().required(),
  syncInterval: Joi.number().default(60000)
});

const updateChannelSchema = Joi.object({
  name: Joi.string(),
  isEnabled: Joi.boolean(),
  config: Joi.object(),
  syncInterval: Joi.number()
});

exports.getChannels = async (req, res) => {
  try {
    const channels = await Channel.find().sort({ createdAt: -1 }).lean();

    const channelsWithStatus = channels.map(channel => ({
      ...channel,
      adapterStatus: adapterFactory.getAdapter(channel._id)?.isConnected() ? 'connected' : 'disconnected'
    }));

    res.json({
      success: true,
      data: channelsWithStatus
    });
  } catch (error) {
    logger.error('Get channels error:', error);
    res.status(500).json({ error: 'Failed to get channels' });
  }
};

exports.getChannel = async (req, res) => {
  try {
    const { id } = req.params;

    const channel = await Channel.findById(id).lean();

    if (!channel) {
      return res.status(404).json({ error: 'Channel not found' });
    }

    res.json({
      success: true,
      data: channel
    });
  } catch (error) {
    logger.error('Get channel error:', error);
    res.status(500).json({ error: 'Failed to get channel' });
  }
};

exports.createChannel = async (req, res) => {
  try {
    const { error, value } = createChannelSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const existingChannel = await Channel.findOne({ type: value.type });
    if (existingChannel) {
      return res.status(400).json({ error: 'Channel with this type already exists' });
    }

    const channel = new Channel(value);
    await channel.save();

    try {
      const adapter = adapterFactory.createAdapter(channel);
      await adapter.connect();
    } catch (adapterError) {
      logger.warn(`Failed to connect adapter for ${value.type}:`, adapterError);
    }

    res.status(201).json({
      success: true,
      data: channel
    });
  } catch (error) {
    logger.error('Create channel error:', error);
    res.status(500).json({ error: 'Failed to create channel' });
  }
};

exports.updateChannel = async (req, res) => {
  try {
    const { id } = req.params;
    const { error, value } = updateChannelSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const channel = await Channel.findById(id);
    if (!channel) {
      return res.status(404).json({ error: 'Channel not found' });
    }

    Object.assign(channel, value);
    await channel.save();

    if (value.config || value.isEnabled !== undefined) {
      adapterFactory.removeAdapter(id);
      if (channel.isEnabled) {
        try {
          const adapter = adapterFactory.createAdapter(channel);
          await adapter.connect();
        } catch (adapterError) {
          logger.warn(`Failed to reconnect adapter for ${channel.type}:`, adapterError);
        }
      }
    }

    res.json({
      success: true,
      data: channel
    });
  } catch (error) {
    logger.error('Update channel error:', error);
    res.status(500).json({ error: 'Failed to update channel' });
  }
};

exports.deleteChannel = async (req, res) => {
  try {
    const { id } = req.params;

    const channel = await Channel.findById(id);
    if (!channel) {
      return res.status(404).json({ error: 'Channel not found' });
    }

    adapterFactory.removeAdapter(id);
    await Channel.findByIdAndDelete(id);

    res.json({
      success: true,
      message: 'Channel deleted successfully'
    });
  } catch (error) {
    logger.error('Delete channel error:', error);
    res.status(500).json({ error: 'Failed to delete channel' });
  }
};

exports.testChannel = async (req, res) => {
  try {
    const { id } = req.params;

    const channel = await Channel.findById(id);
    if (!channel) {
      return res.status(404).json({ error: 'Channel not found' });
    }

    let adapter = adapterFactory.getAdapter(id);
    if (!adapter) {
      adapter = adapterFactory.createAdapter(channel);
    }

    const connected = await adapter.connect();

    res.json({
      success: true,
      data: {
        connected,
        channelType: channel.type
      }
    });
  } catch (error) {
    logger.error('Test channel error:', error);
    res.status(500).json({ error: 'Failed to test channel', details: error.message });
  }
};

exports.syncChannel = async (req, res) => {
  try {
    const { id } = req.params;

    const channel = await Channel.findById(id);
    if (!channel) {
      return res.status(404).json({ error: 'Channel not found' });
    }

    const messageService = require('../services/MessageService');
    const result = await messageService.fetchFromChannel(channel.type);

    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    logger.error('Sync channel error:', error);
    res.status(500).json({ error: 'Failed to sync channel', details: error.message });
  }
};
