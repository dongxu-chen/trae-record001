package com.tracing.sampling.store;

import com.google.gson.Gson;
import com.tracing.sampling.config.RedisProperties;
import com.tracing.sampling.model.SamplingDecisionRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.Pipeline;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class RedisSamplingConfigStore implements SamplingConfigStore {

    private static final Logger logger = LoggerFactory.getLogger(RedisSamplingConfigStore.class);

    private static final String LATENCY_STATS_KEY = "latency:stats:";
    private static final String ENDPOINT_MULTIPLIER_KEY = "endpoint:multiplier:";
    private static final String SAMPLING_DECISIONS_KEY = "decisions:history";
    private static final String CURRENT_RATE_KEY = "config:current_rate";
    private static final String TARGET_RATE_KEY = "config:target_rate";
    private static final String GLOBAL_MULTIPLIER_KEY = "config:global_multiplier";

    private final JedisPool jedisPool;
    private final RedisProperties redisProperties;
    private final Gson gson;
    
    private final Map<String, CachedLatencyStats> latencyCache = new ConcurrentHashMap<>();
    private final Map<String, Double> multiplierCache = new ConcurrentHashMap<>();
    private volatile long lastCacheUpdate = 0;
    private static final long CACHE_TTL_MS = 5000;

    public RedisSamplingConfigStore(JedisPool jedisPool, RedisProperties redisProperties) {
        this.jedisPool = jedisPool;
        this.redisProperties = redisProperties;
        this.gson = new Gson();
    }

    private String buildKey(String suffix) {
        return redisProperties.getKeyPrefix() + suffix;
    }

    @Override
    public long getAverageLatency(String endpointKey) {
        if (endpointKey == null) {
            return 0;
        }
        
        long now = System.currentTimeMillis();
        CachedLatencyStats cached = latencyCache.get(endpointKey);
        if (cached != null && (now - cached.timestamp) < CACHE_TTL_MS) {
            return cached.averageLatency;
        }

        try (Jedis jedis = jedisPool.getResource()) {
            String key = buildKey(LATENCY_STATS_KEY + endpointKey);
            String totalLatency = jedis.hget(key, "totalLatency");
            String count = jedis.hget(key, "count");
            
            if (totalLatency != null && count != null) {
                long total = Long.parseLong(totalLatency);
                long cnt = Long.parseLong(count);
                long avg = cnt > 0 ? total / cnt : 0;
                
                latencyCache.put(endpointKey, new CachedLatencyStats(avg, now));
                return avg;
            }
        } catch (Exception e) {
            logger.warn("Failed to get latency stats for {}: {}", endpointKey, e.getMessage());
        }
        
        return 0;
    }

    @Override
    public void updateLatencyStats(String endpointKey, long latency) {
        if (endpointKey == null) {
            return;
        }

        try (Jedis jedis = jedisPool.getResource()) {
            String key = buildKey(LATENCY_STATS_KEY + endpointKey);
            
            Pipeline pipeline = jedis.pipelined();
            pipeline.hincrBy(key, "totalLatency", latency);
            pipeline.hincrBy(key, "count", 1);
            pipeline.expire(key, 3600 * 24);
            pipeline.sync();
            
            latencyCache.remove(endpointKey);
        } catch (Exception e) {
            logger.warn("Failed to update latency stats for {}: {}", endpointKey, e.getMessage());
        }
    }

    @Override
    public double getEndpointSampleRateMultiplier(String endpointKey) {
        if (endpointKey == null) {
            return 1.0;
        }
        
        Double cached = multiplierCache.get(endpointKey);
        if (cached != null) {
            return cached;
        }

        try (Jedis jedis = jedisPool.getResource()) {
            String key = buildKey(ENDPOINT_MULTIPLIER_KEY + endpointKey);
            String value = jedis.get(key);
            
            if (value != null) {
                double multiplier = Double.parseDouble(value);
                multiplierCache.put(endpointKey, multiplier);
                return multiplier;
            }
        } catch (Exception e) {
            logger.warn("Failed to get endpoint multiplier for {}: {}", endpointKey, e.getMessage());
        }
        
        return 1.0;
    }

    @Override
    public void setEndpointSampleRateMultiplier(String endpointKey, double multiplier) {
        if (endpointKey == null) {
            return;
        }

        try (Jedis jedis = jedisPool.getResource()) {
            String key = buildKey(ENDPOINT_MULTIPLIER_KEY + endpointKey);
            jedis.setex(key, 3600 * 24 * 7, String.valueOf(multiplier));
            multiplierCache.put(endpointKey, multiplier);
        } catch (Exception e) {
            logger.warn("Failed to set endpoint multiplier for {}: {}", endpointKey, e.getMessage());
        }
    }

    @Override
    public void recordSamplingDecision(SamplingDecisionRecord record) {
        try (Jedis jedis = jedisPool.getResource()) {
            String key = buildKey(SAMPLING_DECISIONS_KEY);
            String value = gson.toJson(record);
            
            Pipeline pipeline = jedis.pipelined();
            pipeline.lpush(key, value);
            pipeline.ltrim(key, 0, 9999);
            pipeline.expire(key, 3600 * 24);
            pipeline.sync();
        } catch (Exception e) {
            logger.debug("Failed to record sampling decision: {}", e.getMessage());
        }
    }

    @Override
    public double getCurrentSampleRate() {
        try (Jedis jedis = jedisPool.getResource()) {
            String key = buildKey(CURRENT_RATE_KEY);
            String value = jedis.get(key);
            if (value != null) {
                return Double.parseDouble(value);
            }
        } catch (Exception e) {
            logger.warn("Failed to get current sample rate: {}", e.getMessage());
        }
        return 0.1;
    }

    @Override
    public void updateCurrentSampleRate(double rate) {
        try (Jedis jedis = jedisPool.getResource()) {
            String key = buildKey(CURRENT_RATE_KEY);
            jedis.set(key, String.valueOf(rate));
        } catch (Exception e) {
            logger.warn("Failed to update current sample rate: {}", e.getMessage());
        }
    }

    @Override
    public double getGlobalTargetSampleRate() {
        try (Jedis jedis = jedisPool.getResource()) {
            String key = buildKey(TARGET_RATE_KEY);
            String value = jedis.get(key);
            if (value != null) {
                return Double.parseDouble(value);
            }
        } catch (Exception e) {
            logger.warn("Failed to get global target sample rate: {}", e.getMessage());
        }
        return 0.1;
    }

    @Override
    public void setGlobalTargetSampleRate(double rate) {
        try (Jedis jedis = jedisPool.getResource()) {
            String key = buildKey(TARGET_RATE_KEY);
            jedis.set(key, String.valueOf(rate));
        } catch (Exception e) {
            logger.warn("Failed to set global target sample rate: {}", e.getMessage());
        }
    }

    public Map<String, Object> getLatencyStatsMap(String endpointKey) {
        Map<String, Object> result = new HashMap<>();
        
        try (Jedis jedis = jedisPool.getResource()) {
            String key = buildKey(LATENCY_STATS_KEY + endpointKey);
            Map<String, String> stats = jedis.hgetAll(key);
            
            if (!stats.isEmpty()) {
                long totalLatency = Long.parseLong(stats.getOrDefault("totalLatency", "0"));
                long count = Long.parseLong(stats.getOrDefault("count", "0"));
                result.put("endpoint", endpointKey);
                result.put("totalLatency", totalLatency);
                result.put("count", count);
                result.put("averageLatency", count > 0 ? totalLatency / count : 0);
            }
        } catch (Exception e) {
            logger.warn("Failed to get latency stats map for {}: {}", endpointKey, e.getMessage());
        }
        
        return result;
    }

    public void clearCache() {
        latencyCache.clear();
        multiplierCache.clear();
        lastCacheUpdate = System.currentTimeMillis();
    }

    private static class CachedLatencyStats {
        final long averageLatency;
        final long timestamp;

        CachedLatencyStats(long averageLatency, long timestamp) {
            this.averageLatency = averageLatency;
            this.timestamp = timestamp;
        }
    }
}
