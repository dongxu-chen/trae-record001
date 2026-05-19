const { getClient } = require('../db/redis');
const Message = require('../models/Message');
const config = require('../config');
const logger = require('../utils/logger');
const { SimHash } = require('../utils/SimHash');

class DeduplicationService {
  constructor() {
    this.windowMinutes = config.deduplication.windowMinutes || 30;
    this.similarityThreshold = config.deduplication.similarityThreshold || 0.85;
    this.simHash = new SimHash(64);
  }

  computeSimHash(text) {
    return this.simHash.compute(text);
  }

  async findDuplicate(normalizedMessage) {
    const redisClient = getClient();
    const contentText = `${normalizedMessage.title || ''} ${normalizedMessage.content || ''}`;
    const newSimHash = this.computeSimHash(contentText);
    const newSimHashHex = this.simHash.toHexString(newSimHash);

    const cacheKey = `dedup:simhash:${newSimHashHex}`;
    const cachedMessageId = await redisClient.get(cacheKey);
    
    if (cachedMessageId) {
      const existingMessage = await Message.findOne({ messageId: cachedMessageId });
      if (existingMessage && existingMessage.simHash) {
        const existingSimHash = this.simHash.fromHexString(existingMessage.simHash);
        const similarity = this.simHash.similarity(newSimHash, existingSimHash);
        if (similarity >= this.similarityThreshold) {
          return existingMessage;
        }
      }
    }

    const windowStart = new Date(Date.now() - this.windowMinutes * 60 * 1000);
    const recentMessages = await Message.find({
      createdAt: { $gte: windowStart },
      simHash: { $exists: true }
    }).select('messageId simHash title content channels');

    for (const msg of recentMessages) {
      try {
        const existingSimHash = this.simHash.fromHexString(msg.simHash);
        const similarity = this.simHash.similarity(newSimHash, existingSimHash);
        
        if (similarity >= this.similarityThreshold) {
          await redisClient.setEx(
            cacheKey,
            this.windowMinutes * 60,
            msg.messageId
          );
          return msg;
        }
      } catch (err) {
        logger.warn('Error comparing SimHash:', err.message);
      }
    }

    return null;
  }

  async findSimilar(contentText, threshold = null) {
    const simThreshold = threshold || this.similarityThreshold;
    const newSimHash = this.computeSimHash(contentText);

    const windowStart = new Date(Date.now() - this.windowMinutes * 60 * 1000);
    const recentMessages = await Message.find({
      createdAt: { $gte: windowStart },
      simHash: { $exists: true }
    }).select('messageId simHash title content');

    let bestMatch = null;
    let bestSimilarity = 0;

    for (const msg of recentMessages) {
      try {
        const existingSimHash = this.simHash.fromHexString(msg.simHash);
        const similarity = this.simHash.similarity(newSimHash, existingSimHash);
        
        if (similarity >= simThreshold && similarity > bestSimilarity) {
          bestSimilarity = similarity;
          bestMatch = msg;
        }
      } catch (err) {
        logger.warn('Error comparing SimHash:', err.message);
      }
    }

    return bestMatch;
  }

  calculateSimilarity(text1, text2) {
    return this.simHash.similarityText(text1, text2);
  }

  async mergeMessage(existingMessage, normalizedMessage) {
    const channelExists = existingMessage.channels.some(
      c => c.channel === normalizedMessage.channel &&
           c.channelMessageId === normalizedMessage.channelMessageId
    );

    if (!channelExists) {
      existingMessage.channels.push({
        channel: normalizedMessage.channel,
        channelMessageId: normalizedMessage.channelMessageId,
        receivedAt: normalizedMessage.receivedAt,
        isRead: false,
        raw: normalizedMessage.raw
      });

      const hasAnyRead = existingMessage.channels.some(c => c.isRead);
      existingMessage.isRead = hasAnyRead;

      if (hasAnyRead) {
        existingMessage.readAt = existingMessage.readAt || new Date();
      }

      await existingMessage.save();
      logger.info(`Merged duplicate message from ${normalizedMessage.channel} into message ${existingMessage.messageId}`);
    }

    return existingMessage;
  }

  async processMessage(normalizedMessage) {
    const existingMessage = await this.findDuplicate(normalizedMessage);

    if (existingMessage) {
      return {
        isDuplicate: true,
        message: await this.mergeMessage(existingMessage, normalizedMessage)
      };
    }

    return {
      isDuplicate: false,
      message: null
    };
  }

  async clearDedupCache() {
    const redisClient = getClient();
    const keys = await redisClient.keys('dedup:*');
    if (keys.length > 0) {
      await redisClient.del(keys);
    }
    logger.info('Deduplication cache cleared');
  }

  async batchComputeSimHash() {
    const messages = await Message.find({ simHash: { $exists: false } }).select('messageId title content');
    
    for (const msg of messages) {
      const contentText = `${msg.title || ''} ${msg.content || ''}`;
      const simHash = this.computeSimHash(contentText);
      const simHashHex = this.simHash.toHexString(simHash);
      
      await Message.updateOne(
        { messageId: msg.messageId },
        { $set: { simHash: simHashHex } }
      );
    }
    
    logger.info(`Updated SimHash for ${messages.length} messages`);
    return messages.length;
  }
}

module.exports = new DeduplicationService();
module.exports.DeduplicationService = DeduplicationService;
