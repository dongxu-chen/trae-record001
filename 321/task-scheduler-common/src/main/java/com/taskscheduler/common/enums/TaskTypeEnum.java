package com.taskscheduler.common.enums;

import lombok.Getter;

@Getter
public enum TaskTypeEnum {

    CRON(1, "Cron定时任务"),
    DAG(2, "DAG依赖任务");

    private final Integer code;
    private final String desc;

    TaskTypeEnum(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public static TaskTypeEnum getByCode(Integer code) {
        if (code == null) {
            return null;
        }
        for (TaskTypeEnum item : values()) {
            if (item.getCode().equals(code)) {
                return item;
            }
        }
        return null;
    }
}
