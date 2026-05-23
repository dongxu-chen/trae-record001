package com.meeting.booking.common;

import lombok.Getter;

@Getter
public enum ApprovalStatusEnum {
    PENDING(0, "待审批"),
    APPROVED(1, "已通过"),
    REJECTED(2, "已拒绝");

    private final Integer code;
    private final String desc;

    ApprovalStatusEnum(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}
