require('dotenv').config();

const express = require('express');
const config = require('./config');
const logger = require('./utils/logger');
const { connect: connectMongo } = require('./db/mongoose');
const { connect: connectRedis } = require('./db/redis');
const Channel = require('./models/Channel');
const adapterFactory = require('./adapters/AdapterFactory');
const aggregationService = require('./services/AggregationService');
const classificationService = require('./services/ClassificationService');

const messagesRoutes = require('./routes/messages');
const messagesEnhancedRoutes = require('./routes/messagesEnhanced');
const channelsRoutes = require('./routes/channels');
const preferencesRoutes = require('./routes/preferences');
const aggregationRoutes = require('./routes/aggregation');
const classificationRoutes = require('./routes/classification');

const app = express();

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

app.use((req, res, next) => {
  logger.info(`${req.method} ${req.path}`);
  next();
});

app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

app.use('/api/messages', messagesRoutes);
app.use('/api/messages/enhanced', messagesEnhancedRoutes);
app.use('/api/channels', channelsRoutes);
app.use('/api/preferences', preferencesRoutes);
app.use('/api/aggregation', aggregationRoutes);
app.use('/api/classification', classificationRoutes);

app.use((err, req, res, next) => {
  logger.error('Unhandled error:', err);
  res.status(500).json({
    error: 'Internal Server Error',
    message: config.env === 'development' ? err.message : undefined
  });
});

app.use((req, res) => {
  res.status(404).json({ error: 'Not Found' });
});

const initAdapters = async () => {
  try {
    const channels = await Channel.getEnabledChannels();
    logger.info(`Initializing ${channels.length} channel adapters`);

    for (const channel of channels) {
      try {
        const adapter = adapterFactory.createAdapter(channel);
        await adapter.connect();
        logger.info(`Adapter for ${channel.type} connected successfully`);
      } catch (error) {
        logger.error(`Failed to initialize adapter for ${channel.type}:`, error);
        channel.status = 'error';
        channel.lastError = error.message;
        await channel.save();
      }
    }
  } catch (error) {
    logger.error('Failed to initialize adapters:', error);
  }
};

const startServer = async () => {
  try {
    await connectMongo();
    await connectRedis();
    await classificationService.initialize();
    await initAdapters();
    await aggregationService.start();

    app.listen(config.port, () => {
      logger.info(`Server is running on port ${config.port}`);
      logger.info(`Environment: ${config.env}`);
    });
  } catch (error) {
    logger.error('Failed to start server:', error);
    process.exit(1);
  }
};

const gracefulShutdown = async () => {
  logger.info('Received shutdown signal, graceful shutdown...');

  try {
    aggregationService.stop();
    await adapterFactory.disconnectAll();
    process.exit(0);
  } catch (error) {
    logger.error('Error during shutdown:', error);
    process.exit(1);
  }
};

process.on('SIGTERM', gracefulShutdown);
process.on('SIGINT', gracefulShutdown);
process.on('uncaughtException', (err) => {
  logger.error('Uncaught Exception:', err);
  process.exit(1);
});
process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

startServer();

module.exports = app;
