package com.pushcenter.disruptor;

import com.pushcenter.model.PushMessage;

public class MessageEvent {

    private PushMessage message;

    public PushMessage getMessage() {
        return message;
    }

    public void setMessage(PushMessage message) {
        this.message = message;
    }

    public void clear() {
        this.message = null;
    }
}
