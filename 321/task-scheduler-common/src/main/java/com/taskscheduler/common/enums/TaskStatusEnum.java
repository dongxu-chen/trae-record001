package com.taskscheduler.common.enums;

import lombok.Getter;

@Getter
public enum TaskStatusEnum {

    STOPPED(0, "停止"),
    RUNNING(1, "运行中");

    private final Integer code;
    private final String desc;

    TaskStatusEnum(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}
