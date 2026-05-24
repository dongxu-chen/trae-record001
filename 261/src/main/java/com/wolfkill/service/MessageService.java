package com.wolfkill.service;

import com.wolfkill.manager.PlayerManager;
import com.wolfkill.model.PlayerSession;
import com.wolfkill.protocol.MessageType;
import com.wolfkill.protocol.MessageWrapper;
import io.netty.channel.Channel;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class MessageService {

    private static final Logger logger = LoggerFactory.getLogger(MessageService.class);

    private final PlayerManager playerManager;

    public MessageService(PlayerManager playerManager) {
        this.playerManager = playerManager;
    }

    public void sendToPlayer(Long playerId, MessageType type, com.google.protobuf.Message message) {
        PlayerSession player = playerManager.getPlayer(playerId);
        if (player != null && player.getChannel() != null && player.isOnline()) {
            sendToChannel(player.getChannel(), type, message);
        }
    }

    public void sendToChannel(Channel channel, MessageType type, com.google.protobuf.Message message) {
        if (channel == null || !channel.isActive()) {
            logger.warn("Channel is not active, cannot send message: {}", type);
            return;
        }

        try {
            MessageWrapper wrapper = MessageWrapper.newBuilder()
                    .setType(type)
                    .setPayload(message.toByteString())
                    .build();

            channel.writeAndFlush(wrapper);
            logger.debug("Sent message to channel: {}", type);
        } catch (Exception e) {
            logger.error("Failed to send message: {}", type, e);
        }
    }
}
