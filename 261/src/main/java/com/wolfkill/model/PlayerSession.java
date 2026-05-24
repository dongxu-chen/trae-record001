package com.wolfkill.model;

import com.wolfkill.protocol.PlayerStatus;
import com.wolfkill.protocol.Role;
import io.netty.channel.Channel;
import io.netty.channel.ChannelId;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class PlayerSession {

    private Long playerId;
    private String nickname;
    private String sessionId;
    private Long currentRoomId;
    private Integer seat;
    private boolean isHost;
    private boolean online;
    private Channel channel;
    private ChannelId channelId;
    private long lastHeartbeat;
    private String reconnectToken;
    private int missedFramesIndex;
    private long disconnectTime;
    private long reconnectTime;
    private int reconnectCount;
    private Role savedRole;
    private PlayerStatus savedStatus;
    private List<Long> savedTeammateIds = new ArrayList<>();
    private volatile boolean reconnecting = false;

    public PlayerSession() {
        this.lastHeartbeat = System.currentTimeMillis();
        this.online = true;
    }

    public void updateHeartbeat() {
        this.lastHeartbeat = System.currentTimeMillis();
    }

    public boolean isHeartbeatExpired(long timeout) {
        return System.currentTimeMillis() - lastHeartbeat > timeout;
    }

    public void markDisconnected() {
        this.disconnectTime = System.currentTimeMillis();
        this.online = false;
        this.reconnecting = true;
    }

    public void markReconnected() {
        this.reconnectTime = System.currentTimeMillis();
        this.reconnectCount++;
        this.online = true;
        this.reconnecting = false;
    }

    public void saveGameState(GameRoomSession room) {
        if (room == null || playerId == null) {
            return;
        }
        this.savedRole = room.getPlayerRole(playerId);
        this.savedStatus = room.getPlayerStatus(playerId);
        this.currentRoomId = room.getRoomId();
        if (this.savedRole == Role.ROLE_WEREWOLF) {
            this.savedTeammateIds = room.getPlayerIdsByRole(Role.ROLE_WEREWOLF);
        } else {
            this.savedTeammateIds.clear();
        }
    }

    public boolean canReconnect(long reconnectWindowMs) {
        return reconnecting && (System.currentTimeMillis() - disconnectTime) < reconnectWindowMs;
    }
}
