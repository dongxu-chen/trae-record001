package com.datasync.common.enums;

import lombok.Getter;

@Getter
public enum DatabaseType {
    MYSQL(1, "MySQL"),
    POSTGRESQL(2, "PostgreSQL");

    private final int code;
    private final String name;

    DatabaseType(int code, String name) {
        this.code = code;
        this.name = name;
    }

    public static DatabaseType fromCode(int code) {
        for (DatabaseType type : values()) {
            if (type.code == code) {
                return type;
            }
        }
        throw new IllegalArgumentException("Unknown database type code: " + code);
    }

    public static DatabaseType fromName(String name) {
        for (DatabaseType type : values()) {
            if (type.name.equalsIgnoreCase(name)) {
                return type;
            }
        }
        throw new IllegalArgumentException("Unknown database type name: " + name);
    }
}
