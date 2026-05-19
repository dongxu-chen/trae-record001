import Redis from 'ioredis'

const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379', {
  maxRetriesPerRequest: 3,
  enableReadyCheck: false,
  retryDelayOnFailover: 100
})

redis.on('error', (err) => {
  console.error('Redis connection error:', err)
})

redis.on('connect', () => {
  console.log('Redis connected successfully')
})

export default redis

// 缓存工具函数
export const cache = {
  async get<T>(key: string): Promise<T | null> {
    try {
      const data = await redis.get(key)
      return data ? JSON.parse(data) : null
    } catch (error) {
      console.error(`Cache get error for key ${key}:`, error)
      return null
    }
  },

  async set(key: string, value: unknown, ttlSeconds: number = 300): Promise<void> {
    try {
      await redis.setex(key, ttlSeconds, JSON.stringify(value))
    } catch (error) {
      console.error(`Cache set error for key ${key}:`, error)
    }
  },

  async del(key: string): Promise<void> {
    try {
      await redis.del(key)
    } catch (error) {
      console.error(`Cache delete error for key ${key}:`, error)
    }
  },

  async delPattern(pattern: string): Promise<void> {
    try {
      const keys = await redis.keys(pattern)
      if (keys.length > 0) {
        await redis.del(...keys)
      }
    } catch (error) {
      console.error(`Cache delete pattern error for ${pattern}:`, error)
    }
  }
}

// 缓存键常量
export const CACHE_KEYS = {
  HOT_SNIPPETS: 'snippets:hot',
  SNIPPET_DETAIL: (id: string) => `snippet:${id}`,
  LANGUAGES: 'snippets:languages',
  USER_SNIPPETS: (userId: string) => `user:${userId}:snippets`
} as const
