package com.distid.config;

import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.apache.curator.framework.CuratorFramework;

public class HealthCheckConfig {

    public static class ZookeeperHealthIndicator implements HealthIndicator {
        private final CuratorFramework curator;

        public ZookeeperHealthIndicator(CuratorFramework curator) {
            this.curator = curator;
        }

        @Override
        public Health health() {
            try {
                if (curator.getZookeeperClient().isConnected()) {
                    return Health.up().withDetail("connection", "connected").build();
                }
                return Health.down().withDetail("connection", "disconnected").build();
            } catch (Exception e) {
                return Health.down(e).build();
            }
        }
    }

    public static class RedisHealthIndicator implements HealthIndicator {
        private final RedisConnectionFactory connectionFactory;

        public RedisHealthIndicator(RedisConnectionFactory connectionFactory) {
            this.connectionFactory = connectionFactory;
        }

        @Override
        public Health health() {
            try {
                connectionFactory.getConnection().ping();
                return Health.up().withDetail("connection", "connected").build();
            } catch (Exception e) {
                return Health.down(e).withDetail("connection", "disconnected").build();
            }
        }
    }
}
