package com.pushcenter.enums;

import lombok.Getter;

@Getter
public enum MessagePriority {

    HIGH("high", 3, "高优先级"),
    NORMAL("normal", 2, "普通优先级"),
    LOW("low", 1, "低优先级");

    private final String code;
    private final int level;
    private final String name;

    MessagePriority(String code, int level, String name) {
        this.code = code;
        this.level = level;
        this.name = name;
    }

    public static MessagePriority fromCode(String code) {
        for (MessagePriority priority : values()) {
            if (priority.getCode().equals(code)) {
                return priority;
            }
        }
        return NORMAL;
    }

    public boolean isHigherThan(MessagePriority other) {
        return this.level > other.level;
    }
}
