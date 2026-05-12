const Redis = require('ioredis');

const redis = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: process.env.REDIS_PORT || 6379,
  password: process.env.REDIS_PASSWORD || undefined,
  db: process.env.REDIS_DB || 0,
  retryStrategy: (times) => {
    const delay = Math.min(times * 50, 2000);
    return delay;
  }
});

redis.on('connect', () => {
  console.log('Redis connected');
});

redis.on('error', (err) => {
  console.error('Redis connection error:', err.message);
});

const CACHE_TTL = {
  SHORT: 60,
  MEDIUM: 300,
  LONG: 3600,
  POPULAR_SONGS: 1800
};

async function getOrSet(key, fetchFn, ttl = CACHE_TTL.MEDIUM) {
  try {
    const cached = await redis.get(key);
    if (cached) {
      return JSON.parse(cached);
    }
    
    const data = await fetchFn();
    if (data !== undefined && data !== null) {
      await redis.set(key, JSON.stringify(data), 'EX', ttl);
    }
    return data;
  } catch (error) {
    console.error('Redis cache error:', error);
    return await fetchFn();
  }
}

async function invalidate(key) {
  try {
    await redis.del(key);
  } catch (error) {
    console.error('Redis invalidate error:', error);
  }
}

async function invalidatePattern(pattern) {
  try {
    const keys = await redis.keys(pattern);
    if (keys.length > 0) {
      await redis.del(...keys);
    }
  } catch (error) {
    console.error('Redis invalidate pattern error:', error);
  }
}

async function incrementPlayCount(songId) {
  try {
    const key = 'song:play_count:' + songId;
    await redis.incr(key);
    await redis.expire(key, 86400);
  } catch (error) {
    console.error('Redis increment play count error:', error);
  }
}

async function getPlayCount(songId) {
  try {
    const count = await redis.get('song:play_count:' + songId);
    return count ? parseInt(count, 10) : 0;
  } catch (error) {
    console.error('Redis get play count error:', error);
    return 0;
  }
}

module.exports = {
  redis,
  CACHE_TTL,
  getOrSet,
  invalidate,
  invalidatePattern,
  incrementPlayCount,
  getPlayCount
};
