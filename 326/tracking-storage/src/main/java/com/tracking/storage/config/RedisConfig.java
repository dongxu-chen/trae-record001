package com.tracking.storage.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;

@Data
@Configuration
@ConfigurationProperties(prefix = "redis")
public class RedisConfig {

    private String host = "localhost";
    private int port = 6379;
    private String password = "";
    private int database = 0;
    private int timeout = 2000;
    private int maxTotal = 128;
    private int maxIdle = 64;
    private int minIdle = 16;

    @Bean
    public JedisPool jedisPool() {
        JedisPoolConfig poolConfig = new JedisPoolConfig();
        poolConfig.setMaxTotal(maxTotal);
        poolConfig.setMaxIdle(maxIdle);
        poolConfig.setMinIdle(minIdle);
        poolConfig.setTestOnBorrow(true);
        poolConfig.setTestOnReturn(true);
        poolConfig.setTestWhileIdle(true);

        if (password != null && !password.isEmpty()) {
            return new JedisPool(poolConfig, host, port, timeout, password, database);
        } else {
            return new JedisPool(poolConfig, host, port, timeout, null, database);
        }
    }
}
