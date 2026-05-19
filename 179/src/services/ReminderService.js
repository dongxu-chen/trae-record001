const Message = require('../models/Message');
const logger = require('../utils/logger');

class ReminderService {
  constructor() {
    this.reminderPatterns = {
      approval: [
        { type: 'approval', keywords: ['请审批', '待审批', '审批', '审核', '请处理', '待处理', '需要您处理', '请您审批', '审批流程', '审批单'], priority: 'high' },
        { type: 'approval', keywords: ['请假', '休假', '加班', '报销', '采购', '合同', '付款', '费用申请', '出差'], priority: 'medium' }
      ],
      meeting: [
        { type: 'meeting', keywords: ['会议', '开会', '请参加', '邀请您参加', '日程安排', '日程提醒', '会议提醒', 'zoom', '腾讯会议'], priority: 'medium' }
      ],
      deadline: [
        { type: 'deadline', keywords: ['截止', '截止日期', 'deadline', '最后期限', '请于', '请在', '之前完成', '务必完成'], priority: 'high' }
      ],
      alert: [
        { type: 'alert', keywords: ['告警', '警报', 'error', '错误', '异常', '故障', '紧急', 'urgent', 'critical', '严重'], priority: 'urgent' }
      ],
      reply: [
        { type: 'reply', keywords: ['请回复', '请确认', '请答复', '请反馈', '期待您的回复', '盼复', '请您确认'], priority: 'medium' }
      ],
      todo: [
        { type: 'todo', keywords: ['待办', 'todo', '任务', '需要完成', '请完成', '需要您', '请您'], priority: 'low' }
      ]
    };

    this.reminderLevels = {
      urgent: { score: 100, pin: true, notify: true },
      high: { score: 75, pin: true, notify: true },
      medium: { score: 50, pin: false, notify: false },
      low: { score: 25, pin: false, notify: false }
    };
  }

  analyzeMessage(message) {
    const text = `${message.title || ''} ${message.content || ''}`.toLowerCase();
    const results = [];

    for (const [category, patterns] of Object.entries(this.reminderPatterns)) {
      for (const pattern of patterns) {
        const matchedKeywords = [];
        for (const keyword of pattern.keywords) {
          if (text.includes(keyword.toLowerCase())) {
            matchedKeywords.push(keyword);
          }
        }

        if (matchedKeywords.length > 0) {
          results.push({
            type: pattern.type,
            category,
            priority: pattern.priority,
            matchedKeywords,
            score: this.reminderLevels[pattern.priority].score * matchedKeywords.length
          });
        }
      }
    }

    if (results.length === 0) {
      return {
        isReminder: false,
        reminderType: null,
        reminderPriority: null,
        shouldPin: false,
        shouldNotify: false,
        score: 0,
        matchedKeywords: []
      };
    }

    results.sort((a, b) => b.score - a.score);
    const topResult = results[0];
    const level = this.reminderLevels[topResult.priority];

    return {
      isReminder: true,
      reminderType: topResult.type,
      reminderCategory: topResult.category,
      reminderPriority: topResult.priority,
      shouldPin: level.pin,
      shouldNotify: level.notify,
      score: topResult.score,
      matchedKeywords: topResult.matchedKeywords,
      allMatches: results
    };
  }

  async processMessage(message) {
    const analysis = this.analyzeMessage(message);

    if (analysis.isReminder) {
      message.reminder = {
        type: analysis.reminderType,
        category: analysis.reminderCategory,
        priority: analysis.reminderPriority,
        score: analysis.score,
        matchedKeywords: analysis.matchedKeywords,
        isPinned: analysis.shouldPin,
        pinnedAt: analysis.shouldPin ? new Date() : null
      };

      message.isPinned = analysis.shouldPin;
      message.pinnedAt = analysis.shouldPin ? new Date() : null;

      if (analysis.shouldNotify) {
        logger.info(`Reminder detected: ${analysis.reminderType} (${analysis.reminderPriority}) for message ${message.messageId}`);
      }
    }

    return analysis;
  }

