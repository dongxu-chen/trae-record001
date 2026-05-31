package com.datacheck.config;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

import javax.sql.DataSource;

@Configuration
public class DataSourceConfig {

    @Bean(name = "sourceMysqlConfig")
    @ConfigurationProperties(prefix = "datasource.mysql.source")
    public HikariConfig sourceMysqlConfig() {
        return new HikariConfig();
    }

    @Bean(name = "sourceMysqlDataSource")
    public DataSource sourceMysqlDataSource(@Qualifier("sourceMysqlConfig") HikariConfig config) {
        return new HikariDataSource(config);
    }

    @Bean(name = "targetMysqlConfig")
    @ConfigurationProperties(prefix = "datasource.mysql.target")
    public HikariConfig targetMysqlConfig() {
        return new HikariConfig();
    }

    @Bean(name = "targetMysqlDataSource")
    @Primary
    public DataSource targetMysqlDataSource(@Qualifier("targetMysqlConfig") HikariConfig config) {
        return new HikariDataSource(config);
    }
}
