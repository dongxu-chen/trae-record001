package com.ticket.enums;

import lombok.Getter;

@Getter
public enum RelationType {

    PARENT_CHILD("父子", "主工单和子工单"),
    DEPENDS_ON("依赖", "依赖其他工单"),
    RELATED("关联", "相关工单"),
    DUPLICATE("重复", "重复工单");

    private final String name;
    private final String description;

    RelationType(String name, String description) {
        this.name = name;
        this.description = description;
    }
}
