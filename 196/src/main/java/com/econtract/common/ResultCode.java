package com.econtract.common;

import lombok.Getter;

@Getter
public enum ResultCode {

    SUCCESS(200, "操作成功"),
    FAIL(500, "操作失败"),
    PARAM_ERROR(400, "参数错误"),
    UNAUTHORIZED(401, "未授权"),
    FORBIDDEN(403, "禁止访问"),
    NOT_FOUND(404, "资源不存在"),

    USER_NOT_FOUND(1001, "用户不存在"),
    USER_PASSWORD_ERROR(1002, "密码错误"),
    USER_DISABLED(1003, "用户已禁用"),
    USER_ALREADY_EXISTS(1004, "用户已存在"),
    PHONE_ALREADY_EXISTS(1005, "手机号已存在"),

    SMS_CODE_ERROR(2001, "验证码错误"),
    SMS_CODE_EXPIRED(2002, "验证码已过期"),
    SMS_SEND_FAIL(2003, "短信发送失败"),

    FACE_VERIFY_FAIL(3001, "人脸认证失败"),
    FACE_NOT_FOUND(3002, "未检测到人脸"),
    FACE_LOW_SIMILARITY(3003, "人脸相似度不足"),

    CONTRACT_NOT_FOUND(4001, "合同不存在"),
    CONTRACT_STATUS_ERROR(4002, "合同状态错误"),
    CONTRACT_NOT_YOUR_TURN(4003, "还未轮到您签署"),
    CONTRACT_ALREADY_SIGNED(4004, "您已签署此合同"),

    TEMPLATE_NOT_FOUND(5001, "模板不存在"),
    TEMPLATE_CODE_EXISTS(5002, "模板编码已存在"),

    SIGNATURE_ERROR(6001, "签名失败"),
    TIMESTAMP_ERROR(6002, "时间戳获取失败"),

    BLOCKCHAIN_ERROR(7001, "区块链存证失败");

    private final Integer code;
    private final String message;

    ResultCode(Integer code, String message) {
        this.code = code;
        this.message = message;
    }
}
