const mongoose = require('mongoose');
const config = require('../config');
const logger = require('../utils/logger');

const connect = async () => {
  try {
    await mongoose.connect(config.mongodb.uri);
    logger.info('MongoDB connected successfully');
  } catch (error) {
    logger.error('MongoDB connection error:', error);
    process.exit(1);
  }
};

mongoose.connection.on('error', (err) => {
  logger.error('MongoDB error:', err);
});

mongoose.connection.on('disconnected', () => {
  logger.warn('MongoDB disconnected');
});

module.exports = { connect, mongoose };
