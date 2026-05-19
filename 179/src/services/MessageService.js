const { v4: uuidv4 } = require('uuid');
const Message = require('../models/Message');
const Channel = require('../models/Channel');
const adapterFactory = require('../adapters/AdapterFactory');
const deduplicationService = require('./DeduplicationService');
const classificationService = require('./ClassificationService');
const summaryService = require('./SummaryService');
const reminderService = require('./ReminderService');
const templateParserService = require('./TemplateParserService');
const logger = require('../utils/logger');

class MessageService {
  async fetchFromAllChannels(since = null) {
    const channels = await Channel.getEnabledChannels();
    logger.info(`Fetching messages from ${channels.length} enabled channels`);

    const results = [];
    const errors = [];

    for (const channel of channels) {
      try {
        let adapter = adapterFactory.getAdapter(channel._id);
        if (!adapter) {
          adapter = adapterFactory.createAdapter(channel);
          await adapter.connect();
        }

        if (!adapter.isConnected()) {
          await adapter.connect();
        }

        const messages = await adapter.fetchMessages(since);
        logger.info(`Fetched ${messages.length} messages from ${channel.type}`);

        const processedMessages = await this.processFetchedMessages(messages, channel);
        results.push({
          channel: channel.type,
          fetched: messages.length,
          processed: processedMessages.newMessages.length,
          duplicates: processedMessages.duplicates.length
        });

        channel.lastSync = new Date();
        channel.status = 'active';
        channel.lastError = null;
        await channel.save();
      } catch (error) {
        logger.error(`Failed to fetch from ${channel.type}:`, error);
        errors.push({
          channel: channel.type,
          error: error.message
        });
        channel.lastError = error.message;
        channel.status = 'error';
        await channel.save();
      }
    }

    return { results, errors };
  }

  async fetchFromChannel(channelType, since = null) {
    const channel = await Channel.getByType(channelType);
    if (!channel) {
      throw new Error(`Channel ${channelType} not found or disabled`);
    }

    let adapter = adapterFactory.getAdapter(channel._id);
    if (!adapter) {
      adapter = adapterFactory.createAdapter(channel);
      await adapter.connect();
    }

    if (!adapter.isConnected()) {
      await adapter.connect();
    }

    const messages = await adapter.fetchMessages(since);
    const processedMessages = await this.processFetchedMessages(messages, channel);

    channel.lastSync = new Date();
    channel.status = 'active';
    channel.lastError = null;
    await channel.save();

    return {
      channel: channelType,
      fetched: messages.length,
      processed: processedMessages.newMessages.length,
      duplicates: processedMessages.duplicates.length,
      messages: processedMessages.newMessages
    };
  }

  async processFetchedMessages(messages, channel) {
    const newMessages = [];
    const duplicates = [];

    for (const normalizedMsg of messages) {
      try {
        const dedupResult = await deduplicationService.processMessage(normalizedMsg);

        if (dedupResult.isDuplicate) {
          duplicates.push(dedupResult.message);
          continue;
        }

        const classification = await classificationService.classify(normalizedMsg);

        const contentText = `${normalizedMsg.title || ''} ${normalizedMsg.content || ''}`;
        const simHash = deduplicationService.computeSimHash(contentText);
        const simHashHex = deduplicationService.simHash.toHexString(simHash);

        const summaryResult = await summaryService.summarizeMessage(normalizedMsg);
        const reminderAnalysis = reminderService.analyzeMessage(normalizedMsg);
        const templateResult = await templateParserService.parseMessage(normalizedMsg);

        const messageId = uuidv4();
        const message = new Message({
          messageId,
          dedupKey: normalizedMsg.dedupKey,
          simHash: simHashHex,
          title: normalizedMsg.title,
          content: normalizedMsg.content,
          summary: summaryResult.summary,
          summaryInfo: {
            ...summaryResult,
            generatedAt: new Date()
          },
          category: classification.category,
          priority: classification.priority,
          isPinned: reminderAnalysis.shouldPin,
          pinnedAt: reminderAnalysis.shouldPin ? new Date() : null,
          reminder: reminderAnalysis.isReminder ? {
            type: reminderAnalysis.reminderType,
            category: reminderAnalysis.reminderCategory,
            priority: reminderAnalysis.reminderPriority,
            score: reminderAnalysis.score,
            matchedKeywords: reminderAnalysis.matchedKeywords,
            isPinned: reminderAnalysis.shouldPin,
            pinnedAt: reminderAnalysis.shouldPin ? new Date() : null,
            analyzedAt: new Date()
          } : null,
          template: {
            name: templateResult.template,
            displayName: templateResult.templateDisplayName,
            matched: templateResult.matched,
            matchScore: templateResult.matchScore,
            parsedAt: new Date()
          },
          structuredData: templateResult.structuredData,
          card: {
            ...templateResult.card,
            generatedAt: new Date()
          },
          channels: [{
            channel: channel.type,
            channelMessageId: normalizedMsg.channelMessageId,
            receivedAt: normalizedMsg.receivedAt,
            isRead: false,
            raw: normalizedMsg.raw
          }],
          sender: normalizedMsg.sender,
          recipients: normalizedMsg.recipients,
          attachments: normalizedMsg.attachments,
          metadata: {
            classificationScores: classification.scores
          },
          isRead: false
        });

        await message.save();
        newMessages.push(message);
        logger.info(`Saved new message: ${messageId} from ${channel.type}`);

        const aggregationService = require('./AggregationService');
        await aggregationService.processNewMessage(message);
      } catch (error) {
        logger.error('Failed to process message:', error);
      }
    }

    return { newMessages, duplicates };
  }

