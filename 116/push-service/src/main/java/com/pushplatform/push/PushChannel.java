package com.pushplatform.push;

import com.pushplatform.entity.PushRecord;

public interface PushChannel {

    String getChannel();

    PushResult send(PushRecord record) throws Exception;
}
