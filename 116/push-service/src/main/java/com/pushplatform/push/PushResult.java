package com.pushplatform.push;

import lombok.Data;

@Data
public class PushResult {

    private boolean success;

    private String messageId;

    private String errorMsg;

    public static PushResult success(String messageId) {
        PushResult result = new PushResult();
        result.setSuccess(true);
        result.setMessageId(messageId);
        return result;
    }

    public static PushResult fail(String errorMsg) {
        PushResult result = new PushResult();
        result.setSuccess(false);
        result.setErrorMsg(errorMsg);
        return result;
    }
}
