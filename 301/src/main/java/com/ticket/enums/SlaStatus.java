package com.ticket.enums;

import lombok.Getter;

@Getter
public enum SlaStatus {

    NORMAL("正常", "在SLA时间内"),
    WARNING("预警", "即将超时"),
    OVERDUE("已超时", "已超过SLA时间"),
    MET("已达成", "SLA已达成"),
    VIOLATED("已违反", "SLA已违反");

    private final String name;
    private final String description;

    SlaStatus(String name, String description) {
        this.name = name;
        this.description = description;
    }
}
