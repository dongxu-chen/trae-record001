import { LRUCache } from 'lru-cache';

class GatewayRateLimiter {
  constructor(options = {}) {
    this.ipLimits = options.ipLimits || {
      max: 100,
      windowMs: 60 * 1000,
    };
    this.userLimits = options.userLimits || {
      max: 200,
      windowMs: 60 * 1000,
    };
    this.globalLimits = options.globalLimits || {
      max: 1000,
      windowMs: 60 * 1000,
    };
    
    this.ipCache = new LRUCache({
      max: 10000,
      ttl: this.ipLimits.windowMs,
    });
    
    this.userCache = new LRUCache({
      max: 10000,
      ttl: this.userLimits.windowMs,
    });
    
    this.globalRequestCount = 0;
    this.globalWindowStart = Date.now();
    
    this.blockedIPs = new Set();
    this.blockedUsers = new Set();
    
    this.stats = {
      totalRequests: 0,
      blockedRequests: 0,
      ipLimited: 0,
      userLimited: 0,
      globalLimited: 0,
    };
  }

  getRateLimitKey(ip, userId = null) {
    return {
      ipKey: `rate:ip:${ip}`,
      userKey: userId ? `rate:user:${userId}` : null,
    };
  }

  checkGlobalLimit() {
    const now = Date.now();
    const windowElapsed = now - this.globalWindowStart;
    
    if (windowElapsed >= this.globalLimits.windowMs) {
      this.globalRequestCount = 0;
      this.globalWindowStart = now;
    }
    
    if (this.globalRequestCount >= this.globalLimits.max) {
      return {
        allowed: false,
        reason: 'GLOBAL_LIMIT_EXCEEDED',
        limit: this.globalLimits.max,
        remaining: 0,
        resetIn: this.globalLimits.windowMs - windowElapsed,
      };
    }
    
    return null;
  }

  checkIPLimit(ip) {
    if (this.blockedIPs.has(ip)) {
      return {
        allowed: false,
        reason: 'IP_BLOCKED',
        limit: 0,
        remaining: 0,
        resetIn: this.ipLimits.windowMs,
      };
    }

    const key = `rate:ip:${ip}`;
    const current = this.ipCache.get(key) || 0;
    
    if (current >= this.ipLimits.max) {
      return {
        allowed: false,
        reason: 'IP_LIMIT_EXCEEDED',
        limit: this.ipLimits.max,
        remaining: 0,
        resetIn: this.ipCache.getRemainingTTL(key),
      };
    }
    
    return null;
  }

  checkUserLimit(userId) {
    if (!userId) return null;
    
    if (this.blockedUsers.has(userId)) {
      return {
        allowed: false,
        reason: 'USER_BLOCKED',
        limit: 0,
        remaining: 0,
        resetIn: this.userLimits.windowMs,
      };
    }

    const key = `rate:user:${userId}`;
    const current = this.userCache.get(key) || 0;
    
    if (current >= this.userLimits.max) {
      return {
        allowed: false,
        reason: 'USER_LIMIT_EXCEEDED',
        limit: this.userLimits.max,
        remaining: 0,
        resetIn: this.userCache.getRemainingTTL(key),
      };
    }
    
    return null;
  }

  increment(ip, userId = null) {
    this.stats.totalRequests++;
    this.globalRequestCount++;
    
    const ipKey = `rate:ip:${ip}`;
    const ipCurrent = (this.ipCache.get(ipKey) || 0) + 1;
    this.ipCache.set(ipKey, ipCurrent);
    
    if (userId) {
      const userKey = `rate:user:${userId}`;
      const userCurrent = (this.userCache.get(userKey) || 0) + 1;
      this.userCache.set(userKey, userCurrent);
    }
    
    return {
      ipRemaining: this.ipLimits.max - ipCurrent,
      userRemaining: userId ? this.userLimits.max - (this.userCache.get(`rate:user:${userId}`) || 0) : null,
      globalRemaining: this.globalLimits.max - this.globalRequestCount,
    };
  }

  checkRateLimit(ip, userId = null) {
    const globalResult = this.checkGlobalLimit();
    if (globalResult) {
      this.stats.blockedRequests++;
      this.stats.globalLimited++;
      return globalResult;
    }

    const ipResult = this.checkIPLimit(ip);
    if (ipResult) {
      this.stats.blockedRequests++;
      this.stats.ipLimited++;
      return ipResult;
    }

    const userResult = this.checkUserLimit(userId);
    if (userResult) {
      this.stats.blockedRequests++;
      this.stats.userLimited++;
      return userResult;
    }

    const remaining = this.increment(ip, userId);
    
    return {
      allowed: true,
      ...remaining,
    };
  }

  blockIP(ip, durationMs = 60 * 60 * 1000) {
    this.blockedIPs.add(ip);
    setTimeout(() => {
      this.blockedIPs.delete(ip);
    }, durationMs);
    console.log(`🚫 IP ${ip} blocked for ${durationMs}ms`);
  }

  blockUser(userId, durationMs = 60 * 60 * 1000) {
    this.blockedUsers.add(userId);
    setTimeout(() => {
      this.blockedUsers.delete(userId);
    }, durationMs);
    console.log(`🚫 User ${userId} blocked for ${durationMs}ms`);
  }

  unblockIP(ip) {
    this.blockedIPs.delete(ip);
  }

  unblockUser(userId) {
    this.blockedUsers.delete(userId);
  }

  getStats() {
    return {
      ...this.stats,
      blockedIPCount: this.blockedIPs.size,
      blockedUserCount: this.blockedUsers.size,
      activeIPs: this.ipCache.size,
      activeUsers: this.userCache.size,
    };
  }

  resetStats() {
    this.stats = {
      totalRequests: 0,
      blockedRequests: 0,
      ipLimited: 0,
      userLimited: 0,
      globalLimited: 0,
    };
  }

  getLimits() {
    return {
      ip: this.ipLimits,
      user: this.userLimits,
      global: this.globalLimits,
    };
  }

  updateLimits(type, newLimits) {
    if (type === 'ip') {
      Object.assign(this.ipLimits, newLimits);
    } else if (type === 'user') {
      Object.assign(this.userLimits, newLimits);
    } else if (type === 'global') {
      Object.assign(this.globalLimits, newLimits);
    }
  }
}

export const gatewayRateLimiter = new GatewayRateLimiter({
  ipLimits: { max: 100, windowMs: 60 * 1000 },
  userLimits: { max: 200, windowMs: 60 * 1000 },
  globalLimits: { max: 1000, windowMs: 60 * 1000 },
});

export default GatewayRateLimiter;
