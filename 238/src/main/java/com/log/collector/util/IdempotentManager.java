package com.log.collector.util;

import com.google.common.hash.Hashing;
import org.apache.flume.Event;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;

import java.nio.charset.StandardCharsets;
import java.util.Properties;
import java.util.concurrent.TimeUnit;

public class IdempotentManager {

    private static final Logger logger = LoggerFactory.getLogger(IdempotentManager.class);

    private static volatile IdempotentManager instance;
    private JedisPool jedisPool;
    private final String idempotentKeyPrefix;
    private final long ttlSeconds;
    private final boolean enabled;

    private IdempotentManager(Properties config) {
        this.enabled = Boolean.parseBoolean(config.getProperty("redis.idempotent.enabled", "true"));
        this.idempotentKeyPrefix = config.getProperty("redis.key.prefix", "log:idempotent:");
        this.ttlSeconds = Long.parseLong(config.getProperty("redis.ttl.seconds", "86400"));

        if (enabled) {
            initRedisPool(config);
        }
    }

    public static IdempotentManager getInstance(Properties config) {
        if (instance == null) {
            synchronized (IdempotentManager.class) {
                if (instance == null) {
                    instance = new IdempotentManager(config);
                }
            }
        }
        return instance;
    }

    private void initRedisPool(Properties config) {
        try {
            String host = config.getProperty("redis.host", "localhost");
            int port = Integer.parseInt(config.getProperty("redis.port", "6379"));
            String password = config.getProperty("redis.password", "");
            int database = Integer.parseInt(config.getProperty("redis.database", "0"));
            int maxTotal = Integer.parseInt(config.getProperty("redis.pool.maxTotal", "20"));
            int maxIdle = Integer.parseInt(config.getProperty("redis.pool.maxIdle", "10"));

            JedisPoolConfig poolConfig = new JedisPoolConfig();
            poolConfig.setMaxTotal(maxTotal);
            poolConfig.setMaxIdle(maxIdle);
            poolConfig.setMinIdle(5);
            poolConfig.setTestOnBorrow(true);
            poolConfig.setTestOnReturn(true);

            if (password != null && !password.isEmpty()) {
                jedisPool = new JedisPool(poolConfig, host, port, 3000, password, database);
            } else {
                jedisPool = new JedisPool(poolConfig, host, port, 3000, null, database);
            }

            logger.info("Redis idempotent pool initialized - host: {}, port: {}", host, port);
        } catch (Exception e) {
            logger.error("Failed to initialize Redis pool", e);
            throw new RuntimeException("Redis pool initialization failed", e);
        }
    }

    public String generateIdempotentId(Event event) {
        String topic = event.getHeaders().get("topic");
        String partition = event.getHeaders().get("partition");
        String offset = event.getHeaders().get("offset");

        if (topic == null || partition == null || offset == null) {
            String bodyHash = Hashing.murmur3_128()
                    .hashBytes(event.getBody())
                    .toString();
            return "body:" + bodyHash;
        }

        return String.format("%s:%s:%s", topic, partition, offset);
    }

    public boolean isProcessed(String idempotentId) {
        if (!enabled) {
            return false;
        }

        try (Jedis jedis = jedisPool.getResource()) {
            String key = idempotentKeyPrefix + idempotentId;
            return jedis.exists(key);
        } catch (Exception e) {
            logger.warn("Redis check failed, proceeding without idempotent check: {}", e.getMessage());
            return false;
        }
    }

    public boolean markProcessed(String idempotentId) {
        if (!enabled) {
            return true;
        }

        try (Jedis jedis = jedisPool.getResource()) {
            String key = idempotentKeyPrefix + idempotentId;
            String result = jedis.set(key, "1", "NX", "EX", ttlSeconds);
            return "OK".equals(result);
        } catch (Exception e) {
            logger.warn("Redis mark failed, proceeding: {}", e.getMessage());
            return true;
        }
    }

    public boolean tryMarkProcessed(String idempotentId) {
        if (!enabled) {
            return true;
        }

        try (Jedis jedis = jedisPool.getResource()) {
            String key = idempotentKeyPrefix + idempotentId;
            Long result = jedis.setnx(key, "1");
            if (result == 1) {
                jedis.expire(key, ttlSeconds);
                return true;
            }
            return false;
        } catch (Exception e) {
            logger.warn("Redis setnx failed, proceeding: {}", e.getMessage());
            return true;
        }
    }

    public void markProcessedAsync(String idempotentId) {
        if (!enabled) {
            return;
        }

        try (Jedis jedis = jedisPool.getResource()) {
            String key = idempotentKeyPrefix + idempotentId;
            jedis.setex(key, ttlSeconds, "1");
        } catch (Exception e) {
            logger.warn("Async mark failed: {}", e.getMessage());
        }
    }

    public void close() {
        if (jedisPool != null && !jedisPool.isClosed()) {
            jedisPool.close();
            logger.info("Redis pool closed");
        }
    }

    public boolean isEnabled() {
        return enabled;
    }
}
