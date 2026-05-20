package com.payment.reconciliation.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum ReconciliationStatusEnum {

    PENDING(0, "待处理"),
    PARSING(1, "解析中"),
    PARSED(2, "解析完成"),
    RECONCILING(3, "对账中"),
    SUCCESS(4, "对账成功"),
    FAILED(5, "失败");

    private final Integer code;
    private final String desc;
}
