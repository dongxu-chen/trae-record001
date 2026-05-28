package com.dbpool.optimizer.model;

public enum PoolType {
    HIKARICP("HikariCP", "com.zaxxer.hikari.HikariDataSource"),
    DRUID("Druid", "com.alibaba.druid.pool.DruidDataSource"),
    TOMCAT_JDBC("Tomcat JDBC", "org.apache.tomcat.jdbc.pool.DataSource");

    private final String displayName;
    private final String className;

    PoolType(String displayName, String className) {
        this.displayName = displayName;
        this.className = className;
    }

    public String getDisplayName() {
        return displayName;
    }

    public String getClassName() {
        return className;
    }
}
