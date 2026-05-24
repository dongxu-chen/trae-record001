package com.wolfkill.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.wolfkill.entity.GameFrame;
import com.wolfkill.entity.GameRecord;
import com.wolfkill.model.GameRoomSession;
import com.wolfkill.protocol.GameResult;
import com.wolfkill.protocol.PlayerInfo;
import com.wolfkill.protocol.RecordFrame;
import com.wolfkill.repository.GameFrameRepository;
import com.wolfkill.repository.GameRecordRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class ReplayService {

    private static final Logger logger = LoggerFactory.getLogger(ReplayService.class);

    private final GameRecordRepository gameRecordRepository;
    private final GameFrameRepository gameFrameRepository;
    private final ObjectMapper objectMapper;

    private final Map<Long, List<RecordFrame>> pendingFrames = new ConcurrentHashMap<>();

    public ReplayService(GameRecordRepository gameRecordRepository,
                         GameFrameRepository gameFrameRepository,
                         ObjectMapper objectMapper) {
        this.gameRecordRepository = gameRecordRepository;
        this.gameFrameRepository = gameFrameRepository;
        this.objectMapper = objectMapper;
    }

    public void startRecording(GameRoomSession room) {
        GameRecord record = new GameRecord();
        record.setRoomId(room.getRoomId());
        record.setRoomName(room.getRoomName());
        record.setStartTime(LocalDateTime.now());
        record.setPlayerCount(room.getCurrentPlayers());
        record = gameRecordRepository.save(record);

        room.setRecordId(record.getId());
        pendingFrames.put(record.getId(), new ArrayList<>());
    }

    public void recordFrame(GameRoomSession room, String eventType, String eventData, List<PlayerInfo> playerStates) {
        if (room.getRecordId() == null) {
            return;
        }

        try {
            RecordFrame frame = RecordFrame.newBuilder()
                    .setTimestamp(System.currentTimeMillis())
                    .setDayNumber(room.getDayNumber())
                    .setPhase(room.getPhase())
                    .setEventType(eventType)
                    .setEventData(eventData != null ? eventData : "")
                    .addAllPlayerStates(playerStates)
                    .build();

            List<RecordFrame> frames = pendingFrames.get(room.getRecordId());
            if (frames != null) {
                frames.add(frame);
            }
        } catch (Exception e) {
            logger.error("Failed to record frame", e);
        }
    }

    @Transactional
    public Long endRecording(GameRoomSession room, GameResult result) {
        if (room.getRecordId() == null) {
            return null;
        }

        try {
            GameRecord record = gameRecordRepository.findById(room.getRecordId()).orElse(null);
            if (record != null) {
                record.setEndTime(LocalDateTime.now());
                record.setGameResult(result.getNumber());
                record.setTotalDays(room.getDayNumber());
                gameRecordRepository.save(record);

                saveFrames(record.getId(), pendingFrames.remove(room.getRecordId()));
            }

            return room.getRecordId();
        } catch (Exception e) {
            logger.error("Failed to end recording", e);
            return null;
        }
    }

    @Async
    @Transactional
    public void saveFrames(Long recordId, List<RecordFrame> frames) {
        if (frames == null || frames.isEmpty()) {
            return;
        }

        try {
            for (int i = 0; i < frames.size(); i++) {
                RecordFrame frame = frames.get(i);
                GameFrame gameFrame = new GameFrame();
                gameFrame.setRecordId(recordId);
                gameFrame.setFrameIndex(i);
                gameFrame.setTimestamp(frame.getTimestamp());
                gameFrame.setDayNumber(frame.getDayNumber());
                gameFrame.setGamePhase(frame.getPhase().getNumber());
                gameFrame.setEventType(frame.getEventType());
                gameFrame.setEventData(frame.getEventData());

                List<Map<String, Object>> playerStateList = new ArrayList<>();
                for (PlayerInfo info : frame.getPlayerStatesList()) {
                    Map<String, Object> state = Map.of(
                            "playerId", info.getPlayerId(),
                            "nickname", info.getNickname(),
                            "seat", info.getSeat(),
                            "role", info.getRole().getNumber(),
                            "status", info.getStatus().getNumber(),
                            "isHost", info.getIsHost(),
                            "isOnline", info.getIsOnline()
                    );
                    playerStateList.add(state);
                }
                gameFrame.setPlayerStates(objectMapper.writeValueAsString(playerStateList));

                gameFrameRepository.save(gameFrame);
            }
        } catch (JsonProcessingException e) {
            logger.error("Failed to save frames", e);
        }
    }

    public List<GameRecord> getRecordList(int page, int size) {
        return gameRecordRepository.findAllByOrderByCreatedAtDesc(
                org.springframework.data.domain.PageRequest.of(page, size)
        ).getContent();
    }

    public List<RecordFrame> getPlaybackFrames(Long recordId) {
        List<GameFrame> gameFrames = gameFrameRepository.findByRecordIdOrderByFrameIndexAsc(recordId);
        List<RecordFrame> frames = new ArrayList<>();

        try {
            for (GameFrame gameFrame : gameFrames) {
                RecordFrame.Builder builder = RecordFrame.newBuilder()
                        .setTimestamp(gameFrame.getTimestamp())
                        .setDayNumber(gameFrame.getDayNumber())
                        .setPhase(com.wolfkill.protocol.GamePhase.forNumber(gameFrame.getGamePhase()))
                        .setEventType(gameFrame.getEventType())
                        .setEventData(gameFrame.getEventData() != null ? gameFrame.getEventData() : "");

                if (gameFrame.getPlayerStates() != null && !gameFrame.getPlayerStates().isEmpty()) {
                    List<Map<String, Object>> playerStateList = objectMapper.readValue(
                            gameFrame.getPlayerStates(),
                            new TypeReference<List<Map<String, Object>>>() {}
                    );

                    for (Map<String, Object> state : playerStateList) {
                        PlayerInfo info = PlayerInfo.newBuilder()
                                .setPlayerId(((Number) state.get("playerId")).longValue())
                                .setNickname((String) state.get("nickname"))
                                .setSeat((Integer) state.get("seat"))
                                .setRole(com.wolfkill.protocol.Role.forNumber((Integer) state.get("role")))
                                .setStatus(com.wolfkill.protocol.PlayerStatus.forNumber((Integer) state.get("status")))
                                .setIsHost((Boolean) state.get("isHost"))
                                .setIsOnline((Boolean) state.get("isOnline"))
                                .build();
                        builder.addPlayerStates(info);
                    }
                }

                frames.add(builder.build());
            }
        } catch (JsonProcessingException e) {
            logger.error("Failed to parse playback frames", e);
        }

        return frames;
    }

    public RecordFrame getPlaybackFrame(Long recordId, int frameIndex) {
        List<RecordFrame> frames = getPlaybackFrames(recordId);
        if (frameIndex >= 0 && frameIndex < frames.size()) {
            return frames.get(frameIndex);
        }
        return null;
    }

    public GameRecord getRecord(Long recordId) {
        return gameRecordRepository.findById(recordId).orElse(null);
    }
}
