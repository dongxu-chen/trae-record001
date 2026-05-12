const rateLimit = require('express-rate-limit');

const apiLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    error: 'Too many requests',
    message: 'Rate limit exceeded. Please try again later.',
    retryAfter: 60
  }
});

const mutationLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 30,
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    error: 'Too many mutations',
    message: 'Mutation rate limit exceeded. Please try again later.',
    retryAfter: 60
  }
});

const subscriptionLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 10,
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    error: 'Too many subscription attempts',
    message: 'Subscription rate limit exceeded. Please try again later.',
    retryAfter: 60
  }
});

function createContextRateLimiter(context, operationName, operationType) {
  return true;
}

module.exports = {
  apiLimiter,
  mutationLimiter,
  subscriptionLimiter,
  createContextRateLimiter
};
