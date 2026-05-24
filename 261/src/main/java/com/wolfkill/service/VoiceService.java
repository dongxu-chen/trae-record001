package com.wolfkill.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.wolfkill.entity.VoiceRoom;
import com.wolfkill.manager.PlayerManager;
import com.wolfkill.manager.RoomManager;
import com.wolfkill.model.GameRoomSession;
import com.wolfkill.model.PlayerSession;
import com.wolfkill.protocol.*;
import com.wolfkill.repository.VoiceRoomRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;

@Service
public class VoiceService {

    private static final Logger logger = LoggerFactory.getLogger(VoiceService.class);

    @Value("${voice.server:localhost}")
    private String voiceServer;

    @Value("${voice.port:8080}")
    private int voicePort;

    private final VoiceRoomRepository voiceRoomRepository;
    private final RoomManager roomManager;
    private final PlayerManager playerManager;
    private final MessageService messageService;
    private final ObjectMapper objectMapper;

    private final Map<Long, Set<Long>> voiceRoomUsers = new ConcurrentHashMap<>();
    private final Map<Long, VoiceUserState> userVoiceStates = new ConcurrentHashMap<>();

    public VoiceService(VoiceRoomRepository voiceRoomRepository, RoomManager roomManager,
                        PlayerManager playerManager, MessageService messageService,
                        ObjectMapper objectMapper) {
        this.voiceRoomRepository = voiceRoomRepository;
        this.roomManager = roomManager;
        this.playerManager = playerManager;
        this.messageService = messageService;
        this.objectMapper = objectMapper;
    }

    public VoiceJoinRes joinVoiceRoom(Long playerId, Long roomId, boolean isWolfRoom) {
        GameRoomSession room = roomManager.getRoom(roomId);
        if (room == null) {
            return buildVoiceErrorRes(1, "房间不存在");
        }

        if (!room.getPlayers().containsKey(playerId)) {
            return buildVoiceErrorRes(2, "玩家不在房间内");
        }

        String roomType = isWolfRoom ? "WOLF" : "MAIN";

        if (isWolfRoom) {
            Role playerRole = room.getPlayerRole(playerId);
            if (playerRole != Role.ROLE_WEREWOLF) {
                return buildVoiceErrorRes(3, "只有狼人可以加入狼人语音频道");
            }

            if (room.getPhase() != GamePhase.PHASE_NIGHT) {
                return buildVoiceErrorRes(4, "只有夜晚可以使用狼人语音频道");
            }
        }

        VoiceRoom voiceRoom = voiceRoomRepository.findByRoomIdAndRoomType(roomId, roomType).orElse(null);
        if (voiceRoom == null || !voiceRoom.getActive()) {
            voiceRoom = createVoiceRoom(roomId, roomType, room);
        }

        if (voiceRoom.getCurrentUsers() >= voiceRoom.getMaxUsers()) {
            return buildVoiceErrorRes(5, "语音频道已满");
        }

        if (isWolfRoom && voiceRoom.getAllowedUserIds() != null) {
            try {
                List<Long> allowedIds = objectMapper.readValue(voiceRoom.getAllowedUserIds(),
                        objectMapper.getTypeFactory().constructCollectionType(List.class, Long.class));
                if (!allowedIds.contains(playerId)) {
                    return buildVoiceErrorRes(6, "无权加入该语音频道");
                }
            } catch (JsonProcessingException e) {
                logger.error("Failed to parse allowed user ids", e);
            }
        }

        voiceRoomUsers.computeIfAbsent(voiceRoom.getId(), k -> ConcurrentHashMap.newKeySet()).add(playerId);
        voiceRoom.setCurrentUsers(voiceRoomUsers.get(voiceRoom.getId()).size());
        voiceRoomRepository.save(voiceRoom);

        VoiceUserState userState = userVoiceStates.computeIfAbsent(playerId, k -> new VoiceUserState());
        userState.setPlayerId(playerId);
        userState.setNickname(playerManager.getPlayer(playerId).getNickname());
        userState.setSpeaking(false);
        userState.setMuted(false);
        userState.setDeafened(false);
        userState.setCurrentVoiceRoomId(voiceRoom.getId());

        broadcastVoiceState(voiceRoom.getId(), roomId);

        logger.info("Player {} joined voice room {} ({})", playerId, voiceRoom.getId(), roomType);

        return VoiceJoinRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .setRoomToken(voiceRoom.getRoomToken())
                .setVoiceServer(voiceServer)
                .setVoicePort(voicePort)
                .build();
    }

