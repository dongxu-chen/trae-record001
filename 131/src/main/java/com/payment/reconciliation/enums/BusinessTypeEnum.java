package com.payment.reconciliation.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum BusinessTypeEnum {

    RECONCILIATION("RECONCILIATION", "对账处理"),
    DISCREPANCY("DISCREPANCY", "差错处理"),
    FUND_TRANSFER("FUND_TRANSFER", "资金调拨");

    private final String code;
    private final String desc;
}
