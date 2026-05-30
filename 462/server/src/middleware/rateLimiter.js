const rateLimit = require('express-rate-limit')

const captchaRateLimit = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  message: {
    success: false,
    message: '请求过于频繁，请稍后再试',
  },
  standardHeaders: true,
  legacyHeaders: false,
})

const verifyRateLimit = rateLimit({
  windowMs: 1 * 60 * 1000,
  max: 20,
  message: {
    success: false,
    message: '验证次数过多，请稍后再试',
  },
  standardHeaders: true,
  legacyHeaders: false,
})

module.exports = {
  captchaRateLimit,
  verifyRateLimit,
}
