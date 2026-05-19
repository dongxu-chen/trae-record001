const Joi = require('joi');
const aggregationService = require('../services/AggregationService');
const UserPreference = require('../models/UserPreference');
const logger = require('../utils/logger');

const sendAggregationSchema = Joi.object({
  userId: Joi.string().default('default'),
  type: Joi.string().valid('digest', 'alert').default('digest')
});

const getLogsSchema = Joi.object({
  userId: Joi.string(),
  page: Joi.number().integer().min(1).default(1),
  pageSize: Joi.number().integer().min(1).max(100).default(20)
});

exports.triggerAggregation = async (req, res) => {
  try {
    const { error, value } = sendAggregationSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const userPref = await UserPreference.getByUserId(value.userId);

    let result;
    if (value.type === 'alert') {
      result = await aggregationService.sendAlertAggregation(value.userId);
    } else {
      result = await aggregationService.sendUserAggregation(userPref, value.type);
    }

    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    logger.error('Trigger aggregation error:', error);
    res.status(500).json({ error: 'Failed to trigger aggregation' });
  }
};

exports.runAggregation = async (req, res) => {
  try {
    await aggregationService.runAggregation('manual');

    res.json({
      success: true,
      message: 'Aggregation task triggered for all users'
    });
  } catch (error) {
    logger.error('Run aggregation error:', error);
    res.status(500).json({ error: 'Failed to run aggregation' });
  }
};

exports.getLogs = async (req, res) => {
  try {
    const { error, value } = getLogsSchema.validate(req.query);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const result = await aggregationService.getAggregationLogs(value.userId, {
      page: value.page,
      pageSize: value.pageSize
    });

    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    logger.error('Get aggregation logs error:', error);
    res.status(500).json({ error: 'Failed to get aggregation logs' });
  }
};

exports.getStatus = async (req, res) => {
  try {
    const tasks = aggregationService.scheduledTasks || new Map();
    const taskStatus = [];

    for (const [name, task] of tasks.entries()) {
      taskStatus.push({
        name,
        running: task.running || false
      });
    }

    const urgentStats = aggregationService.getUrgentStats ? aggregationService.getUrgentStats() : {};

    res.json({
      success: true,
      data: {
        enabled: require('../config').aggregation.enabled,
        tasks: taskStatus,
        urgent: urgentStats
      }
    });
  } catch (error) {
    logger.error('Get aggregation status error:', error);
    res.status(500).json({ error: 'Failed to get aggregation status' });
  }
};

exports.checkUrgent = async (req, res) => {
  try {
    await aggregationService.checkAndSendUrgentMessages();
    
    res.json({
      success: true,
      message: 'Urgent message check completed'
    });
  } catch (error) {
    logger.error('Check urgent messages error:', error);
    res.status(500).json({ error: 'Failed to check urgent messages' });
  }
};
