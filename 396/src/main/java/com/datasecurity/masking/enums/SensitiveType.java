package com.datasecurity.masking.enums;

import lombok.Getter;

@Getter
public enum SensitiveType {

    ID_CARD("身份证号", "^[1-9]\\d{5}(18|19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01])\\d{3}[\\dXx]$"),

    PHONE("手机号", "^1[3-9]\\d{9}$"),

    BANK_CARD("银行卡号", "^[1-9]\\d{12,18}$"),

    NAME("姓名", "^[\\u4e00-\\u9fa5]{2,4}$"),

    EMAIL("邮箱", "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"),

    ADDRESS("地址", "^[\\u4e00-\\u9fa50-9A-Za-z\\s]+[省市区街道路号].*$"),

    UNKNOWN("未知", null);

    private final String description;

    private final String regex;

    SensitiveType(String description, String regex) {
        this.description = description;
        this.regex = regex;
    }
}