    public VoiceLeaveRes leaveVoiceRoom(Long playerId, Long roomId) {
        VoiceUserState userState = userVoiceStates.get(playerId);
        if (userState == null || userState.getCurrentVoiceRoomId() == null) {
            return VoiceLeaveRes.newBuilder()
                    .setHeader(buildSuccessHeader())
                    .build();
        }

        Long voiceRoomId = userState.getCurrentVoiceRoomId();
        Set<Long> users = voiceRoomUsers.get(voiceRoomId);
        if (users != null) {
            users.remove(playerId);
        }

        VoiceRoom voiceRoom = voiceRoomRepository.findById(voiceRoomId).orElse(null);
        if (voiceRoom != null) {
            voiceRoom.setCurrentUsers(users != null ? users.size() : 0);
            voiceRoomRepository.save(voiceRoom);
        }

        userState.setCurrentVoiceRoomId(null);
        userVoiceStates.remove(playerId);

        broadcastVoiceState(voiceRoomId, roomId);

        logger.info("Player {} left voice room {}", playerId, voiceRoomId);

        return VoiceLeaveRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .build();
    }

    public VoiceRoom createVoiceRoom(Long roomId, String roomType, GameRoomSession gameRoom) {
        VoiceRoom voiceRoom = new VoiceRoom();
        voiceRoom.setRoomId(roomId);
        voiceRoom.setVoiceRoomId(UUID.randomUUID().toString());
        voiceRoom.setRoomType(roomType);
        voiceRoom.setRoomToken(generateVoiceToken());
        voiceRoom.setVoiceServer(voiceServer);
        voiceRoom.setVoicePort(voicePort);
        voiceRoom.setActive(true);
        voiceRoom.setMaxUsers(12);
        voiceRoom.setCurrentUsers(0);
        voiceRoom.setExpireTime(LocalDateTime.now().plusHours(2));

        if ("WOLF".equals(roomType)) {
            List<Long> wolfIds = gameRoom.getPlayerIdsByRole(Role.ROLE_WEREWOLF);
            try {
                voiceRoom.setAllowedUserIds(objectMapper.writeValueAsString(wolfIds));
            } catch (JsonProcessingException e) {
                logger.error("Failed to serialize wolf ids", e);
            }
        }

        return voiceRoomRepository.save(voiceRoom);
    }

    public void createWolfVoiceRoom(GameRoomSession room) {
        if (room.getPhase() != GamePhase.PHASE_NIGHT) {
            return;
        }

        List<Long> wolfIds = room.getPlayerIdsByRole(Role.ROLE_WEREWOLF);
        if (wolfIds.isEmpty()) {
            return;
        }

        VoiceRoom voiceRoom = createVoiceRoom(room.getRoomId(), "WOLF", room);

        VoiceWolfRoomCreateNotify notify = VoiceWolfRoomCreateNotify.newBuilder()
                .setRoomId(room.getRoomId())
                .setWolfRoomToken(voiceRoom.getRoomToken())
                .addAllWolfPlayerIds(wolfIds)
                .setExpireTime(System.currentTimeMillis() + 30000)
                .build();

        for (Long wolfId : wolfIds) {
            PlayerSession player = playerManager.getPlayer(wolfId);
            if (player != null && player.isOnline() && player.getChannel() != null) {
                messageService.sendToChannel(player.getChannel(), MessageType.VOICE_WOLF_ROOM_CREATE_NOTIFY, notify);
            }
        }

        logger.info("Wolf voice room created for room {}, wolf count: {}", room.getRoomId(), wolfIds.size());
    }

    public void closeWolfVoiceRoom(Long roomId) {
        List<VoiceRoom> voiceRooms = voiceRoomRepository.findByRoomId(roomId);
        for (VoiceRoom voiceRoom : voiceRooms) {
            if ("WOLF".equals(voiceRoom.getRoomType()) && voiceRoom.getActive()) {
                voiceRoom.setActive(false);
                voiceRoomRepository.save(voiceRoom);

                Set<Long> users = voiceRoomUsers.remove(voiceRoom.getId());
                if (users != null) {
                    for (Long userId : users) {
                        VoiceUserState state = userVoiceStates.remove(userId);
                        if (state != null) {
                            state.setCurrentVoiceRoomId(null);
                        }
                    }
                }

                logger.info("Wolf voice room closed for room {}", roomId);
            }
        }
    }

