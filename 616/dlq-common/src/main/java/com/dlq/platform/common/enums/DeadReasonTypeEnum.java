package com.dlq.platform.common.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum DeadReasonTypeEnum {

    FORMAT_ERROR("FORMAT_ERROR", "格式错误"),
    BIZ_EXCEPTION("BIZ_EXCEPTION", "业务异常"),
    TIMEOUT("TIMEOUT", "消费超时"),
    REJECTED("REJECTED", "消费被拒绝"),
    OTHER("OTHER", "其他原因");

    private final String code;
    private final String desc;
}
