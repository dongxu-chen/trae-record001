class TokenBucket {
  constructor(capacity, refillRate) {
    this.capacity = capacity;
    this.tokens = capacity;
    this.refillRate = refillRate;
    this.lastRefill = Date.now();
    this.lock = false;
  }
  
  refill() {
    const now = Date.now();
    const elapsed = (now - this.lastRefill) / 1000;
    
    if (elapsed > 0) {
      const newTokens = elapsed * this.refillRate;
      this.tokens = Math.min(this.capacity, this.tokens + newTokens);
      this.lastRefill = now;
    }
  }
  
  tryConsume(tokens = 1) {
    this.refill();
    
    if (this.tokens >= tokens) {
      this.tokens -= tokens;
      return true;
    }
    return false;
  }
  
  getAvailableTokens() {
    this.refill();
    return this.tokens;
  }
}

const benchmarkLimiter = new TokenBucket(1000, 1000);

const benchmarkRateLimit = (req, res, next) => {
  if (benchmarkLimiter.tryConsume()) {
    next();
  } else {
    res.status(429).json({
      success: false,
      error: '请求过于频繁，请稍后重试',
      rateLimit: {
        limit: 1000,
        remaining: Math.floor(benchmarkLimiter.getAvailableTokens())
      }
    });
  }
};

module.exports = {
  TokenBucket,
  benchmarkRateLimit
};