package com.payment.reconciliation.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum TransactionStatusEnum {

    PENDING(0, "待处理"),
    COMMITTED(1, "已提交"),
    ROLLBACK(2, "已回滚");

    private final Integer code;
    private final String desc;
}
