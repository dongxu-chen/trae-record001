import Redis from 'ioredis';

let redisClient = null;

const getRedisClient = () => {
  if (redisClient) {
    return redisClient;
  }

  const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379';

  redisClient = new Redis(redisUrl, {
    maxRetriesPerRequest: 3,
    retryStrategy: (times) => {
      if (times > 3) {
        return null;
      }
      return Math.min(times * 200, 2000);
    },
  });

  redisClient.on('connect', () => {
    console.log('Redis connected successfully');
  });

  redisClient.on('error', (error) => {
    console.error('Redis connection error:', error);
  });

  return redisClient;
};

const TRENDING_KEY = 'gallery:trending';
const TRENDING_TTL = 300;

export const cacheTrendingImages = async (images) => {
  try {
    const client = getRedisClient();
    const data = JSON.stringify(images);
    await client.setex(TRENDING_KEY, TRENDING_TTL, data);
    return true;
  } catch (error) {
    console.error('Cache trending images error:', error);
    return false;
  }
};

export const getCachedTrendingImages = async () => {
  try {
    const client = getRedisClient();
    const data = await client.get(TRENDING_KEY);
    if (data) {
      return JSON.parse(data);
    }
    return null;
  } catch (error) {
    console.error('Get cached trending images error:', error);
    return null;
  }
};

export const invalidateTrendingCache = async () => {
  try {
    const client = getRedisClient();
    await client.del(TRENDING_KEY);
    return true;
  } catch (error) {
    console.error('Invalidate trending cache error:', error);
    return false;
  }
};

const USER_LIKES_PREFIX = 'gallery:user:likes:';
const USER_LIKES_TTL = 600;

export const cacheUserLikes = async (userId, likedImageIds) => {
  try {
    const client = getRedisClient();
    const key = USER_LIKES_PREFIX + userId;
    const data = JSON.stringify(likedImageIds);
    await client.setex(key, USER_LIKES_TTL, data);
    return true;
  } catch (error) {
    console.error('Cache user likes error:', error);
    return false;
  }
};

export const getCachedUserLikes = async (userId) => {
  try {
    const client = getRedisClient();
    const key = USER_LIKES_PREFIX + userId;
    const data = await client.get(key);
    if (data) {
      return JSON.parse(data);
    }
    return null;
  } catch (error) {
    console.error('Get cached user likes error:', error);
    return null;
  }
};

export const invalidateUserLikesCache = async (userId) => {
  try {
    const client = getRedisClient();
    const key = USER_LIKES_PREFIX + userId;
    await client.del(key);
    return true;
  } catch (error) {
    console.error('Invalidate user likes cache error:', error);
    return false;
  }
};

export default getRedisClient;
