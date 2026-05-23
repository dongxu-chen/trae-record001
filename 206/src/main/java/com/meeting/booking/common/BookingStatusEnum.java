package com.meeting.booking.common;

import lombok.Getter;

@Getter
public enum BookingStatusEnum {
    CANCELLED(0, "已取消"),
    PENDING(1, "待确认"),
    CONFIRMED(2, "已确认"),
    COMPLETED(3, "已完成"),
    PENDING_APPROVAL(4, "待审批");

    private final Integer code;
    private final String desc;

    BookingStatusEnum(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}
