package com.ticket.enums;

import lombok.Getter;

@Getter
public enum TicketPriority {

    LOW(1, "低"),
    MEDIUM(2, "中"),
    HIGH(3, "高"),
    URGENT(4, "紧急"),
    CRITICAL(5, "致命");

    private final Integer code;
    private final String description;

    TicketPriority(Integer code, String description) {
        this.code = code;
        this.description = description;
    }

    public static TicketPriority fromCode(Integer code) {
        for (TicketPriority priority : values()) {
            if (priority.getCode().equals(code)) {
                return priority;
            }
        }
        throw new IllegalArgumentException("Invalid priority code: " + code);
    }
}