  async getPinnedMessages(filters = {}) {
    const query = {
      isPinned: true,
      isArchived: false,
      ...filters
    };

    const messages = await Message.find(query)
      .sort({ 'reminder.score': -1, pinnedAt: -1, createdAt: -1 })
      .lean();

    return messages;
  }

  async getReminderMessages(filters = {}) {
    const query = {
      'reminder.isPinned': true,
      isRead: false,
      isArchived: false,
      ...filters
    };

    const messages = await Message.find(query)
      .sort({ 'reminder.score': -1, createdAt: -1 })
      .lean();

    const grouped = {
      urgent: [],
      high: [],
      medium: [],
      low: []
    };

    for (const msg of messages) {
      const priority = msg.reminder?.priority || 'low';
      if (grouped[priority]) {
        grouped[priority].push(msg);
      }
    }

    return {
      messages,
      grouped,
      counts: {
        total: messages.length,
        urgent: grouped.urgent.length,
        high: grouped.high.length,
        medium: grouped.medium.length,
        low: grouped.low.length
      }
    };
  }

  async pinMessage(messageId) {
    const message = await Message.findOne({ messageId });
    if (!message) {
      throw new Error('Message not found');
    }

    message.isPinned = true;
    message.pinnedAt = new Date();
    
    if (!message.reminder) {
      message.reminder = {
        type: 'manual',
        category: 'manual',
        priority: 'high',
        score: 80,
        isPinned: true,
        pinnedAt: new Date()
      };
    } else {
      message.reminder.isPinned = true;
      message.reminder.pinnedAt = new Date();
    }

    await message.save();
    return message;
  }

  async unpinMessage(messageId) {
    const message = await Message.findOne({ messageId });
    if (!message) {
      throw new Error('Message not found');
    }

    message.isPinned = false;
    message.pinnedAt = null;
    
    if (message.reminder) {
      message.reminder.isPinned = false;
      message.reminder.pinnedAt = null;
    }

    await message.save();
    return message;
  }

  async getReminderStats() {
    const [pinnedCount, reminderCount, unreadReminderCount] = await Promise.all([
      Message.countDocuments({ isPinned: true, isArchived: false }),
      Message.countDocuments({ 'reminder.isPinned': true, isArchived: false }),
      Message.countDocuments({ 'reminder.isPinned': true, isRead: false, isArchived: false })
    ]);

    const byType = await Message.aggregate([
      { $match: { 'reminder.isPinned': true, isArchived: false } },
      { $group: { _id: '$reminder.type', count: { $sum: 1 } } }
    ]);

    const byPriority = await Message.aggregate([
      { $match: { 'reminder.isPinned': true, isArchived: false } },
      { $group: { _id: '$reminder.priority', count: { $sum: 1 } } }
    ]);

    return {
      pinnedCount,
      reminderCount,
      unreadReminderCount,
      byType: Object.fromEntries(byType.map(item => [item._id, item.count])),
      byPriority: Object.fromEntries(byPriority.map(item => [item._id, item.count]))
    };
  }

  addReminderPattern(category, pattern) {
    if (!this.reminderPatterns[category]) {
      this.reminderPatterns[category] = [];
    }
    this.reminderPatterns[category].push(pattern);
    logger.info(`Added reminder pattern for ${category}: ${pattern.keywords.join(', ')}`);
  }

  removeReminderPattern(category, keywords) {
    if (!this.reminderPatterns[category]) return;
    
    this.reminderPatterns[category] = this.reminderPatterns[category].filter(
      p => !p.keywords.some(k => keywords.includes(k))
    );
    logger.info(`Removed reminder pattern from ${category}: ${keywords.join(', ')}`);
  }

  getReminderPatterns() {
    return JSON.parse(JSON.stringify(this.reminderPatterns));
  }
}

module.exports = new ReminderService();
module.exports.ReminderService = ReminderService;
