package com.pushcenter.channel;

import com.pushcenter.enums.PushChannel;
import com.pushcenter.model.PushMessage;
import com.pushcenter.model.PushResult;

public interface PushChannelHandler {

    PushChannel getChannel();

    PushResult send(PushMessage message);

    boolean isAvailable();
}
