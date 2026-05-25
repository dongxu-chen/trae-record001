package com.taskscheduler.common.enums;

import lombok.Getter;

@Getter
public enum TaskPriorityEnum {

    HIGHEST(1, "最高优先级"),
    HIGH(3, "高优先级"),
    NORMAL(5, "普通优先级"),
    LOW(7, "低优先级"),
    LOWEST(10, "最低优先级");

    private final Integer code;
    private final String desc;

    TaskPriorityEnum(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public static TaskPriorityEnum getByCode(Integer code) {
        if (code == null) {
            return NORMAL;
        }
        for (TaskPriorityEnum e : values()) {
            if (e.getCode().equals(code)) {
                return e;
            }
        }
        return NORMAL;
    }

    public static boolean isValid(Integer code) {
        return code != null && code >= 1 && code <= 10;
    }
}
