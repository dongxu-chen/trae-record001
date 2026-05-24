package com.wolfkill.model;

import com.wolfkill.protocol.GamePhase;
import com.wolfkill.protocol.PlayerStatus;
import com.wolfkill.protocol.Role;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

@Data
public class GameRoomSession {

    private Long roomId;
    private String roomName;
    private Long hostId;
    private String password;
    private int maxPlayers;
    private GamePhase phase = GamePhase.PHASE_WAITING;
    private int dayNumber = 0;
    private boolean active = true;
    private ConcurrentMap<Long, PlayerSession> players = new ConcurrentHashMap<>();
    private ConcurrentMap<Long, Role> playerRoles = new ConcurrentHashMap<>();
    private ConcurrentMap<Long, PlayerStatus> playerStatuses = new ConcurrentHashMap<>();
    private List<Long> wolfVoteTargets = new ArrayList<>();
    private Long witchAntidoteTarget;
    private Long witchPoisonTarget;
    private boolean witchAntidoteUsed = false;
    private boolean witchPoisonUsed = false;
    private ConcurrentMap<Long, Long> votes = new ConcurrentHashMap<>();
    private Long hunterTarget;
    private boolean hunterShot = false;
    private List<Long> deadPlayers = new ArrayList<>();
    private List<String> recordFrames = new ArrayList<>();
    private Long recordId;
    private long createdAt;
    private long phaseStartTime;
    private long phaseEndTime;
    private Long currentSpeakerId;
    private int speechIndex;
    private List<Long> speechOrder = new ArrayList<>();
    private volatile boolean phaseProcessing = false;
    private int retryCount = 0;
    private String lastError;
    private long lastErrorTime;

    public int getCurrentPlayers() {
        return players.size();
    }

    public List<PlayerSession> getPlayerList() {
        return new ArrayList<>(players.values());
    }

    public boolean isFull() {
        return players.size() >= maxPlayers;
    }

    public boolean hasPassword() {
        return password != null && !password.isEmpty();
    }

    public void addPlayer(PlayerSession player) {
        players.put(player.getPlayerId(), player);
        playerStatuses.put(player.getPlayerId(), PlayerStatus.STATUS_ALIVE);
    }

    public void removePlayer(Long playerId) {
        players.remove(playerId);
        playerRoles.remove(playerId);
        playerStatuses.remove(playerId);
    }

    public PlayerSession getPlayer(Long playerId) {
        return players.get(playerId);
    }

    public Role getPlayerRole(Long playerId) {
        return playerRoles.get(playerId);
    }

    public void setPlayerRole(Long playerId, Role role) {
        playerRoles.put(playerId, role);
    }

    public PlayerStatus getPlayerStatus(Long playerId) {
        return playerStatuses.getOrDefault(playerId, PlayerStatus.STATUS_OFFLINE);
    }

    public void setPlayerStatus(Long playerId, PlayerStatus status) {
        playerStatuses.put(playerId, status);
    }

    public boolean isPlayerAlive(Long playerId) {
        return playerStatuses.get(playerId) == PlayerStatus.STATUS_ALIVE;
    }

    public List<Long> getAlivePlayerIds() {
        List<Long> alive = new ArrayList<>();
        for (var entry : playerStatuses.entrySet()) {
            if (entry.getValue() == PlayerStatus.STATUS_ALIVE) {
                alive.add(entry.getKey());
            }
        }
        return alive;
    }

    public List<Long> getPlayerIdsByRole(Role role) {
        List<Long> result = new ArrayList<>();
        for (var entry : playerRoles.entrySet()) {
            if (entry.getValue() == role && isPlayerAlive(entry.getKey())) {
                result.add(entry.getKey());
            }
        }
        return result;
    }

    public int countAliveByRole(Role role) {
        int count = 0;
        for (var entry : playerRoles.entrySet()) {
            if (entry.getValue() == role && isPlayerAlive(entry.getKey())) {
                count++;
            }
        }
        return count;
    }
}