  async getMessages(filters = {}, options = {}) {
    const query = { isArchived: false, ...filters };

    const sort = options.sort || { createdAt: -1 };
    const page = options.page || 1;
    const pageSize = options.pageSize || 20;
    const skip = (page - 1) * pageSize;

    const [messages, total] = await Promise.all([
      Message.find(query)
        .sort(sort)
        .skip(skip)
        .limit(pageSize)
        .lean(),
      Message.countDocuments(query)
    ]);

    return {
      messages,
      pagination: {
        page,
        pageSize,
        total,
        totalPages: Math.ceil(total / pageSize)
      }
    };
  }

  async getMessageById(messageId) {
    return Message.findOne({ messageId }).lean();
  }

  async markAsRead(messageId, channel = null) {
    const message = await Message.findOne({ messageId });
    if (!message) {
      throw new Error('Message not found');
    }

    await message.markAsRead(channel);

    if (channel) {
      const channelInfo = message.channels.find(c => c.channel === channel);
      if (channelInfo) {
        try {
          const adapter = adapterFactory.getAdapterByType(channel);
          if (adapter) {
            await adapter.markAsRead([channelInfo.channelMessageId]);
          }
        } catch (error) {
          logger.error(`Failed to mark as read in ${channel}:`, error);
        }
      }
    }

    return message;
  }

  async markAsUnread(messageId, channel = null) {
    const message = await Message.findOne({ messageId });
    if (!message) {
      throw new Error('Message not found');
    }

    await message.markAsUnread(channel);

    if (channel) {
      const channelInfo = message.channels.find(c => c.channel === channel);
      if (channelInfo) {
        try {
          const adapter = adapterFactory.getAdapterByType(channel);
          if (adapter) {
            await adapter.markAsUnread([channelInfo.channelMessageId]);
          }
        } catch (error) {
          logger.error(`Failed to mark as unread in ${channel}:`, error);
        }
      }
    }

    return message;
  }

  async markAllAsRead(filters = {}) {
    const query = { isRead: false, isArchived: false, ...filters };
    const result = await Message.updateMany(query, {
      $set: {
        isRead: true,
        readAt: new Date(),
        'channels.$[].isRead': true,
        'channels.$[].readAt': new Date()
      }
    });

    return {
      modifiedCount: result.modifiedCount
    };
  }

  async archiveMessage(messageId) {
    const message = await Message.findOne({ messageId });
    if (!message) {
      throw new Error('Message not found');
    }

    message.isArchived = true;
    message.archivedAt = new Date();
    await message.save();

    return message;
  }

  async deleteMessage(messageId) {
    const result = await Message.deleteOne({ messageId });
    if (result.deletedCount === 0) {
      throw new Error('Message not found');
    }
    return { success: true };
  }

  async getUnreadCount(filters = {}) {
    return Message.getUnreadCount(filters);
  }

  async getUnreadByCategory() {
    const results = await Message.getUnreadByCategory();
    const counts = {
      notification: 0,
      approval: 0,
      alert: 0,
      other: 0
    };

    for (const result of results) {
      counts[result._id] = result.count;
    }

    return counts;
  }

  async getUnreadByChannel() {
    const results = await Message.aggregate([
      { $match: { isRead: false, isArchived: false } },
      { $unwind: '$channels' },
      { $match: { 'channels.isRead': false } },
      { $group: { _id: '$channels.channel', count: { $sum: 1 } } }
    ]);

    const counts = {
      email: 0,
      dingtalk: 0,
      wework: 0,
      slack: 0
    };

    for (const result of results) {
      counts[result._id] = result.count;
    }

    return counts;
  }

