package com.wolfkill.manager;

import com.wolfkill.entity.GameRoom;
import com.wolfkill.model.GameRoomSession;
import com.wolfkill.model.PlayerSession;
import com.wolfkill.protocol.GamePhase;
import com.wolfkill.repository.GameRoomRepository;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.atomic.AtomicLong;

@Component
public class RoomManager {

    private final ConcurrentMap<Long, GameRoomSession> roomSessions = new ConcurrentHashMap<>();
    private final AtomicLong roomIdGenerator = new AtomicLong(System.currentTimeMillis());

    private final GameRoomRepository gameRoomRepository;

    public RoomManager(GameRoomRepository gameRoomRepository) {
        this.gameRoomRepository = gameRoomRepository;
    }

    public GameRoomSession createRoom(Long hostId, String roomName, int maxPlayers, String password) {
        long roomId = roomIdGenerator.incrementAndGet();

        GameRoom gameRoom = new GameRoom();
        gameRoom.setId(roomId);
        gameRoom.setRoomName(roomName);
        gameRoom.setMaxPlayers(maxPlayers);
        gameRoom.setCurrentPlayers(0);
        gameRoom.setPassword(password);
        gameRoom.setHostId(hostId);
        gameRoom.setGamePhase(GamePhase.PHASE_WAITING.getNumber());
        gameRoom.setActive(true);
        gameRoomRepository.save(gameRoom);

        GameRoomSession session = new GameRoomSession();
        session.setRoomId(roomId);
        session.setRoomName(roomName);
        session.setHostId(hostId);
        session.setPassword(password);
        session.setMaxPlayers(maxPlayers);
        session.setCreatedAt(System.currentTimeMillis());

        roomSessions.put(roomId, session);
        return session;
    }

    public GameRoomSession getRoom(Long roomId) {
        return roomSessions.get(roomId);
    }

    public void removeRoom(Long roomId) {
        roomSessions.remove(roomId);
        GameRoom gameRoom = gameRoomRepository.findById(roomId).orElse(null);
        if (gameRoom != null) {
            gameRoom.setActive(false);
            gameRoomRepository.save(gameRoom);
        }
    }

    public List<GameRoomSession> getActiveRooms() {
        return new ArrayList<>(roomSessions.values());
    }

    public boolean joinRoom(Long roomId, PlayerSession player, String password) {
        GameRoomSession room = roomSessions.get(roomId);
        if (room == null || !room.isActive()) {
            return false;
        }

        if (room.hasPassword() && !room.getPassword().equals(password)) {
            return false;
        }

        if (room.isFull()) {
            return false;
        }

        if (room.getPlayers().containsKey(player.getPlayerId())) {
            return false;
        }

        int seat = findAvailableSeat(room);
        player.setSeat(seat);
        player.setCurrentRoomId(roomId);
        player.setHost(player.getPlayerId().equals(room.getHostId()));

        room.addPlayer(player);

        GameRoom gameRoom = gameRoomRepository.findById(roomId).orElse(null);
        if (gameRoom != null) {
            gameRoom.setCurrentPlayers(room.getCurrentPlayers());
            gameRoomRepository.save(gameRoom);
        }

        return true;
    }

    private int findAvailableSeat(GameRoomSession room) {
        boolean[] seats = new boolean[room.getMaxPlayers()];
        for (PlayerSession player : room.getPlayerList()) {
            if (player.getSeat() != null && player.getSeat() < seats.length) {
                seats[player.getSeat()] = true;
            }
        }
        for (int i = 0; i < seats.length; i++) {
            if (!seats[i]) {
                return i;
            }
        }
        return seats.length;
    }

    public void leaveRoom(Long roomId, Long playerId) {
        GameRoomSession room = roomSessions.get(roomId);
        if (room == null) {
            return;
        }

        room.removePlayer(playerId);

        if (playerId.equals(room.getHostId()) && room.getCurrentPlayers() > 0) {
            PlayerSession newHost = room.getPlayerList().get(0);
            room.setHostId(newHost.getPlayerId());
            newHost.setHost(true);
        }

        GameRoom gameRoom = gameRoomRepository.findById(roomId).orElse(null);
        if (gameRoom != null) {
            gameRoom.setCurrentPlayers(room.getCurrentPlayers());
            if (playerId.equals(gameRoom.getHostId()) && room.getCurrentPlayers() > 0) {
                gameRoom.setHostId(room.getHostId());
            }
            gameRoomRepository.save(gameRoom);
        }

        if (room.getCurrentPlayers() == 0) {
            removeRoom(roomId);
        }
    }

    public void updateRoomPhase(Long roomId, GamePhase phase) {
        GameRoomSession room = roomSessions.get(roomId);
        if (room != null) {
            room.setPhase(phase);
            GameRoom gameRoom = gameRoomRepository.findById(roomId).orElse(null);
            if (gameRoom != null) {
                gameRoom.setGamePhase(phase.getNumber());
                gameRoomRepository.save(gameRoom);
            }
        }
    }

    public void incrementDayNumber(Long roomId) {
        GameRoomSession room = roomSessions.get(roomId);
        if (room != null) {
            room.setDayNumber(room.getDayNumber() + 1);
            GameRoom gameRoom = gameRoomRepository.findById(roomId).orElse(null);
            if (gameRoom != null) {
                gameRoom.setDayNumber(room.getDayNumber());
                gameRoomRepository.save(gameRoom);
            }
        }
    }
}
