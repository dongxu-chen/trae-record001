package com.datasync.common.enums;

import lombok.Getter;

@Getter
public enum OperationType {
    INSERT(1, "INSERT"),
    UPDATE(2, "UPDATE"),
    DELETE(3, "DELETE"),
    DDL(4, "DDL");

    private final int code;
    private final String name;

    OperationType(int code, String name) {
        this.code = code;
        this.name = name;
    }

    public static OperationType fromCode(int code) {
        for (OperationType type : values()) {
            if (type.code == code) {
                return type;
            }
        }
        throw new IllegalArgumentException("Unknown operation type code: " + code);
    }

    public static OperationType fromName(String name) {
        for (OperationType type : values()) {
            if (type.name.equalsIgnoreCase(name)) {
                return type;
            }
        }
        throw new IllegalArgumentException("Unknown operation type name: " + name);
    }
}
