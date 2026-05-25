package com.tracking.flink.function;

import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.TrackEvent;
import com.tracking.common.util.IdGenerator;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;
import org.apache.flink.util.Collector;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;

public class UserIdMappingSinkFunction extends KeyedProcessFunction<String, TrackEvent, TrackEvent> {

    private static final Logger LOG = LoggerFactory.getLogger(UserIdMappingSinkFunction.class);

    private final String redisHost;
    private final int redisPort;
    private final String redisPassword;
    private transient JedisPool jedisPool;

    public UserIdMappingSinkFunction(String redisHost, int redisPort, String redisPassword) {
        this.redisHost = redisHost;
        this.redisPort = redisPort;
        this.redisPassword = redisPassword;
    }

    @Override
    public void open(Configuration parameters) {
        JedisPoolConfig poolConfig = new JedisPoolConfig();
        poolConfig.setMaxTotal(64);
        poolConfig.setMaxIdle(32);
        poolConfig.setMinIdle(8);
        if (redisPassword != null && !redisPassword.isEmpty()) {
            jedisPool = new JedisPool(poolConfig, redisHost, redisPort, 2000, redisPassword);
        } else {
            jedisPool = new JedisPool(poolConfig, redisHost, redisPort, 2000);
        }
    }

    @Override
    public void processElement(TrackEvent event, Context context, Collector<TrackEvent> collector) {
        try (Jedis jedis = jedisPool.getResource()) {
            if (event.getUserId() != null && !IdGenerator.isAnonymousId(event.getUserId())) {
                if (event.getAnonymousId() != null) {
                    String key = TrackingConstants.REDIS_KEY_USER_MAPPING + event.getAnonymousId();
                    jedis.setex(key, TrackingConstants.REDIS_EXPIRE_HOURS * 3600, event.getUserId());
                    LOG.debug("Stored user mapping: {} -> {}", event.getAnonymousId(), event.getUserId());
                }

                if (event.getDeviceId() != null) {
                    String key = TrackingConstants.REDIS_KEY_USER_MAPPING + "device:" + event.getDeviceId();
                    jedis.setex(key, TrackingConstants.REDIS_EXPIRE_HOURS * 3600, event.getUserId());
                }
            }
        } catch (Exception e) {
            LOG.warn("Failed to store user mapping in Redis", e);
        }
    }

    @Override
    public void close() {
        if (jedisPool != null) {
            jedisPool.close();
        }
    }
}
