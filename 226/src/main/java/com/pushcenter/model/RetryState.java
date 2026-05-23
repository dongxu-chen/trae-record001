package com.pushcenter.model;

import com.pushcenter.enums.MessageStatus;
import com.pushcenter.enums.PushChannel;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RetryState implements Serializable {

    private static final long serialVersionUID = 1L;

    private String messageId;

    private String userId;

    private String templateCode;

    private Map<String, Object> variables;

    private String title;

    private String content;

    private PushChannel channel;

    private String receiver;

    private int currentRetryCount;

    private int maxRetryCount;

    private long nextRetryTime;

    private long firstFailTime;

    private long lastFailTime;

    private String lastErrorMessage;

    private MessageStatus status;
}
