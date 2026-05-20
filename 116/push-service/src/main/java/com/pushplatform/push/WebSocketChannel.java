package com.pushplatform.push;

import com.alibaba.fastjson2.JSON;
import com.pushplatform.common.enums.PushChannelEnum;
import com.pushplatform.entity.PushRecord;
import com.pushplatform.websocket.WebSocketHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@Component
public class WebSocketChannel implements PushChannel {

    private static final Logger logger = LoggerFactory.getLogger(WebSocketChannel.class);

    @Override
    public String getChannel() {
        return PushChannelEnum.WEBSOCKET.getCode();
    }

    @Override
    public PushResult send(PushRecord record) {
        try {
            Map<String, Object> message = new HashMap<>();
            message.put("type", "push");
            message.put("messageId", UUID.randomUUID().toString());
            message.put("title", record.getTitle());
            message.put("content", record.getContent());
            
            String messageJson = JSON.toJSONString(message);
            boolean success = WebSocketHandler.sendMessage(record.getTarget(), messageJson);
            
            if (success) {
                logger.info("WebSocket send success, target: {}, messageId: {}", record.getTarget(), message.get("messageId"));
                return PushResult.success(message.get("messageId").toString());
            } else {
                logger.warn("WebSocket send failed, target: {} is offline", record.getTarget());
                return PushResult.fail("User is offline");
            }
        } catch (Exception e) {
            logger.error("WebSocket send error, target: {}", record.getTarget(), e);
            return PushResult.fail(e.getMessage());
        }
    }
}
