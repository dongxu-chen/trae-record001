package com.pushcenter.channel;

import com.pushcenter.enums.PushChannel;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;

@Component
public class ChannelHandlerFactory {

    @Resource
    private List<PushChannelHandler> handlers;

    private final Map<PushChannel, PushChannelHandler> handlerMap = new EnumMap<>(PushChannel.class);

    @PostConstruct
    public void init() {
        for (PushChannelHandler handler : handlers) {
            handlerMap.put(handler.getChannel(), handler);
        }
    }

    public PushChannelHandler getHandler(PushChannel channel) {
        return handlerMap.get(channel);
    }

    public boolean isChannelAvailable(PushChannel channel) {
        PushChannelHandler handler = handlerMap.get(channel);
        return handler != null && handler.isAvailable();
    }
}
