package com.pushcenter.model;

import com.pushcenter.enums.MessageStatus;
import com.pushcenter.enums.PushChannel;
import lombok.Builder;
import lombok.Data;

import java.io.Serializable;

@Data
@Builder
public class PushResult implements Serializable {

    private static final long serialVersionUID = 1L;

    private String messageId;

    private PushChannel channel;

    private MessageStatus status;

    private boolean success;

    private String errorMessage;

    private long sendTime;

    private String thirdPartyId;
}
