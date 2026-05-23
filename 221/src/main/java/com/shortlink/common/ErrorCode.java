package com.shortlink.common;

import lombok.Getter;

@Getter
public enum ErrorCode {

    SUCCESS(200, "success"),
    PARAM_ERROR(400, "参数错误"),
    SHORT_CODE_NOT_FOUND(404, "短链接不存在"),
    SHORT_CODE_EXPIRED(410, "短链接已过期"),
    SHORT_CODE_ALREADY_EXISTS(409, "短码已存在"),
    INVALID_SHORT_CODE(422, "无效的短码格式"),
    INVALID_URL(423, "无效的URL格式"),
    SERVER_ERROR(500, "服务器内部错误");

    private final Integer code;
    private final String message;

    ErrorCode(Integer code, String message) {
        this.code = code;
        this.message = message;
    }
}
