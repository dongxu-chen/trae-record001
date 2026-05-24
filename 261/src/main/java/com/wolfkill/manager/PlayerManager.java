package com.wolfkill.manager;

import com.wolfkill.entity.Player;
import com.wolfkill.model.PlayerSession;
import com.wolfkill.repository.PlayerRepository;
import io.netty.channel.Channel;
import io.netty.channel.ChannelId;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

@Component
public class PlayerManager {

    private final ConcurrentMap<Long, PlayerSession> playerSessions = new ConcurrentHashMap<>();
    private final ConcurrentMap<ChannelId, Long> channelToPlayer = new ConcurrentHashMap<>();

    private final PlayerRepository playerRepository;

    public PlayerManager(PlayerRepository playerRepository) {
        this.playerRepository = playerRepository;
    }

    public PlayerSession login(String nickname, String token, Channel channel) {
        Player player = playerRepository.findByNickname(nickname).orElse(null);
        if (player == null) {
            player = new Player();
            player.setNickname(nickname);
            player.setOnline(true);
            player = playerRepository.save(player);
        } else {
            player.setOnline(true);
            player = playerRepository.save(player);
        }

        String sessionId = UUID.randomUUID().toString().replace("-", "");
        player.setSessionId(sessionId);
        playerRepository.save(player);

        PlayerSession session = new PlayerSession();
        session.setPlayerId(player.getId());
        session.setNickname(player.getNickname());
        session.setSessionId(sessionId);
        session.setChannel(channel);
        session.setChannelId(channel.id());
        session.setOnline(true);

        playerSessions.put(player.getId(), session);
        channelToPlayer.put(channel.id(), player.getId());

        return session;
    }

    public void logout(Long playerId) {
        PlayerSession session = playerSessions.remove(playerId);
        if (session != null && session.getChannelId() != null) {
            channelToPlayer.remove(session.getChannelId());
        }

        Player player = playerRepository.findById(playerId).orElse(null);
        if (player != null) {
            player.setOnline(false);
            player.setCurrentRoomId(null);
            playerRepository.save(player);
        }
    }

    public PlayerSession getPlayer(Long playerId) {
        return playerSessions.get(playerId);
    }

    public PlayerSession getPlayerByChannel(ChannelId channelId) {
        Long playerId = channelToPlayer.get(channelId);
        if (playerId == null) {
            return null;
        }
        return playerSessions.get(playerId);
    }

    private static final long RECONNECT_WINDOW_MS = 5 * 60 * 1000;

    public PlayerSession reconnect(Long playerId, String sessionId, Channel channel) {
        Player player = playerRepository.findById(playerId).orElse(null);
        if (player == null || !sessionId.equals(player.getSessionId())) {
            logger.warn("Reconnect failed: invalid player or session for playerId {}", playerId);
            return null;
        }

        PlayerSession oldSession = playerSessions.get(playerId);
        if (oldSession == null) {
            logger.warn("Reconnect failed: no existing session for playerId {}", playerId);
            return null;
        }

        if (!oldSession.canReconnect(RECONNECT_WINDOW_MS)) {
            logger.warn("Reconnect failed: reconnect window expired for playerId {}", playerId);
            return null;
        }

        if (oldSession.getChannelId() != null) {
            channelToPlayer.remove(oldSession.getChannelId());
            Channel oldChannel = oldSession.getChannel();
            if (oldChannel != null && oldChannel.isActive()) {
                oldChannel.close();
            }
        }

        player.setOnline(true);
        playerRepository.save(player);

        oldSession.setChannel(channel);
        oldSession.setChannelId(channel.id());
        oldSession.markReconnected();
        oldSession.updateHeartbeat();

        playerSessions.put(player.getId(), oldSession);
        channelToPlayer.put(channel.id(), player.getId());

        logger.info("Player {} reconnected successfully, reconnect count: {}",
                playerId, oldSession.getReconnectCount());

        return oldSession;
    }

    public void handlePlayerDisconnect(Long playerId, GameRoomSession room) {
        PlayerSession session = playerSessions.get(playerId);
        if (session == null) {
            return;
        }

        session.saveGameState(room);
        session.markDisconnected();

        if (room != null) {
            session.setMissedFramesIndex(room.getRecordFrames().size());
        }

        Player player = playerRepository.findById(playerId).orElse(null);
        if (player != null) {
            player.setOnline(false);
            playerRepository.save(player);
        }

        logger.info("Player {} disconnected, can reconnect within {}ms", playerId, RECONNECT_WINDOW_MS);
    }

    public void updateChannel(Long playerId, Channel channel) {
        PlayerSession session = playerSessions.get(playerId);
        if (session != null) {
            if (session.getChannelId() != null) {
                channelToPlayer.remove(session.getChannelId());
            }
            session.setChannel(channel);
            session.setChannelId(channel.id());
            channelToPlayer.put(channel.id(), playerId);
        }
    }

    public void updateHeartbeat(Long playerId) {
        PlayerSession session = playerSessions.get(playerId);
        if (session != null) {
            session.updateHeartbeat();
        }

        Player player = playerRepository.findById(playerId).orElse(null);
        if (player != null) {
            player.setLastHeartbeat(LocalDateTime.now());
            playerRepository.save(player);
        }
    }

    public void setPlayerOffline(Long playerId) {
        PlayerSession session = playerSessions.get(playerId);
        if (session != null) {
            session.setOnline(false);
        }

        Player player = playerRepository.findById(playerId).orElse(null);
        if (player != null) {
            player.setOnline(false);
            playerRepository.save(player);
        }
    }

    public Map<Long, PlayerSession> getAllPlayers() {
        return playerSessions;
    }
}
