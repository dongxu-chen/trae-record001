package com.loganalytics.sink;

import com.loganalytics.config.FlinkConfig;
import com.loganalytics.model.TrafficForecast;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.sink.RichSinkFunction;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;

public class ForecastRedisSink extends RichSinkFunction<TrafficForecast> {

    private final FlinkConfig config;
    private transient JedisPool jedisPool;
    private transient ObjectMapper objectMapper;

    public ForecastRedisSink(FlinkConfig config) {
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
    public void invoke(TrafficForecast forecast, Context context) throws Exception {
        try (Jedis jedis = jedisPool.getResource()) {
            String key = String.format("forecast:%s:%s", forecast.getDimension(), forecast.getValue());
            String value = objectMapper.writeValueAsString(forecast);
            jedis.setex(key, 3600, value);

            String predictedKey = String.format("predicted_qps:%s:%s", forecast.getDimension(), forecast.getValue());
            jedis.setex(predictedKey, 3600, String.valueOf(forecast.getPredictedQps()));

            String predictedNextKey = String.format("predicted_qps_next:%s:%s", forecast.getDimension(), forecast.getValue());
            jedis.setex(predictedNextKey, 3600, String.valueOf(forecast.getPredictedQpsNext()));

            String trendKey = String.format("trend:%s:%s", forecast.getDimension(), forecast.getValue());
            String trendValue = String.format("direction=%s,slope=%.6f,intercept=%.2f,confidence=%.4f",
                    forecast.getTrendDirection(), forecast.getTrendSlope(),
                    forecast.getTrendIntercept(), forecast.getConfidence());
            jedis.setex(trendKey, 3600, trendValue);

            String maKey = String.format("moving_avg:%s:%s", forecast.getDimension(), forecast.getValue());
            String maValue = String.format("ma5=%.2f,ma10=%.2f", forecast.getMovingAvg5(), forecast.getMovingAvg10());
            jedis.setex(maKey, 3600, maValue);

            String deviationKey = String.format("forecast_deviation:%s:%s", forecast.getDimension(), forecast.getValue());
            jedis.setex(deviationKey, 3600, String.valueOf(forecast.getDeviationFromPredicted()));
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
