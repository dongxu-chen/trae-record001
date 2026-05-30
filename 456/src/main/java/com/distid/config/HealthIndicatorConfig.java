package com.distid.config;

import com.distid.config.HealthCheckConfig.RedisHealthIndicator;
import com.distid.config.HealthCheckConfig.ZookeeperHealthIndicator;
import org.apache.curator.framework.CuratorFramework;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;

@Configuration
public class HealthIndicatorConfig {

    @Bean
    public HealthIndicator zookeeperHealthIndicator(CuratorFramework curator) {
        return new ZookeeperHealthIndicator(curator);
    }

    @Bean
    public HealthIndicator redisHealthIndicator(RedisConnectionFactory connectionFactory) {
        return new RedisHealthIndicator(connectionFactory);
    }
}
