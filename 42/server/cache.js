const Redis = require('ioredis');

const redis = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: process.env.REDIS_PORT || 6379,
  password: process.env.REDIS_PASSWORD || undefined,
  db: process.env.REDIS_DB || 0,
});

const CACHE_TTL = {
  LIKES: 3600,
  COMMENTS: 3600,
  FOLLOWERS: 3600,
  FOLLOWING: 3600,
  USER_FEED: 300,
  VIDEO_STATS: 600,
};

const KEY_PREFIX = {
  USER_LIKES: 'user:likes',
  VIDEO_LIKES: 'video:likes',
  VIDEO_COMMENTS: 'video:comments',
  USER_COMMENTS: 'user:comments',
  USER_FOLLOWERS: 'user:followers',
  USER_FOLLOWING: 'user:following',
  USER_FEED: 'user:feed',
  VIDEO_STATS: 'video:stats',
};

function getKey(prefix, id) {
  return `${prefix}:${id}`;
}

async function cacheLike(userId, videoId) {
  const multi = redis.multi();
  multi.sadd(getKey(KEY_PREFIX.USER_LIKES, userId), videoId);
  multi.sadd(getKey(KEY_PREFIX.VIDEO_LIKES, videoId), userId);
  multi.expire(getKey(KEY_PREFIX.USER_LIKES, userId), CACHE_TTL.LIKES);
  multi.expire(getKey(KEY_PREFIX.VIDEO_LIKES, videoId), CACHE_TTL.LIKES);
  await multi.exec();
}

async function removeCachedLike(userId, videoId) {
  const multi = redis.multi();
  multi.srem(getKey(KEY_PREFIX.USER_LIKES, userId), videoId);
  multi.srem(getKey(KEY_PREFIX.VIDEO_LIKES, videoId), userId);
  await multi.exec();
}

async function getUserLikes(userId) {
  return redis.smembers(getKey(KEY_PREFIX.USER_LIKES, userId));
}

async function getVideoLikes(videoId) {
  return redis.smembers(getKey(KEY_PREFIX.VIDEO_LIKES, videoId));
}

async function isLiked(userId, videoId) {
  return redis.sismember(getKey(KEY_PREFIX.USER_LIKES, userId), videoId);
}

async function addComment(comment) {
  const commentKey = getKey(KEY_PREFIX.VIDEO_COMMENTS, comment.videoId);
  const userCommentKey = getKey(KEY_PREFIX.USER_COMMENTS, comment.userId);
  
  const multi = redis.multi();
  multi.rpush(commentKey, JSON.stringify(comment));
  multi.rpush(userCommentKey, JSON.stringify(comment));
  multi.expire(commentKey, CACHE_TTL.COMMENTS);
  multi.expire(userCommentKey, CACHE_TTL.COMMENTS);
  await multi.exec();
}

async function getVideoComments(videoId, limit = 50) {
  const comments = await redis.lrange(
    getKey(KEY_PREFIX.VIDEO_COMMENTS, videoId),
    -limit,
    -1
  );
  return comments.map((c) => JSON.parse(c));
}

async function cacheFollow(followerId, followingId) {
  const multi = redis.multi();
  multi.sadd(getKey(KEY_PREFIX.USER_FOLLOWERS, followingId), followerId);
  multi.sadd(getKey(KEY_PREFIX.USER_FOLLOWING, followerId), followingId);
  multi.expire(getKey(KEY_PREFIX.USER_FOLLOWERS, followingId), CACHE_TTL.FOLLOWERS);
  multi.expire(getKey(KEY_PREFIX.USER_FOLLOWING, followerId), CACHE_TTL.FOLLOWING);
  await multi.exec();
}

async function removeCachedFollow(followerId, followingId) {
  const multi = redis.multi();
  multi.srem(getKey(KEY_PREFIX.USER_FOLLOWERS, followingId), followerId);
  multi.srem(getKey(KEY_PREFIX.USER_FOLLOWING, followerId), followingId);
  await multi.exec();
}

async function getFollowers(userId) {
  return redis.smembers(getKey(KEY_PREFIX.USER_FOLLOWERS, userId));
}

async function getFollowing(userId) {
  return redis.smembers(getKey(KEY_PREFIX.USER_FOLLOWING, userId));
}

async function isFollowing(followerId, followingId) {
  return redis.sismember(getKey(KEY_PREFIX.USER_FOLLOWING, followerId), followingId);
}

async function cacheUserFeed(userId, videos, ttl = CACHE_TTL.USER_FEED) {
  const key = getKey(KEY_PREFIX.USER_FEED, userId);
  await redis.setex(key, ttl, JSON.stringify(videos));
}

async function getUserFeedFromCache(userId) {
  const key = getKey(KEY_PREFIX.USER_FEED, userId);
  const data = await redis.get(key);
  return data ? JSON.parse(data) : null;
}

async function invalidateUserFeed(userId) {
  await redis.del(getKey(KEY_PREFIX.USER_FEED, userId));
}

async function cacheVideoStats(videoId, stats, ttl = CACHE_TTL.VIDEO_STATS) {
  const key = getKey(KEY_PREFIX.VIDEO_STATS, videoId);
  await redis.setex(key, ttl, JSON.stringify(stats));
}

async function getVideoStatsFromCache(videoId) {
  const key = getKey(KEY_PREFIX.VIDEO_STATS, videoId);
  const data = await redis.get(key);
  return data ? JSON.parse(data) : null;
}

async function clearCache(pattern) {
  const keys = await redis.keys(pattern);
  if (keys.length > 0) {
    await redis.del(...keys);
  }
}

async function getStats() {
  return {
    memory: await redis.info('memory'),
    keyspace: await redis.info('keyspace'),
  };
}

module.exports = {
  redis,
  cacheLike,
  removeCachedLike,
  getUserLikes,
  getVideoLikes,
  isLiked,
  addComment,
  getVideoComments,
  cacheFollow,
  removeCachedFollow,
  getFollowers,
  getFollowing,
  isFollowing,
  cacheUserFeed,
  getUserFeedFromCache,
  invalidateUserFeed,
  cacheVideoStats,
  getVideoStatsFromCache,
  clearCache,
  getStats,
};
