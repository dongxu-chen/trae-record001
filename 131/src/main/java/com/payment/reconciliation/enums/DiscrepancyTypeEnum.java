package com.payment.reconciliation.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum DiscrepancyTypeEnum {

    LONG(1, "长款"),
    SHORT(2, "短款"),
    AMOUNT_MISMATCH(3, "金额不符");

    private final Integer code;
    private final String desc;
}
