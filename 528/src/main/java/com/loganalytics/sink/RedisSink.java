package com.loganalytics.sink;

import com.loganalytics.config.FlinkConfig;
import com.loganalytics.model.MetricsResult;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.sink.RichSinkFunction;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;

import com.fasterxml.jackson.databind.ObjectMapper;

public class RedisSink extends RichSinkFunction<MetricsResult> {

    private final FlinkConfig config;
    private transient JedisPool jedisPool;
    private transient ObjectMapper objectMapper;

    public RedisSink(FlinkConfig config) {
        this.config = config;
    }

    @Override
    public void open(Configuration parameters) throws Exception {
        super.open(parameters);
        JedisPoolConfig poolConfig = new JedisPoolConfig();
        poolConfig.setMaxTotal(128);
        poolConfig.setMaxIdle(128);
        poolConfig.setMinIdle(16);
        this.jedisPool = new JedisPool(poolConfig, config.getRedisHost(), config.getRedisPort());
        this.objectMapper = new ObjectMapper();
    }

    @Override
    public void invoke(MetricsResult metrics, Context context) throws Exception {
        try (Jedis jedis = jedisPool.getResource()) {
            String key = String.format("metrics:%s:%s", metrics.getDimension(), metrics.getValue());
            String value = objectMapper.writeValueAsString(metrics);
            jedis.setex(key, 3600, value);

            String qpsKey = String.format("qps:%s:%s", metrics.getDimension(), metrics.getValue());
            jedis.setex(qpsKey, 3600, String.valueOf(metrics.getQps()));

            String errorRateKey = String.format("error_rate:%s:%s", metrics.getDimension(), metrics.getValue());
            jedis.setex(errorRateKey, 3600, String.valueOf(metrics.getErrorRate()));

            String p50Key = String.format("latency_p50:%s:%s", metrics.getDimension(), metrics.getValue());
            jedis.setex(p50Key, 3600, String.valueOf(metrics.getP50Latency()));

            String p95Key = String.format("latency_p95:%s:%s", metrics.getDimension(), metrics.getValue());
            jedis.setex(p95Key, 3600, String.valueOf(metrics.getP95Latency()));

            String p99Key = String.format("latency_p99:%s:%s", metrics.getDimension(), metrics.getValue());
            jedis.setex(p99Key, 3600, String.valueOf(metrics.getP99Latency()));

            String p999Key = String.format("latency_p999:%s:%s", metrics.getDimension(), metrics.getValue());
            jedis.setex(p999Key, 3600, String.valueOf(metrics.getP999Latency()));

            String statsKey = String.format("stats:%s:%s", metrics.getDimension(), metrics.getValue());
            String statsValue = String.format("mean=%.4f,stddev=%.4f,min=%.4f,max=%.4f,total=%d,errors=%d",
                    metrics.getAvgLatency(), metrics.getStdDevLatency(),
                    metrics.getMinLatency(), metrics.getMaxLatency(),
                    metrics.getTotalRequests(), metrics.getErrorRequests());
            jedis.setex(statsKey, 3600, statsValue);

            String thresholdKey = String.format("thresholds:%s:%s", metrics.getDimension(), metrics.getValue());
            String thresholdValue = String.format("error_rate_mean=%.4f,error_rate_stddev=%.4f,latency_mean=%.4f,latency_stddev=%.4f,qps_mean=%.4f,qps_stddev=%.4f",
                    metrics.getErrorRateMean(), metrics.getErrorRateStdDev(),
                    metrics.getLatencyMean(), metrics.getLatencyStdDev(),
                    metrics.getQpsMean(), metrics.getQpsStdDev());
            jedis.setex(thresholdKey, 3600, thresholdValue);
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
