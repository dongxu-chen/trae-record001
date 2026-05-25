package com.taskscheduler.common.enums;

import lombok.Getter;

@Getter
public enum ExecutorRouteStrategyEnum {

    ROUND_ROBIN(1, "轮询"),
    RANDOM(2, "随机"),
    CONSISTENT_HASH(3, "一致性哈希");

    private final Integer code;
    private final String desc;

    ExecutorRouteStrategyEnum(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public static ExecutorRouteStrategyEnum getByCode(Integer code) {
        if (code == null) {
            return ROUND_ROBIN;
        }
        for (ExecutorRouteStrategyEnum item : values()) {
            if (item.getCode().equals(code)) {
                return item;
            }
        }
        return ROUND_ROBIN;
    }
}
