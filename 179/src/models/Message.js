const mongoose = require('mongoose');

const messageSchema = new mongoose.Schema({
  messageId: {
    type: String,
    required: true,
    unique: true
  },
  dedupKey: {
    type: String,
    required: true,
    index: true
  },
  simHash: {
    type: String,
    index: true
  },
  title: {
    type: String,
    required: true
  },
  content: {
    type: String,
    required: true
  },
  summary: {
    type: String
  },
  summaryInfo: {
    summary: String,
    method: {
      type: String,
      enum: ['textrank', 'external_ai', 'truncated', 'single_sentence', 'none']
    },
    length: Number,
    keySentences: [{
      text: String,
      score: String
    }],
    generatedAt: Date
  },
  category: {
    type: String,
    enum: ['notification', 'approval', 'alert', 'meeting', 'task', 'other'],
    default: 'notification',
    index: true
  },
  priority: {
    type: String,
    enum: ['low', 'medium', 'high', 'urgent'],
    default: 'medium'
  },
  isPinned: {
    type: Boolean,
    default: false,
    index: true
  },
  pinnedAt: {
    type: Date
  },
  reminder: {
    type: {
      type: String,
      enum: ['approval', 'meeting', 'deadline', 'alert', 'reply', 'todo', 'manual']
    },
    category: String,
    priority: {
      type: String,
      enum: ['urgent', 'high', 'medium', 'low']
    },
    score: Number,
    matchedKeywords: [String],
    isPinned: Boolean,
    pinnedAt: Date,
    analyzedAt: Date
  },
  template: {
    name: String,
    displayName: String,
    matched: Boolean,
    matchScore: Number,
    parsedAt: Date
  },
  structuredData: {
    type: mongoose.Schema.Types.Mixed,
    default: {}
  },
  card: {
    templateName: String,
    displayName: String,
    category: String,
    icon: String,
    color: String,
    priority: String,
    title: String,
    summary: String,
    fields: [{
      key: String,
      label: String,
      value: mongoose.Schema.Types.Mixed,
      highlight: Boolean
    }],
    actionButtons: [{
      action: String,
      label: String,
      style: String
    }],
    matchScore: Number,
    generatedAt: Date
  },
  channels: [{
    channel: {
      type: String,
      enum: ['email', 'dingtalk', 'wework', 'slack'],
      required: true
    },
    channelMessageId: {
      type: String,
      required: true
    },
    receivedAt: {
      type: Date,
      required: true
    },
    isRead: {
      type: Boolean,
      default: false
    },
    readAt: {
      type: Date
    },
    raw: {
      type: mongoose.Schema.Types.Mixed
    }
  }],
  sender: {
    name: String,
    email: String,
    avatar: String
  },
  recipients: [{
    type: String
  }],
  attachments: [{
    name: String,
    url: String,
    size: Number,
    type: String
  }],
  metadata: {
    type: mongoose.Schema.Types.Mixed,
    default: {}
  },
  isRead: {
    type: Boolean,
    default: false,
    index: true
  },
  readAt: {
    type: Date
  },
  isArchived: {
    type: Boolean,
    default: false,
    index: true
  },
  archivedAt: {
    type: Date
  },
  mergedFrom: [{
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Message'
  }],
  urgentNotified: {
    type: Boolean,
    default: false,
    index: true
  },
  urgentNotifiedAt: {
    type: Date
  }
}, {
  timestamps: true
});

messageSchema.index({ category: 1, isRead: 1, createdAt: -1 });
messageSchema.index({ 'channels.channel': 1, 'channels.isRead': 1 });

messageSchema.methods.markAsRead = async function(channel) {
  this.isRead = true;
  this.readAt = new Date();
  if (channel) {
    const channelInfo = this.channels.find(c => c.channel === channel);
    if (channelInfo) {
      channelInfo.isRead = true;
      channelInfo.readAt = new Date();
    }
  } else {
    this.channels.forEach(c => {
      c.isRead = true;
      c.readAt = c.readAt || new Date();
    });
  }
  return this.save();
};

