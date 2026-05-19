package com.payment.reconciliation.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum FeeTypeEnum {

    PERCENTAGE(1, "百分比费率"),
    FIXED(2, "固定金额"),
    TIERED(3, "阶梯费率");

    private final Integer code;
    private final String desc;
}
