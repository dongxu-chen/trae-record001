const { createClient } = require('redis');
const config = require('../config');
const logger = require('../utils/logger');

let client = null;

const connect = async () => {
  try {
    const options = {
      socket: {
        host: config.redis.host,
        port: config.redis.port
      }
    };

    if (config.redis.password) {
      options.password = config.redis.password;
    }

    client = createClient(options);

    client.on('error', (err) => {
      logger.error('Redis client error:', err);
    });

    client.on('connect', () => {
      logger.info('Redis connected successfully');
    });

    client.on('end', () => {
      logger.warn('Redis disconnected');
    });

    await client.connect();
    return client;
  } catch (error) {
    logger.error('Redis connection error:', error);
    throw error;
  }
};

const getClient = () => {
  if (!client) {
    throw new Error('Redis client not initialized. Call connect() first.');
  }
  return client;
};

module.exports = { connect, getClient };