  async getStats() {
    const [total, unread, byCategory, byChannel, structuredStats] = await Promise.all([
      Message.countDocuments({ isArchived: false }),
      this.getUnreadCount(),
      this.getUnreadByCategory(),
      this.getUnreadByChannel(),
      Message.getStructuredStats()
    ]);

    return {
      total,
      unread,
      byCategory,
      byChannel,
      ...structuredStats
    };
  }

  async getPinnedMessages(filters = {}, options = {}) {
    const query = {
      isPinned: true,
      isArchived: false,
      ...filters
    };

    const sort = options.sort || { 'reminder.score': -1, pinnedAt: -1, createdAt: -1 };
    const page = options.page || 1;
    const pageSize = options.pageSize || 20;
    const skip = (page - 1) * pageSize;

    const [messages, total] = await Promise.all([
      Message.find(query)
        .sort(sort)
        .skip(skip)
        .limit(pageSize)
        .lean(),
      Message.countDocuments(query)
    ]);

    return {
      messages,
      pagination: {
        page,
        pageSize,
        total,
        totalPages: Math.ceil(total / pageSize)
      }
    };
  }

  async pinMessage(messageId) {
    const message = await Message.findOne({ messageId });
    if (!message) {
      throw new Error('Message not found');
    }
    return message.pin();
  }

  async unpinMessage(messageId) {
    const message = await Message.findOne({ messageId });
    if (!message) {
      throw new Error('Message not found');
    }
    return message.unpin();
  }

  async getReminderMessages(filters = {}) {
    return reminderService.getReminderMessages(filters);
  }

  async getReminderStats() {
    return reminderService.getReminderStats();
  }

  async regenerateSummary(messageId) {
    const message = await Message.findOne({ messageId });
    if (!message) {
      throw new Error('Message not found');
    }
    return message.generateSummary(summaryService);
  }

  async regenerateAllSummaries(filters = {}) {
    const query = { isArchived: false, ...filters };
    const messages = await Message.find(query);
    const results = [];

    for (const msg of messages) {
      try {
        await msg.generateSummary(summaryService);
        results.push({ messageId: msg.messageId, success: true });
      } catch (error) {
        results.push({ messageId: msg.messageId, success: false, error: error.message });
      }
    }

    return {
      total: messages.length,
      success: results.filter(r => r.success).length,
      failed: results.filter(r => !r.success).length,
      results
    };
  }

  async reparseTemplate(messageId) {
    const message = await Message.findOne({ messageId });
    if (!message) {
      throw new Error('Message not found');
    }
    return message.parseTemplate(templateParserService);
  }

  async reparseAllTemplates(filters = {}) {
    const query = { isArchived: false, ...filters };
    const messages = await Message.find(query);
    const results = [];

    for (const msg of messages) {
      try {
        await msg.parseTemplate(templateParserService);
        results.push({ messageId: msg.messageId, success: true, template: msg.template?.name });
      } catch (error) {
        results.push({ messageId: msg.messageId, success: false, error: error.message });
      }
    }

    return {
      total: messages.length,
      success: results.filter(r => r.success).length,
      failed: results.filter(r => !r.success).length,
      results
    };
  }

  async reanalyzeReminder(messageId) {
    const message = await Message.findOne({ messageId });
    if (!message) {
      throw new Error('Message not found');
    }
    return message.analyzeReminder(reminderService);
  }

  async getByTemplate(templateName, filters = {}, options = {}) {
    const query = {
      'template.name': templateName,
      isArchived: false,
      ...filters
    };

    const sort = options.sort || { createdAt: -1 };
    const page = options.page || 1;
    const pageSize = options.pageSize || 20;
    const skip = (page - 1) * pageSize;

    const [messages, total] = await Promise.all([
      Message.find(query)
        .sort(sort)
        .skip(skip)
        .limit(pageSize)
        .lean(),
      Message.countDocuments(query)
    ]);

    return {
      messages,
      pagination: {
        page,
        pageSize,
        total,
        totalPages: Math.ceil(total / pageSize)
      }
    };
  }

  async getCard(messageId) {
    const message = await Message.findOne({ messageId }).lean();
    if (!message) {
      throw new Error('Message not found');
    }
    return message.card || null;
  }

  async getStructuredData(messageId) {
    const message = await Message.findOne({ messageId }).lean();
    if (!message) {
      throw new Error('Message not found');
    }
    return message.structuredData || {};
  }
}

module.exports = new MessageService();
module.exports.MessageService = MessageService;
