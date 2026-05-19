const Joi = require('joi');
const messageService = require('../services/MessageService');
const logger = require('../utils/logger');

const getMessagesSchema = Joi.object({
  page: Joi.number().integer().min(1).default(1),
  pageSize: Joi.number().integer().min(1).max(100).default(20),
  category: Joi.string().valid('notification', 'approval', 'alert', 'other'),
  channel: Joi.string().valid('email', 'dingtalk', 'wework', 'slack'),
  isRead: Joi.boolean(),
  priority: Joi.string().valid('low', 'medium', 'high', 'urgent'),
  sortBy: Joi.string().valid('createdAt', 'priority').default('createdAt'),
  sortOrder: Joi.string().valid('asc', 'desc').default('desc')
});

const markReadSchema = Joi.object({
  messageId: Joi.string().required(),
  channel: Joi.string().valid('email', 'dingtalk', 'wework', 'slack')
});

const markAllReadSchema = Joi.object({
  category: Joi.string().valid('notification', 'approval', 'alert', 'other'),
  channel: Joi.string().valid('email', 'dingtalk', 'wework', 'slack'),
  priority: Joi.string().valid('low', 'medium', 'high', 'urgent')
});

const fetchSchema = Joi.object({
  channel: Joi.string().valid('email', 'dingtalk', 'wework', 'slack'),
  since: Joi.string().isoDate()
});

exports.getMessages = async (req, res) => {
  try {
    const { error, value } = getMessagesSchema.validate(req.query);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const filters = {};
    if (value.category) filters.category = value.category;
    if (value.isRead !== undefined) filters.isRead = value.isRead;
    if (value.priority) filters.priority = value.priority;
    if (value.channel) {
      filters['channels.channel'] = value.channel;
    }

    const sort = {};
    sort[value.sortBy] = value.sortOrder === 'desc' ? -1 : 1;

    const result = await messageService.getMessages(filters, {
      page: value.page,
      pageSize: value.pageSize,
      sort
    });

    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    logger.error('Get messages error:', error);
    res.status(500).json({ error: 'Failed to get messages' });
  }
};

exports.getMessage = async (req, res) => {
  try {
    const { messageId } = req.params;

    const message = await messageService.getMessageById(messageId);

    if (!message) {
      return res.status(404).json({ error: 'Message not found' });
    }

    res.json({
      success: true,
      data: message
    });
  } catch (error) {
    logger.error('Get message error:', error);
    res.status(500).json({ error: 'Failed to get message' });
  }
};

exports.markAsRead = async (req, res) => {
  try {
    const { error, value } = markReadSchema.validate({ ...req.params, ...req.body });
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const message = await messageService.markAsRead(value.messageId, value.channel);

    res.json({
      success: true,
      data: message
    });
  } catch (error) {
    logger.error('Mark as read error:', error);
    res.status(500).json({ error: 'Failed to mark as read' });
  }
};

exports.markAsUnread = async (req, res) => {
  try {
    const { error, value } = markReadSchema.validate({ ...req.params, ...req.body });
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const message = await messageService.markAsUnread(value.messageId, value.channel);

    res.json({
      success: true,
      data: message
    });
  } catch (error) {
    logger.error('Mark as unread error:', error);
    res.status(500).json({ error: 'Failed to mark as unread' });
  }
};

exports.markAllAsRead = async (req, res) => {
  try {
    const { error, value } = markAllReadSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const filters = {};
    if (value.category) filters.category = value.category;
    if (value.channel) filters['channels.channel'] = value.channel;
    if (value.priority) filters.priority = value.priority;

    const result = await messageService.markAllAsRead(filters);

    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    logger.error('Mark all as read error:', error);
    res.status(500).json({ error: 'Failed to mark all as read' });
  }
};

exports.archiveMessage = async (req, res) => {
  try {
    const { messageId } = req.params;

    const message = await messageService.archiveMessage(messageId);

    res.json({
      success: true,
      data: message
    });
  } catch (error) {
    logger.error('Archive message error:', error);
    res.status(500).json({ error: 'Failed to archive message' });
  }
};

exports.deleteMessage = async (req, res) => {
  try {
    const { messageId } = req.params;

    await messageService.deleteMessage(messageId);

    res.json({
      success: true,
      message: 'Message deleted successfully'
    });
  } catch (error) {
    logger.error('Delete message error:', error);
    res.status(500).json({ error: 'Failed to delete message' });
  }
};

exports.getUnreadCount = async (req, res) => {
  try {
    const filters = {};
    if (req.query.category) filters.category = req.query.category;
    if (req.query.channel) filters['channels.channel'] = req.query.channel;

    const count = await messageService.getUnreadCount(filters);

    res.json({
      success: true,
      data: { count }
    });
  } catch (error) {
    logger.error('Get unread count error:', error);
    res.status(500).json({ error: 'Failed to get unread count' });
  }
};

exports.getStats = async (req, res) => {
  try {
    const stats = await messageService.getStats();

    res.json({
      success: true,
      data: stats
    });
  } catch (error) {
    logger.error('Get stats error:', error);
    res.status(500).json({ error: 'Failed to get stats' });
  }
};

exports.fetchMessages = async (req, res) => {
  try {
    const { error, value } = fetchSchema.validate(req.query);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    let result;
    if (value.channel) {
      result = await messageService.fetchFromChannel(value.channel, value.since);
    } else {
      result = await messageService.fetchFromAllChannels(value.since);
    }

    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    logger.error('Fetch messages error:', error);
    res.status(500).json({ error: 'Failed to fetch messages' });
  }
};
