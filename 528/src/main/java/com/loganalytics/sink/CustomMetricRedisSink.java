package com.loganalytics.sink;

import com.loganalytics.config.FlinkConfig;
import com.loganalytics.model.CustomMetric;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.sink.RichSinkFunction;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;

public class CustomMetricRedisSink extends RichSinkFunction<CustomMetric> {

    private final FlinkConfig config;
    private transient JedisPool jedisPool;
    private transient ObjectMapper objectMapper;

    public CustomMetricRedisSink(FlinkConfig config) {
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
    public void invoke(CustomMetric metric, Context context) throws Exception {
        try (Jedis jedis = jedisPool.getResource()) {
            String key = String.format("custom_metric:%s:%s:%s",
                    metric.getMetricName(), metric.getDimension(), metric.getValue());
            String value = objectMapper.writeValueAsString(metric);
            jedis.setex(key, 3600, value);

            String latestKey = String.format("custom_metric_latest:%s:%s",
                    metric.getMetricName(), metric.getDimension());
            jedis.setex(latestKey, 3600, String.valueOf(metric.getResult()));
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
