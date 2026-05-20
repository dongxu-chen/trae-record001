package com.pushplatform.websocket;

import com.alibaba.fastjson2.JSON;
import io.netty.channel.Channel;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.SimpleChannelInboundHandler;
import io.netty.handler.codec.http.websocketx.TextWebSocketFrame;
import io.netty.handler.codec.http.websocketx.WebSocketFrame;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.function.Consumer;

@Component
public class WebSocketHandler extends SimpleChannelInboundHandler<WebSocketFrame> {

    private static final Logger logger = LoggerFactory.getLogger(WebSocketHandler.class);

    private static final Map<String, Channel> USER_CHANNELS = new ConcurrentHashMap<>();
    private static final Map<Channel, String> CHANNEL_USERS = new ConcurrentHashMap<>();

    private ExecutorService businessExecutor;

    public void setBusinessExecutor(ExecutorService businessExecutor) {
        this.businessExecutor = businessExecutor;
    }

    @Override
    protected void channelRead0(ChannelHandlerContext ctx, WebSocketFrame frame) {
        if (frame instanceof TextWebSocketFrame) {
            String text = ((TextWebSocketFrame) frame).text();
            logger.debug("Received message: {}", text);

            if (businessExecutor != null) {
                businessExecutor.execute(() -> processMessage(ctx, text));
            } else {
                processMessage(ctx, text);
            }
        }
    }

    private void processMessage(ChannelHandlerContext ctx, String text) {
        try {
            Map<String, Object> msg = JSON.parseObject(text, Map.class);
            String type = (String) msg.get("type");

            if ("bind".equals(type)) {
                String userId = (String) msg.get("userId");
                bindUser(userId, ctx.channel());
            } else if ("ping".equals(type)) {
                ctx.writeAndFlush(new TextWebSocketFrame("{\"type\":\"pong\"}"));
            }
        } catch (Exception e) {
            logger.error("Parse message failed", e);
        }
    }

    @Override
    public void channelActive(ChannelHandlerContext ctx) {
        logger.debug("Channel connected: {}", ctx.channel().id());
    }

    @Override
    public void channelInactive(ChannelHandlerContext ctx) {
        logger.debug("Channel disconnected: {}", ctx.channel().id());
        String userId = CHANNEL_USERS.remove(ctx.channel());
        if (userId != null) {
            USER_CHANNELS.remove(userId);
        }
    }

    @Override
    public void exceptionCaught(ChannelHandlerContext ctx, Throwable cause) {
        logger.error("WebSocket exception", cause);
        ctx.close();
    }

    private void bindUser(String userId, Channel channel) {
        Channel oldChannel = USER_CHANNELS.put(userId, channel);
        if (oldChannel != null) {
            CHANNEL_USERS.remove(oldChannel);
            oldChannel.close();
        }
        CHANNEL_USERS.put(channel, userId);
        logger.info("User {} bind success", userId);
    }

    public void sendMessageAsync(String userId, String message, Consumer<Boolean> callback) {
        if (businessExecutor != null) {
            businessExecutor.execute(() -> {
                boolean success = sendMessage(userId, message);
                if (callback != null) {
                    callback.accept(success);
                }
            });
        } else {
            boolean success = sendMessage(userId, message);
            if (callback != null) {
                callback.accept(success);
            }
        }
    }

    public static boolean sendMessage(String userId, String message) {
        Channel channel = USER_CHANNELS.get(userId);
        if (channel != null && channel.isActive()) {
            channel.writeAndFlush(new TextWebSocketFrame(message));
            return true;
        }
        return false;
    }

    public static boolean isOnline(String userId) {
        Channel channel = USER_CHANNELS.get(userId);
        return channel != null && channel.isActive();
    }
}
