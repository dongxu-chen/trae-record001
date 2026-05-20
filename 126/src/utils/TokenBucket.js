class TokenBucket {
  constructor(options = {}) {
    this.capacity = options.capacity || 10;
    this.tokens = this.capacity;
    this.fillPerSecond = options.fillPerSecond || 10;
    this.lastFillTime = Date.now();
    this.waitingQueue = [];
    this.isProcessingQueue = false;
    this.totalRequests = 0;
    this.rejectedRequests = 0;
    this.processedRequests = 0;
  }

  refill() {
    const now = Date.now();
    const elapsedSeconds = (now - this.lastFillTime) / 1000;
    const tokensToAdd = elapsedSeconds * this.fillPerSecond;
    
    if (tokensToAdd > 0) {
      this.tokens = Math.min(this.capacity, this.tokens + tokensToAdd);
      this.lastFillTime = now;
    }
  }

  async acquire(options = {}) {
    this.totalRequests++;
    const tokensNeeded = options.tokens || 1;
    const maxWait = options.maxWait || 5000;
    const priority = options.priority || 0;

    this.refill();

    if (this.tokens >= tokensNeeded) {
      this.tokens -= tokensNeeded;
      this.processedRequests++;
      return true;
    }

    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        this.waitingQueue = this.waitingQueue.filter(item => item.timeoutId !== timeoutId);
        this.rejectedRequests++;
        reject(new Error(`Request timed out after ${maxWait}ms waiting for token`));
      }, maxWait);

      const queueItem = {
        tokensNeeded,
        timeoutId,
        resolve,
        reject,
        priority,
        addedAt: Date.now(),
      };

      const insertIndex = this.waitingQueue.findIndex(
        item => item.priority < priority
      );
      
      if (insertIndex === -1) {
        this.waitingQueue.push(queueItem);
      } else {
        this.waitingQueue.splice(insertIndex, 0, queueItem);
      }

      if (!this.isProcessingQueue) {
        this.processQueue();
      }
    });
  }

  async processQueue() {
    if (this.isProcessingQueue) return;
    this.isProcessingQueue = true;

    while (this.waitingQueue.length > 0) {
      this.refill();
      
      const nextItem = this.waitingQueue[0];
      
      if (this.tokens >= nextItem.tokensNeeded) {
        this.waitingQueue.shift();
        clearTimeout(nextItem.timeoutId);
        this.tokens -= nextItem.tokensNeeded;
        this.processedRequests++;
        nextItem.resolve(true);
      } else {
        const nextTokenTime = ((nextItem.tokensNeeded - this.tokens) / this.fillPerSecond) * 1000;
        await new Promise(resolve => setTimeout(resolve, Math.max(10, nextTokenTime)));
      }
    }

    this.isProcessingQueue = false;
  }

  tryAcquire(options = {}) {
    this.refill();
    const tokensNeeded = options.tokens || 1;
    
    if (this.tokens >= tokensNeeded) {
      this.tokens -= tokensNeeded;
      this.processedRequests++;
      this.totalRequests++;
      return true;
    }
    
    this.totalRequests++;
    this.rejectedRequests++;
    return false;
  }

  getStats() {
    this.refill();
    return {
      availableTokens: this.tokens,
      capacity: this.capacity,
      fillRate: this.fillPerSecond,
      waitingQueueSize: this.waitingQueue.length,
      totalRequests: this.totalRequests,
      rejectedRequests: this.rejectedRequests,
      processedRequests: this.processedRequests,
      rejectionRate: this.totalRequests > 0 
        ? (this.rejectedRequests / this.totalRequests * 100).toFixed(2) + '%'
        : '0%',
    };
  }

  resetStats() {
    this.totalRequests = 0;
    this.rejectedRequests = 0;
    this.processedRequests = 0;
  }

  clear() {
    this.waitingQueue.forEach(item => {
      clearTimeout(item.timeoutId);
      item.reject(new Error('Token bucket cleared'));
    });
    this.waitingQueue = [];
    this.tokens = this.capacity;
    this.lastFillTime = Date.now();
  }
}

export const globalRateLimiter = new TokenBucket({
  capacity: 10,
  fillPerSecond: 10,
});

export const createRateLimiter = (options) => new TokenBucket(options);

export const withRateLimit = (fn, options = {}) => {
  const rateLimiter = options.rateLimiter || globalRateLimiter;
  
  return async (...args) => {
    try {
      await rateLimiter.acquire(options);
      return await fn(...args);
    } catch (error) {
      if (options.onReject) {
        return options.onReject(error, ...args);
      }
      throw error;
    }
  };
};

export const rateLimitMiddleware = (options = {}) => {
  const rateLimiter = options.rateLimiter || globalRateLimiter;
  
  return async (resolve, parent, args, context, info) => {
    try {
      await rateLimiter.acquire({ 
        tokens: options.tokens, 
        maxWait: options.maxWait,
        priority: options.priority,
      });
      return resolve();
    } catch (error) {
      console.warn(`[RateLimit] Field ${info.fieldName} rejected: ${error.message}`);
      throw new Error(`Rate limit exceeded. Please try again later.`);
    }
  };
};

export default TokenBucket;
