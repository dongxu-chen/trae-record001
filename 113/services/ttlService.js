const redis = require('../config/redis');

const SHORTLINK_PREFIX = 'shortlink:';
const LAST_ACCESS_PREFIX = 'lastaccess:';
const TTL_YEAR = 365 * 24 * 60 * 60;
const CLEANUP_INTERVAL = 60 * 60 * 1000;

class TTLService {
  constructor() {
    this.cleanupTimer = null;
  }

  async setLastAccess(shortCode) {
    const key = LAST_ACCESS_PREFIX + shortCode;
    await redis.set(key, Date.now());
  }

  async getLastAccess(shortCode) {
    const key = LAST_ACCESS_PREFIX + shortCode;
    const timestamp = await redis.get(key);
    return timestamp ? parseInt(timestamp) : null;
  }

  async createShortlink(shortCode, longUrl) {
    const linkKey = SHORTLINK_PREFIX + shortCode;
    const accessKey = LAST_ACCESS_PREFIX + shortCode;
    
    await redis.set(linkKey, longUrl);
    await redis.set(accessKey, Date.now());
  }

  async getLongUrl(shortCode) {
    const linkKey = SHORTLINK_PREFIX + shortCode;
    const accessKey = LAST_ACCESS_PREFIX + shortCode;
    
    const longUrl = await redis.get(linkKey);
    if (!longUrl) {
      return null;
    }

    await redis.set(accessKey, Date.now());
    
    return longUrl;
  }

  async deleteShortlink(shortCode) {
    const linkKey = SHORTLINK_PREFIX + shortCode;
    const accessKey = LAST_ACCESS_PREFIX + shortCode;
    
    await redis.del(linkKey);
    await redis.del(accessKey);
    
    console.log(`Deleted expired shortlink: ${shortCode}`);
  }

  async isExpired(shortCode) {
    const lastAccess = await this.getLastAccess(shortCode);
    if (!lastAccess) {
      return true;
    }
    
    const now = Date.now();
    const expireTime = lastAccess + (TTL_YEAR * 1000);
    
    return now > expireTime;
  }

  async cleanupExpired() {
    try {
      console.log('Starting expired shortlinks cleanup...');
      
      const keys = await redis.keys(SHORTLINK_PREFIX + '*');
      let cleanedCount = 0;
      
      for (const key of keys) {
        const shortCode = key.replace(SHORTLINK_PREFIX, '');
        
        if (await this.isExpired(shortCode)) {
          await this.deleteShortlink(shortCode);
          cleanedCount++;
        }
      }
      
      console.log(`Cleanup completed. Removed ${cleanedCount} expired shortlinks.`);
      return cleanedCount;
    } catch (error) {
      console.error('Cleanup error:', error);
      return 0;
    }
  }

  startCleanupScheduler() {
    if (this.cleanupTimer) {
      console.log('Cleanup scheduler already running');
      return;
    }

    this.cleanupTimer = setInterval(async () => {
      await this.cleanupExpired();
    }, CLEANUP_INTERVAL);

    console.log('TTL cleanup scheduler started');
  }

  stopCleanupScheduler() {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = null;
      console.log('TTL cleanup scheduler stopped');
    }
  }

  async getStats() {
    const keys = await redis.keys(SHORTLINK_PREFIX + '*');
    const total = keys.length;
    
    let expired = 0;
    for (const key of keys) {
      const shortCode = key.replace(SHORTLINK_PREFIX, '');
      if (await this.isExpired(shortCode)) {
        expired++;
      }
    }
    
    return {
      total,
      expired,
      active: total - expired
    };
  }
}

module.exports = new TTLService();