messageSchema.methods.markAsUnread = async function(channel) {
  this.isRead = false;
  this.readAt = null;
  if (channel) {
    const channelInfo = this.channels.find(c => c.channel === channel);
    if (channelInfo) {
      channelInfo.isRead = false;
      channelInfo.readAt = null;
    }
  } else {
    this.channels.forEach(c => {
      c.isRead = false;
      c.readAt = null;
    });
  }
  return this.save();
};

messageSchema.statics.getUnreadCount = async function(filters = {}) {
  const query = { isRead: false, isArchived: false, ...filters };
  return this.countDocuments(query);
};

messageSchema.statics.getUnreadByCategory = async function() {
  return this.aggregate([
    { $match: { isRead: false, isArchived: false } },
    { $group: { _id: '$category', count: { $sum: 1 } } }
  ]);
};

messageSchema.statics.getPinnedMessages = async function(filters = {}) {
  const query = {
    isPinned: true,
    isArchived: false,
    ...filters
  };
  return this.find(query).sort({ pinnedAt: -1, createdAt: -1 });
};

messageSchema.statics.getByTemplate = async function(templateName, filters = {}) {
  const query = {
    'template.name': templateName,
    isArchived: false,
    ...filters
  };
  return this.find(query).sort({ createdAt: -1 });
};

messageSchema.statics.getStructuredStats = async function() {
  const [byTemplate, byReminderType, pinnedCount] = await Promise.all([
    this.aggregate([
      { $match: { isArchived: false } },
      { $group: { _id: '$template.name', count: { $sum: 1 } } }
    ]),
    this.aggregate([
      { $match: { 'reminder.isPinned': true, isArchived: false } },
      { $group: { _id: '$reminder.type', count: { $sum: 1 } } }
    ]),
    this.countDocuments({ isPinned: true, isArchived: false })
  ]);

  return {
    byTemplate: Object.fromEntries(byTemplate.map(item => [item._id || 'unknown', item.count])),
    byReminderType: Object.fromEntries(byReminderType.map(item => [item._id || 'unknown', item.count])),
    pinnedCount
  };
};

messageSchema.methods.generateSummary = async function(summaryService) {
  const result = await summaryService.summarizeMessage(this.toObject());
  this.summary = result.summary;
  this.summaryInfo = {
    ...result,
    generatedAt: new Date()
  };
  return this.save();
};

messageSchema.methods.analyzeReminder = async function(reminderService) {
  const analysis = await reminderService.processMessage(this);
  if (analysis.isReminder) {
    this.reminder.analyzedAt = new Date();
  }
  return this.save();
};

messageSchema.methods.parseTemplate = async function(templateParserService) {
  const result = await templateParserService.parseMessage(this.toObject());
  this.template = {
    name: result.template,
    displayName: result.templateDisplayName,
    matched: result.matched,
    matchScore: result.matchScore,
    parsedAt: new Date()
  };
  this.structuredData = result.structuredData;
  this.card = {
    ...result.card,
    generatedAt: new Date()
  };
  if (result.matched && result.card.priority) {
    this.priority = result.card.priority;
  }
  return this.save();
};

messageSchema.methods.pin = async function() {
  this.isPinned = true;
  this.pinnedAt = new Date();
  if (!this.reminder) {
    this.reminder = {
      type: 'manual',
      category: 'manual',
      priority: 'high',
      isPinned: true,
      pinnedAt: new Date()
    };
  } else {
    this.reminder.isPinned = true;
    this.reminder.pinnedAt = new Date();
  }
  return this.save();
};

messageSchema.methods.unpin = async function() {
  this.isPinned = false;
  this.pinnedAt = null;
  if (this.reminder) {
    this.reminder.isPinned = false;
    this.reminder.pinnedAt = null;
  }
  return this.save();
};

module.exports = mongoose.model('Message', messageSchema);
