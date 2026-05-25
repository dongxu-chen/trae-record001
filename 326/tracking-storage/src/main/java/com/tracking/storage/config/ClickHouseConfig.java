package com.tracking.storage.config;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import javax.sql.DataSource;

@Data
@Configuration
@ConfigurationProperties(prefix = "clickhouse")
public class ClickHouseConfig {

    private String host = "localhost";
    private int port = 8123;
    private String database = "tracking";
    private String username = "default";
    private String password = "";
    private int maxPoolSize = 10;
    private int minIdle = 2;
    private long connectionTimeout = 30000;
    private long idleTimeout = 600000;
    private long maxLifetime = 1800000;

    @Bean
    public DataSource clickHouseDataSource() {
        HikariConfig config = new HikariConfig();
        String jdbcUrl = String.format("jdbc:clickhouse://%s:%d/%s", host, port, database);
        config.setJdbcUrl(jdbcUrl);
        config.setUsername(username);
        config.setPassword(password);
        config.setDriverClassName("com.clickhouse.jdbc.ClickHouseDriver");
        config.setMaximumPoolSize(maxPoolSize);
        config.setMinimumIdle(minIdle);
        config.setConnectionTimeout(connectionTimeout);
        config.setIdleTimeout(idleTimeout);
        config.setMaxLifetime(maxLifetime);
        config.setConnectionTestQuery("SELECT 1");
        return new HikariDataSource(config);
    }

    public String getJdbcUrl() {
        return String.format("jdbc:clickhouse://%s:%d/%s", host, port, database);
    }
}
