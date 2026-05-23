package com.pushcenter.model;

import com.pushcenter.enums.PushChannel;
import lombok.Builder;
import lombok.Data;

import java.io.Serializable;
import java.util.List;
import java.util.Map;

@Data
@Builder
public class UserChannelConfig implements Serializable {

    private static final long serialVersionUID = 1L;

    private String userId;

    private Map<PushChannel, String> channelReceivers;

    private List<PushChannel> preferredChannels;

    private List<PushChannel> disabledChannels;

    private String timezone;
}
