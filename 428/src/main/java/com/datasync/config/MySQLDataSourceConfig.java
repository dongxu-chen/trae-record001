package com.datasync.config;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;

import javax.sql.DataSource;

@Configuration
public class MySQLDataSourceConfig {

    private final SyncConfig syncConfig;

    public MySQLDataSourceConfig(SyncConfig syncConfig) {
        this.syncConfig = syncConfig;
    }

    @Bean(name = "mysqlDataSource")
    public DataSource mysqlDataSource() {
        SyncConfig.MySQLConfig mysqlConfig = syncConfig.getMysql();

        HikariConfig config = new HikariConfig();
        config.setJdbcUrl(mysqlConfig.getUrl());
        config.setUsername(mysqlConfig.getUsername());
        config.setPassword(mysqlConfig.getPassword());
        config.setMaximumPoolSize(10);
        config.setMinimumIdle(2);
        config.setConnectionTimeout(30000);
        config.setIdleTimeout(60000);
        config.setPoolName("MySQL-Pool");
        config.addDataSourceProperty("useSSL", "false");
        config.addDataSourceProperty("serverTimezone", "Asia/Shanghai");
        config.addDataSourceProperty("useUnicode", "true");
        config.addDataSourceProperty("characterEncoding", "UTF-8");

        return new HikariDataSource(config);
    }

    @Bean(name = "mysqlJdbcTemplate")
    public JdbcTemplate mysqlJdbcTemplate() {
        return new JdbcTemplate(mysqlDataSource());
    }
}
