package com.wolfkill.service;

import com.wolfkill.manager.PlayerManager;
import com.wolfkill.manager.RoomManager;
import com.wolfkill.model.GameRoomSession;
import com.wolfkill.model.PlayerSession;
import com.wolfkill.protocol.PlayerStatus;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Service
public class HeartbeatService {

    private static final Logger logger = LoggerFactory.getLogger(HeartbeatService.class);

    @Value("${game.heartbeat.timeout:30000}")
    private long heartbeatTimeout;

    private static final long RECONNECT_WINDOW_MS = 5 * 60 * 1000;
    private static final long FORCE_LOGOUT_MS = 10 * 60 * 1000;

    private final PlayerManager playerManager;
    private final RoomManager roomManager;

    public HeartbeatService(PlayerManager playerManager, RoomManager roomManager) {
        this.playerManager = playerManager;
        this.roomManager = roomManager;
    }

    @Scheduled(fixedRateString = "${game.heartbeat.interval:5000}")
    public void checkHeartbeats() {
        List<Long> toDisconnect = new ArrayList<>();
        List<Long> toRemove = new ArrayList<>();

        for (Map.Entry<Long, PlayerSession> entry : playerManager.getAllPlayers().entrySet()) {
            PlayerSession player = entry.getValue();

            if (player.isOnline() && player.isHeartbeatExpired(heartbeatTimeout)) {
                logger.warn("Player heartbeat timeout: {} ({})", player.getPlayerId(), player.getNickname());
                toDisconnect.add(player.getPlayerId());
            }

            if (!player.isOnline() && player.isReconnecting()) {
                long offlineDuration = System.currentTimeMillis() - player.getDisconnectTime();
                if (offlineDuration > FORCE_LOGOUT_MS) {
                    logger.info("Player {} reconnect window expired, force logout", player.getPlayerId());
                    toRemove.add(player.getPlayerId());
                }
            }
        }

        for (Long playerId : toDisconnect) {
            PlayerSession player = playerManager.getPlayer(playerId);
            if (player != null && player.getCurrentRoomId() != null) {
                GameRoomSession room = roomManager.getRoom(player.getCurrentRoomId());
                playerManager.handlePlayerDisconnect(playerId, room);
                if (room != null) {
                    room.setPlayerStatus(playerId, PlayerStatus.STATUS_DISCONNECTED);
                }
            } else {
                playerManager.setPlayerOffline(playerId);
            }
        }

        for (Long playerId : toRemove) {
            PlayerSession player = playerManager.getPlayer(playerId);
            if (player != null && player.getCurrentRoomId() != null) {
                roomManager.leaveRoom(player.getCurrentRoomId(), playerId);
            }
            playerManager.logout(playerId);
        }
    }

    @Scheduled(cron = "0 0 * * * *")
    public void cleanupInactiveRooms() {
        logger.info("Starting cleanup of inactive rooms...");

        List<GameRoomSession> rooms = roomManager.getActiveRooms();
        for (GameRoomSession room : rooms) {
            if (!room.isActive() || room.getCurrentPlayers() == 0) {
                roomManager.removeRoom(room.getRoomId());
                logger.info("Cleaned up inactive room: {}", room.getRoomId());
            }
        }
    }
}
