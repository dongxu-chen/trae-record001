package com.pushcenter.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class PushResponse {

    private boolean success;
    private String messageId;
    private String message;
    private String channel;
}
