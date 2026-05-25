package com.taskscheduler.common.enums;

import lombok.Getter;

@Getter
public enum ExecutorStatusEnum {

    OFFLINE(0, "离线"),
    ONLINE(1, "在线");

    private final Integer code;
    private final String desc;

    ExecutorStatusEnum(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}
