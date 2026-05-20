package com.pushplatform.push.reactive;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PushResult {

    private boolean success;
    private String messageId;
    private String errorMessage;
    private long latencyMs;

    public static PushResult success(String messageId) {
        return PushResult.builder()
                .success(true)
                .messageId(messageId)
                .build();
    }

    public static PushResult fail(String errorMessage) {
        return PushResult.builder()
                .success(false)
                .errorMessage(errorMessage)
                .build();
    }
}
