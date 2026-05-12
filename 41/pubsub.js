const { RedisPubSub } = require('graphql-subscriptions');
const Redis = require('ioredis');

const NEW_BOOK_ADDED = 'NEW_BOOK_ADDED';

const pub = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: process.env.REDIS_PORT || 6379,
  retryStrategy: (times) => {
    const delay = Math.min(times * 50, 2000);
    return delay;
  }
});

const sub = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: process.env.REDIS_PORT || 6379,
  retryStrategy: (times) => {
    const delay = Math.min(times * 50, 2000);
    return delay;
  }
});

const pubsub = new RedisPubSub({
  publisher: pub,
  subscriber: sub
});

async function closePubSub() {
  try {
    await pub.quit();
    await sub.quit();
    console.log('Redis connections closed');
  } catch (error) {
    console.error('Error closing Redis connections:', error);
  }
}

module.exports = {
  pubsub,
  NEW_BOOK_ADDED,
  closePubSub
};
