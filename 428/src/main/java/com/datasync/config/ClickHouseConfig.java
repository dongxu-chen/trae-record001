package com.datasync.config;

import com.clickhouse.jdbc.ClickHouseDataSource;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;

import javax.sql.DataSource;
import java.sql.SQLException;
import java.util.Properties;

@Configuration
public class ClickHouseDataSourceConfig {

    private final SyncConfig syncConfig;

    public ClickHouseDataSourceConfig(SyncConfig syncConfig) {
        this.syncConfig = syncConfig;
    }

    @Bean(name = "clickHouseDataSource")
    public DataSource clickHouseDataSource() throws SQLException {
        SyncConfig.ClickHouseConfig chConfig = syncConfig.getClickhouse();
        SyncConfig.ConnectionPoolConfig poolConfig = chConfig.getConnectionPool();

        Properties properties = new Properties();
        properties.setProperty("user", chConfig.getUsername());
        properties.setProperty("password", chConfig.getPassword());
        properties.setProperty("database", chConfig.getDatabase());

        ClickHouseDataSource clickHouseDataSource = new ClickHouseDataSource(chConfig.getUrl(), properties);

        HikariConfig hikariConfig = new HikariConfig();
        hikariConfig.setDataSource(clickHouseDataSource);
        hikariConfig.setMaximumPoolSize(poolConfig.getMaximumPoolSize());
        hikariConfig.setMinimumIdle(poolConfig.getMinimumIdle());
        hikariConfig.setConnectionTimeout(poolConfig.getConnectionTimeout());
        hikariConfig.setIdleTimeout(poolConfig.getIdleTimeout());
        hikariConfig.setPoolName("ClickHouse-Pool");

        return new HikariDataSource(hikariConfig);
    }

    @Bean(name = "clickHouseJdbcTemplate")
    public JdbcTemplate clickHouseJdbcTemplate() throws SQLException {
        return new JdbcTemplate(clickHouseDataSource());
    }
}
