require('dotenv').config();

module.exports = {
  port: process.env.PORT || 3000,
  env: process.env.NODE_ENV || 'development',

  mongodb: {
    uri: process.env.MONGODB_URI || 'mongodb://localhost:27017/message_center'
  },

  redis: {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379'),
    password: process.env.REDIS_PASSWORD || null
  },

  email: {
    imap: {
      host: process.env.EMAIL_IMAP_HOST,
      port: parseInt(process.env.EMAIL_IMAP_PORT || '993'),
      tls: process.env.EMAIL_IMAP_TLS !== 'false',
      user: process.env.EMAIL_USER,
      password: process.env.EMAIL_PASSWORD
    }
  },

  dingtalk: {
    appKey: process.env.DINGTALK_APP_KEY,
    appSecret: process.env.DINGTALK_APP_SECRET,
    userId: process.env.DINGTALK_USER_ID
  },

  wework: {
    corpId: process.env.WEWORK_CORP_ID,
    agentId: process.env.WEWORK_AGENT_ID,
    secret: process.env.WEWORK_SECRET,
    userId: process.env.WEWORK_USER_ID
  },

  slack: {
    botToken: process.env.SLACK_BOT_TOKEN,
    userId: process.env.SLACK_USER_ID
  },

  aggregation: {
    cron: process.env.AGGREGATION_CRON || '0 */30 * * * *',
    enabled: process.env.AGGREGATION_ENABLED !== 'false'
  },

  deduplication: {
    windowMinutes: parseInt(process.env.DEDUP_WINDOW_MINUTES || '30'),
    similarityThreshold: parseFloat(process.env.DEDUP_SIMILARITY_THRESHOLD || '0.85'),
    hashBits: parseInt(process.env.DEDUP_HASH_BITS || '64')
  },

  classification: {
    useFastText: process.env.CLASSIFICATION_USE_FASTTEXT !== 'false',
    modelPath: process.env.CLASSIFICATION_MODEL_PATH || null,
    trainingDataPath: process.env.CLASSIFICATION_TRAINING_DATA_PATH || null,
    minConfidence: parseFloat(process.env.CLASSIFICATION_MIN_CONFIDENCE || '0.3')
  },

  urgentNotification: {
    enabled: process.env.URGENT_NOTIFICATION_ENABLED !== 'false',
    cooldownPeriod: parseInt(process.env.URGENT_COOLDOWN_PERIOD || '60000'),
    priorityLevels: ['high', 'urgent'],
    categories: ['alert']
  },

  ai: {
    summary: {
      useExternalAI: process.env.AI_SUMMARY_USE_EXTERNAL === 'true',
      endpoint: process.env.AI_SUMMARY_ENDPOINT || 'https://api.openai.com/v1/chat/completions',
      apiKey: process.env.AI_SUMMARY_API_KEY || '',
      minLength: parseInt(process.env.AI_SUMMARY_MIN_LENGTH || '200'),
      defaultLength: parseInt(process.env.AI_SUMMARY_DEFAULT_LENGTH || '100')
    }
  },

  reminder: {
    enabled: process.env.REMINDER_ENABLED !== 'false',
    autoPin: process.env.REMINDER_AUTO_PIN !== 'false',
    pinPriority: ['urgent', 'high']
  },

  template: {
    enabled: process.env.TEMPLATE_ENABLED !== 'false',
    autoParse: process.env.TEMPLATE_AUTO_PARSE !== 'false',
    minMatchScore: parseFloat(process.env.TEMPLATE_MIN_MATCH_SCORE || '0.3')
  },

  jwt: {
    secret: process.env.JWT_SECRET || 'your-secret-key',
    expiresIn: '7d'
  }
};
