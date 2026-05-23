package com.pushcenter.model;

import com.pushcenter.enums.MessagePriority;
import com.pushcenter.enums.PushChannel;
import com.pushcenter.enums.MessageStatus;
import lombok.Builder;
import lombok.Data;

import java.io.Serializable;
import java.util.Map;

@Data
@Builder
public class PushMessage implements Serializable {

    private static final long serialVersionUID = 1L;

    private String messageId;

    private String userId;

    private String templateCode;

    private Map<String, Object> variables;

    private String title;

    private String content;

    private PushChannel channel;

    private String receiver;

    private MessageStatus status;

    private int retryCount;

    private int maxRetryCount;

    private long nextRetryTime;

    private long createTime;

    private long sendTime;

    private String errorMessage;

    private MessagePriority priority;

    private boolean jumpQueue;
}
