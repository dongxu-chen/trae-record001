package com.payment.reconciliation.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum SettlementStatusEnum {

    PENDING(0, "待结算"),
    IN_PROGRESS(1, "结算中"),
    COMPLETED(2, "已完成"),
    DELAYED(3, "已延迟"),
    FAILED(4, "结算失败");

    private final Integer code;
    private final String desc;
}