    public void updateUserSpeakingState(Long playerId, boolean isSpeaking) {
        VoiceUserState state = userVoiceStates.get(playerId);
        if (state != null) {
            state.setSpeaking(isSpeaking);
            if (state.getCurrentVoiceRoomId() != null) {
                VoiceRoom voiceRoom = voiceRoomRepository.findById(state.getCurrentVoiceRoomId()).orElse(null);
                if (voiceRoom != null) {
                    broadcastVoiceState(state.getCurrentVoiceRoomId(), voiceRoom.getRoomId());
                }
            }
        }
    }

    public void updateUserMuteState(Long playerId, boolean isMuted) {
        VoiceUserState state = userVoiceStates.get(playerId);
        if (state != null) {
            state.setMuted(isMuted);
            if (state.getCurrentVoiceRoomId() != null) {
                VoiceRoom voiceRoom = voiceRoomRepository.findById(state.getCurrentVoiceRoomId()).orElse(null);
                if (voiceRoom != null) {
                    broadcastVoiceState(state.getCurrentVoiceRoomId(), voiceRoom.getRoomId());
                }
            }
        }
    }

    private void broadcastVoiceState(Long voiceRoomId, Long gameRoomId) {
        GameRoomSession room = roomManager.getRoom(gameRoomId);
        if (room == null) {
            return;
        }

        Set<Long> users = voiceRoomUsers.get(voiceRoomId);
        if (users == null || users.isEmpty()) {
            return;
        }

        List<VoiceUserState> states = new ArrayList<>();
        for (Long userId : users) {
            VoiceUserState state = userVoiceStates.get(userId);
            if (state != null) {
                states.add(state);
            }
        }

        VoiceUserStateNotify.Builder notifyBuilder = VoiceUserStateNotify.newBuilder()
                .setRoomId(gameRoomId);

        for (VoiceUserState state : states) {
            notifyBuilder.addUsers(com.wolfkill.protocol.VoiceUserState.newBuilder()
                    .setPlayerId(state.getPlayerId())
                    .setNickname(state.getNickname())
                    .setIsSpeaking(state.isSpeaking())
                    .setIsMuted(state.isMuted())
                    .setIsDeafened(state.isDeafened())
                    .build());
        }

        VoiceUserStateNotify notify = notifyBuilder.build();

        for (Long userId : users) {
            PlayerSession player = playerManager.getPlayer(userId);
            if (player != null && player.isOnline() && player.getChannel() != null) {
                messageService.sendToChannel(player.getChannel(), MessageType.VOICE_USER_STATE_NOTIFY, notify);
            }
        }
    }

    private String generateVoiceToken() {
        byte[] randomBytes = new byte[32];
        ThreadLocalRandom.current().nextBytes(randomBytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(randomBytes);
    }

    private VoiceJoinRes buildVoiceErrorRes(int code, String message) {
        return VoiceJoinRes.newBuilder()
                .setHeader(Header.newBuilder()
                        .setCode(code)
                        .setMessage(message)
                        .setTimestamp(System.currentTimeMillis())
                        .build())
                .build();
    }

    private Header buildSuccessHeader() {
        return Header.newBuilder()
                .setCode(0)
                .setMessage("success")
                .setTimestamp(System.currentTimeMillis())
                .build();
    }

    public static class VoiceUserState {
        private Long playerId;
        private String nickname;
        private boolean speaking;
        private boolean muted;
        private boolean deafened;
        private Long currentVoiceRoomId;

        public Long getPlayerId() { return playerId; }
        public void setPlayerId(Long playerId) { this.playerId = playerId; }
        public String getNickname() { return nickname; }
        public void setNickname(String nickname) { this.nickname = nickname; }
        public boolean isSpeaking() { return speaking; }
        public void setSpeaking(boolean speaking) { this.speaking = speaking; }
        public boolean isMuted() { return muted; }
        public void setMuted(boolean muted) { this.muted = muted; }
        public boolean isDeafened() { return deafened; }
        public void setDeafened(boolean deafened) { this.deafened = deafened; }
        public Long getCurrentVoiceRoomId() { return currentVoiceRoomId; }
        public void setCurrentVoiceRoomId(Long currentVoiceRoomId) { this.currentVoiceRoomId = currentVoiceRoomId; }
    }

    public void cleanupExpiredVoiceRooms() {
        List<VoiceRoom> activeRooms = voiceRoomRepository.findByActiveTrue();
        LocalDateTime now = LocalDateTime.now();
        for (VoiceRoom room : activeRooms) {
            if (room.getExpireTime() != null && room.getExpireTime().isBefore(now)) {
                room.setActive(false);
                voiceRoomRepository.save(room);
                voiceRoomUsers.remove(room.getId());
                logger.info("Expired voice room cleaned up: {}", room.getId());
            }
        }
    }
}
