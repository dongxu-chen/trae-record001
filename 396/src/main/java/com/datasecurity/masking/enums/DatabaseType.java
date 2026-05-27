package com.datasecurity.masking.enums;

import lombok.Getter;

@Getter
public enum DatabaseType {

    MYSQL("MySQL", "com.mysql.cj.jdbc.Driver"),

    POSTGRESQL("PostgreSQL", "org.postgresql.Driver"),

    MONGODB("MongoDB", null);

    private final String name;

    private final String driverClass;

    DatabaseType(String name, String driverClass) {
        this.name = name;
        this.driverClass = driverClass;
    }
}
