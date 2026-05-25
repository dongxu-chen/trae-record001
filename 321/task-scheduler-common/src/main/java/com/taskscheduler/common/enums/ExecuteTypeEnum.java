package com.taskscheduler.common.enums;

import lombok.Getter;

@Getter
public enum ExecuteTypeEnum {

    NORMAL(1, "正常执行"),
    RETRY(2, "重试执行"),
    MANUAL(3, "手动触发");

    private final Integer code;
    private final String desc;

    ExecuteTypeEnum(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}
