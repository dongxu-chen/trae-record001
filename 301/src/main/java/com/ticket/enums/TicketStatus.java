package com.ticket.enums;

import lombok.Getter;

@Getter
public enum TicketStatus {

    PENDING("待处理", "工单已创建，等待分配"),
    ASSIGNED("已分配", "工单已分配给处理人"),
    IN_PROGRESS("处理中", "处理人正在处理"),
    PENDING_REPLY("待回复", "等待用户回复"),
    RESOLVED("已解决", "问题已解决，等待确认"),
    COMPLETED("已完成", "工单已完成"),
    CLOSED("已关闭", "工单已关闭"),
    CANCELLED("已取消", "工单已取消");

    private final String name;
    private final String description;

    TicketStatus(String name, String description) {
        this.name = name;
        this.description = description;
    }
}
