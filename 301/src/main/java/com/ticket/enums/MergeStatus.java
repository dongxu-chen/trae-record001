package com.ticket.enums;

import lombok.Getter;

@Getter
public enum MergeStatus {

    PENDING("待确认", "自动检测到相似工单，等待确认"),
    APPROVED("已合并", "工单已合并"),
    REJECTED("已拒绝", "合并申请被拒绝"),
    CANCELLED("已取消", "合并已取消");

    private final String name;
    private final String description;

    MergeStatus(String name, String description) {
        this.name = name;
        this.description = description;
    }
}
