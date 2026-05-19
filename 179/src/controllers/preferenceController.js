const Joi = require('joi');
const UserPreference = require('../models/UserPreference');
const logger = require('../utils/logger');

const updatePreferenceSchema = Joi.object({
  aggregationEnabled: Joi.boolean(),
  aggregationCron: Joi.string(),
  aggregationChannels: Joi.array().items(Joi.string().valid('email', 'dingtalk', 'wework', 'slack')),
  aggregationCategories: Joi.array().items(Joi.string().valid('notification', 'approval', 'alert', 'other')),
  pushEnabled: Joi.boolean(),
  soundEnabled: Joi.boolean(),
  quietHours: Joi.object({
    enabled: Joi.boolean(),
    start: Joi.string(),
    end: Joi.string()
  }),
  categorySettings: Joi.object(),
  notificationConfig: Joi.object({
    email: Joi.object({
      enabled: Joi.boolean(),
      address: Joi.string().email()
    }),
    dingtalk: Joi.object({
      enabled: Joi.boolean(),
      webhook: Joi.string().uri()
    }),
    wework: Joi.object({
      enabled: Joi.object({
        enabled: Joi.boolean(),
        webhook: Joi.string().uri()
      })
    }),
    slack: Joi.object({
      enabled: Joi.boolean(),
      webhook: Joi.string().uri()
    })
  }),
  autoArchiveDays: Joi.number().min(1).max(365),
  displaySettings: Joi.object({
    sortBy: Joi.string().valid('createdAt', 'priority'),
    pageSize: Joi.number().min(1).max(100)
  })
});

exports.getPreference = async (req, res) => {
  try {
    const userId = req.params.userId || 'default';

    const preference = await UserPreference.getByUserId(userId);

    res.json({
      success: true,
      data: preference
    });
  } catch (error) {
    logger.error('Get preference error:', error);
    res.status(500).json({ error: 'Failed to get preference' });
  }
};

exports.updatePreference = async (req, res) => {
  try {
    const userId = req.params.userId || 'default';
    const { error, value } = updatePreferenceSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    let preference = await UserPreference.findOne({ userId });
    if (!preference) {
      preference = new UserPreference({ userId, ...value });
    } else {
      Object.assign(preference, value);
    }

    await preference.save();

    res.json({
      success: true,
      data: preference
    });
  } catch (error) {
    logger.error('Update preference error:', error);
    res.status(500).json({ error: 'Failed to update preference' });
  }
};

exports.resetPreference = async (req, res) => {
  try {
    const userId = req.params.userId || 'default';

    await UserPreference.deleteOne({ userId });

    const defaultPref = await UserPreference.getByUserId(userId);

    res.json({
      success: true,
      data: defaultPref
    });
  } catch (error) {
    logger.error('Reset preference error:', error);
    res.status(500).json({ error: 'Failed to reset preference' });
  }
};
