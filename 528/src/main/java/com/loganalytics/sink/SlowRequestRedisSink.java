package com.loganalytics.sink;

import com.loganalytics.config.FlinkConfig;
import com.loganalytics.model.SlowRequestEvent;
import com.loganalytics.model.TraceSpan;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.sink.RichSinkFunction;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;

public class SlowRequestRedisSink extends RichSinkFunction<SlowRequestEvent> {

    private final FlinkConfig config;
    private transient JedisPool jedisPool;
    private transient ObjectMapper objectMapper;

    public SlowRequestRedisSink(FlinkConfig config) {
        this.config = config;
    }

    @Override
    public void open(Configuration parameters) throws Exception {
        super.open(parameters);
        JedisPoolConfig poolConfig = new JedisPoolConfig();
        poolConfig.setMaxTotal(64);
        poolConfig.setMaxIdle(64);
        poolConfig.setMinIdle(8);
        this.jedisPool = new JedisPool(poolConfig, config.getRedisHost(), config.getRedisPort());
        this.objectMapper = new ObjectMapper();
    }

    @Override
    public void invoke(SlowRequestEvent event, Context context) throws Exception {
        try (Jedis jedis = jedisPool.getResource()) {
            String key = String.format("slow_request:%s", event.getTraceId());
            String value = objectMapper.writeValueAsString(event);
            jedis.setex(key, 3600, value);

            String apiSlowKey = String.format("slow_requests:api:%s", event.getPath());
            jedis.lpush(apiSlowKey, event.getTraceId());
            jedis.ltrim(apiSlowKey, 0, 99);
            jedis.expire(apiSlowKey, 3600);

            String recentKey = "slow_requests:recent";
            jedis.lpush(recentKey, event.getTraceId());
            jedis.ltrim(recentKey, 0, 199);
            jedis.expire(recentKey, 3600);

            String reasonKey = String.format("slow_reason:%s", event.getSlowReason());
            jedis.incr(reasonKey);
            jedis.expire(reasonKey, 300);
        }
    }

    @Override
    public void close() throws Exception {
        super.close();
        if (jedisPool != null) {
            jedisPool.close();
        }
    }
}
