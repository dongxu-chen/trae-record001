package com.ticket.enums;

import lombok.Getter;

@Getter
public enum TicketType {

    INCIDENT("事件", "故障或服务中断"),
    SERVICE_REQUEST("服务请求", "请求服务或信息"),
    PROBLEM("问题", "未知原因的事件"),
    CHANGE("变更", "配置项变更"),
    BUG("缺陷", "系统Bug"),
    CONSULTING("咨询", "技术咨询");

    private final String name;
    private final String description;

    TicketType(String name, String description) {
        this.name = name;
        this.description = description;
    }
}
