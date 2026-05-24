package com.wolfkill.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.wolfkill.ai.AiService;
import com.wolfkill.manager.PlayerManager;
import com.wolfkill.manager.RoomManager;
import com.wolfkill.model.GameRoomSession;
import com.wolfkill.model.PlayerSession;
import com.wolfkill.protocol.*;
import io.netty.channel.Channel;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

@Service
public class GameService {

    private static final Logger logger = LoggerFactory.getLogger(GameService.class);

    private final RoomManager roomManager;
    private final PlayerManager playerManager;
    private final RoleService roleService;
    private final MessageService messageService;
    private final ReplayService replayService;
    private final ObjectMapper objectMapper;
    private final VoiceService voiceService;
    private final RankService rankService;
    private final AiService aiService;

    private final ScheduledExecutorService gameScheduler = new ScheduledThreadPoolExecutor(10);
    private final Map<Long, Runnable> nightTimeouts = new ConcurrentHashMap<>();
    private final Map<Long, Runnable> speechTimeouts = new ConcurrentHashMap<>();
    private final Map<Long, Runnable> voteTimeouts = new ConcurrentHashMap<>();
    private final Map<Long, Runnable> hunterTimeouts = new ConcurrentHashMap<>();
    private final Map<Long, Long> roomMatchIds = new ConcurrentHashMap<>();

    private static final long NIGHT_DURATION = 30000;
    private static final long SPEECH_DURATION = 60000;
    private static final long VOTE_DURATION = 30000;
    private static final long HUNTER_SHOT_DURATION = 20000;
    private static final long PHASE_TIMEOUT_MARGIN = 5000;
    private static final int MAX_RETRY_COUNT = 3;
    private static final long RETRY_DELAY = 2000;

    public GameService(RoomManager roomManager, PlayerManager playerManager,
                       RoleService roleService, MessageService messageService,
                       ReplayService replayService, ObjectMapper objectMapper,
                       VoiceService voiceService, RankService rankService,
                       AiService aiService) {
        this.roomManager = roomManager;
        this.playerManager = playerManager;
        this.roleService = roleService;
        this.messageService = messageService;
        this.replayService = replayService;
        this.objectMapper = objectMapper;
        this.voiceService = voiceService;
        this.rankService = rankService;
        this.aiService = aiService;
    }

    @Scheduled(fixedRate = 10000)
    public void checkStuckPhases() {
        for (GameRoomSession room : roomManager.getActiveRooms()) {
            if (room.getPhase() == GamePhase.PHASE_WAITING || room.getPhase() == GamePhase.PHASE_ENDED) {
                continue;
            }

            long elapsed = System.currentTimeMillis() - room.getPhaseStartTime();
            long expectedDuration = getPhaseExpectedDuration(room.getPhase());

            if (elapsed > expectedDuration + PHASE_TIMEOUT_MARGIN) {
                logger.warn("Detected stuck phase in room {}: {}, elapsed {}ms", room.getRoomId(), room.getPhase(), elapsed);
                recoverStuckPhase(room);
            }
        }
    }

    private long getPhaseExpectedDuration(GamePhase phase) {
        return switch (phase) {
            case PHASE_NIGHT -> NIGHT_DURATION;
            case PHASE_SPEECH -> SPEECH_DURATION * 12;
            case PHASE_VOTE -> VOTE_DURATION;
            default -> 60000;
        };
    }

    private void recoverStuckPhase(GameRoomSession room) {
        if (room.getRetryCount() >= MAX_RETRY_COUNT) {
            logger.error("Max retries exceeded for room {}, forcing game end", room.getRoomId());
            forceEndGame(room);
            return;
        }

        room.setRetryCount(room.getRetryCount() + 1);
        room.setLastError("Phase timeout recovery");
        room.setLastErrorTime(System.currentTimeMillis());

        logger.info("Recovering room {} from stuck phase {}, retry {}/{}",
                room.getRoomId(), room.getPhase(), room.getRetryCount(), MAX_RETRY_COUNT);

        try {
            advanceFromStuckPhase(room);
        } catch (Exception e) {
            logger.error("Recovery failed for room {}", room.getRoomId(), e);
            scheduleRetry(room);
        }
    }

    private void advanceFromStuckPhase(GameRoomSession room) {
        cancelAllTimeouts(room.getRoomId());
        room.setPhaseProcessing(false);

        switch (room.getPhase()) {
            case PHASE_NIGHT -> processNightEnd(room.getRoomId());
            case PHASE_SPEECH -> startVotePhase(room.getRoomId());
            case PHASE_VOTE -> processVoteEnd(room.getRoomId());
            case PHASE_DAY -> startSpeechPhase(room.getRoomId());
            default -> {
                room.setRetryCount(MAX_RETRY_COUNT);
                forceEndGame(room);
            }
        }
    }

    private void scheduleRetry(GameRoomSession room) {
        gameScheduler.schedule(() -> {
            if (room.getRetryCount() < MAX_RETRY_COUNT) {
                recoverStuckPhase(room);
            } else {
                forceEndGame(room);
            }
        }, RETRY_DELAY, TimeUnit.MILLISECONDS);
    }

    private void forceEndGame(GameRoomSession room) {
        try {
            cancelAllTimeouts(room.getRoomId());
            room.setPhaseProcessing(false);

            int wolfCount = room.countAliveByRole(Role.ROLE_WEREWOLF);
            int villagerCount = room.getAlivePlayerIds().size() - wolfCount;

            GameResult result = wolfCount >= villagerCount ?
                    GameResult.RESULT_WEREWOLF_WIN : GameResult.RESULT_VILLAGER_WIN;

            endGame(room, result);

            logger.info("Force ended game in room {} with result: {}", room.getRoomId(), result);
        } catch (Exception e) {
            logger.error("Failed to force end game for room {}", room.getRoomId(), e);
        }
    }

    public boolean startGame(Long roomId, Long playerId) {
        GameRoomSession room = roomManager.getRoom(roomId);
        if (room == null) {
            return false;
        }

        if (!playerId.equals(room.getHostId())) {
            return false;
        }

        if (room.getPhase() != GamePhase.PHASE_WAITING) {
            return false;
        }

        if (room.isPhaseProcessing()) {
            logger.warn("Room {} is already processing, cannot start game", roomId);
            return false;
        }

        int playerCount = room.getCurrentPlayers();
        if (playerCount < 6) {
            logger.info("Room {} has only {} players, auto-filling with AI", roomId, playerCount);
            aiService.autoFillRoomIfNeeded(roomId);
            playerCount = room.getCurrentPlayers();
        }

        if (!roleService.isValidRoleConfig(playerCount)) {
            return false;
        }

        try {
            room.setPhaseProcessing(true);
            room.setRetryCount(0);
            room.setLastError(null);

            roleService.assignRoles(room);
            roomManager.updateRoomPhase(roomId, GamePhase.PHASE_NIGHT);
            roomManager.incrementDayNumber(roomId);

            replayService.startRecording(room);

            sendGameStartNotify(room);
            sendRoleAssignments(room);

            recordFrame(room, "GAME_START", null);

            startNightPhase(roomId);
            return true;
        } catch (Exception e) {
            logger.error("Failed to start game in room {}", roomId, e);
            room.setPhaseProcessing(false);
            room.setLastError("Start game failed: " + e.getMessage());
            return false;
        }
    }

    private void sendGameStartNotify(GameRoomSession room) {
        List<PlayerInfo> playerInfos = buildPlayerInfoList(room);
        GameStartNotify notify = GameStartNotify.newBuilder()
                .setRoomId(room.getRoomId())
                .addAllPlayers(playerInfos)
                .build();

        broadcastToRoom(room, MessageType.GAME_START_NOTIFY, notify);
    }

    private void sendRoleAssignments(GameRoomSession room) {
        List<Long> wolfIds = room.getPlayerIdsByRole(Role.ROLE_WEREWOLF);

        for (Map.Entry<Long, Role> entry : room.getPlayerRoles().entrySet()) {
            Long playerId = entry.getKey();
            Role role = entry.getValue();

            RoleAssignNotify.Builder builder = RoleAssignNotify.newBuilder()
                    .setPlayerId(playerId)
                    .setRole(role);

            if (role == Role.ROLE_WEREWOLF) {
                for (Long wolfId : wolfIds) {
                    if (!wolfId.equals(playerId)) {
                        builder.addTeammateIds(wolfId);
                    }
                }
            }

            messageService.sendToPlayer(playerId, MessageType.ROLE_ASSIGN_NOTIFY, builder.build());
        }
    }

    private void startNightPhase(Long roomId) {
        GameRoomSession room = roomManager.getRoom(roomId);
        if (room == null) {
            return;
        }

        try {
            room.setPhaseProcessing(true);
            roomManager.updateRoomPhase(roomId, GamePhase.PHASE_NIGHT);
            room.setPhaseStartTime(System.currentTimeMillis());
            room.setPhaseEndTime(System.currentTimeMillis() + NIGHT_DURATION);

            room.getWolfVoteTargets().clear();
            room.setWitchAntidoteTarget(null);
            room.setWitchPoisonTarget(null);
            room.setHunterTarget(null);
            room.setHunterShot(false);
            room.getVotes().clear();

            NightStartNotify notify = NightStartNotify.newBuilder()
                    .setRoomId(roomId)
                    .setDayNumber(room.getDayNumber())
                    .build();
            broadcastToRoom(room, MessageType.NIGHT_START_NOTIFY, notify);

            recordFrame(room, "NIGHT_START", null);

            voiceService.createWolfVoiceRoom(room);

            aiService.scheduleAiActions(roomId);

            Runnable timeout = () -> {
                try {
                    nightTimeouts.remove(roomId);
                    processNightEnd(roomId);
                } catch (Exception e) {
                    logger.error("Night phase timeout error for room {}", roomId, e);
                    handlePhaseError(room, e);
                }
            };
            nightTimeouts.put(roomId, timeout);
            gameScheduler.schedule(timeout, NIGHT_DURATION, TimeUnit.MILLISECONDS);

            room.setPhaseProcessing(false);
        } catch (Exception e) {
            logger.error("Failed to start night phase for room {}", roomId, e);
            handlePhaseError(room, e);
        }
    }

    public void handleWolfKill(Long roomId, Long playerId, Long targetId) {
        GameRoomSession room = roomManager.getRoom(roomId);
        if (room == null || room.getPhase() != GamePhase.PHASE_NIGHT) {
            return;
        }

        Role role = room.getPlayerRole(playerId);
        if (role != Role.ROLE_WEREWOLF || !room.isPlayerAlive(playerId)) {
            return;
        }

        if (!room.isPlayerAlive(targetId)) {
            return;
        }

        room.getWolfVoteTargets().add(targetId);

        Map<String, Object> data = new HashMap<>();
        data.put("killerId", playerId);
        data.put("targetId", targetId);
        recordFrame(room, "WOLF_KILL", data);
    }

    public boolean handleSeerCheck(Long roomId, Long playerId, Long targetId) {
        GameRoomSession room = roomManager.getRoom(roomId);
        if (room == null || room.getPhase() != GamePhase.PHASE_NIGHT) {
            return false;
        }

        Role role = room.getPlayerRole(playerId);
        if (role != Role.ROLE_SEER || !room.isPlayerAlive(playerId)) {
            return false;
        }

        Role targetRole = room.getPlayerRole(targetId);
        boolean isWerewolf = targetRole == Role.ROLE_WEREWOLF;

        SeerCheckRes res = SeerCheckRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .setTargetId(targetId)
                .setIsWerewolf(isWerewolf)
                .build();
        messageService.sendToPlayer(playerId, MessageType.SEER_CHECK_RES, res);

        Map<String, Object> data = new HashMap<>();
        data.put("seerId", playerId);
        data.put("targetId", targetId);
        data.put("isWerewolf", isWerewolf);
        recordFrame(room, "SEER_CHECK", data);

        return true;
    }

    public boolean handleWitchAction(Long roomId, Long playerId, boolean useAntidote,
                                     boolean usePoison, Long poisonTargetId) {
        GameRoomSession room = roomManager.getRoom(roomId);
        if (room == null || room.getPhase() != GamePhase.PHASE_NIGHT) {
            return false;
        }

        Role role = room.getPlayerRole(playerId);
        if (role != Role.ROLE_WITCH || !room.isPlayerAlive(playerId)) {
            return false;
        }

        if (useAntidote && room.isWitchAntidoteUsed()) {
            return false;
        }
        if (usePoison && room.isWitchPoisonUsed()) {
            return false;
        }

        if (useAntidote) {
            room.setWitchAntidoteUsed(true);
            if (!room.getWolfVoteTargets().isEmpty()) {
                room.setWitchAntidoteTarget(room.getWolfVoteTargets().get(room.getWolfVoteTargets().size() - 1));
            }
        }

        if (usePoison && poisonTargetId != null && room.isPlayerAlive(poisonTargetId)) {
            room.setWitchPoisonUsed(true);
            room.setWitchPoisonTarget(poisonTargetId);
        }

        WitchActionRes res = WitchActionRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .setAntidoteUsed(room.isWitchAntidoteUsed())
                .setPoisonUsed(room.isWitchPoisonUsed())
                .build();
        messageService.sendToPlayer(playerId, MessageType.WITCH_ACTION_RES, res);

        Map<String, Object> data = new HashMap<>();
        data.put("witchId", playerId);
        data.put("useAntidote", useAntidote);
        data.put("usePoison", usePoison);
        data.put("poisonTargetId", poisonTargetId);
        recordFrame(room, "WITCH_ACTION", data);

        return true;
    }

    public void handleHunterShot(Long roomId, Long playerId, Long targetId) {
        GameRoomSession room = roomManager.getRoom(roomId);
        if (room == null) {
            return;
        }

        Role role = room.getPlayerRole(playerId);
        if (role != Role.ROLE_HUNTER) {
            return;
        }

        if (!room.isHunterShot() || targetId == null || !room.isPlayerAlive(targetId)) {
            return;
        }

        room.setHunterTarget(targetId);
        room.setHunterShot(false);

        killPlayer(room, targetId, "猎人枪杀");

        Map<String, Object> data = new HashMap<>();
        data.put("hunterId", playerId);
        data.put("targetId", targetId);
        recordFrame(room, "HUNTER_SHOT", data);

        checkGameEnd(room);
    }

    private void processNightEnd(Long roomId) {
        nightTimeouts.remove(roomId);

        GameRoomSession room = roomManager.getRoom(roomId);
        if (room == null) {
            return;
        }

        List<Long> deadPlayers = new ArrayList<>();

        Long wolfTarget = null;
        if (!room.getWolfVoteTargets().isEmpty()) {
            wolfTarget = room.getWolfVoteTargets().get(room.getWolfVoteTargets().size() - 1);
        }

        if (wolfTarget != null && !wolfTarget.equals(room.getWitchAntidoteTarget())) {
            deadPlayers.add(wolfTarget);
            killPlayer(room, wolfTarget, "狼人击杀");
        }

        if (room.getWitchPoisonTarget() != null) {
            if (!deadPlayers.contains(room.getWitchPoisonTarget())) {
                deadPlayers.add(room.getWitchPoisonTarget());
            }
            killPlayer(room, room.getWitchPoisonTarget(), "女巫毒杀");
        }

        startDayPhase(roomId, deadPlayers);
    }

    private void handlePhaseError(GameRoomSession room, Exception e) {
        room.setLastError(e.getMessage());
        room.setLastErrorTime(System.currentTimeMillis());
        room.setPhaseProcessing(false);

        if (room.getRetryCount() < MAX_RETRY_COUNT) {
            scheduleRetry(room);
        } else {
            forceEndGame(room);
        }
    }

    private void startDayPhase(Long roomId, List<Long> deadPlayers) {
        GameRoomSession room = roomManager.getRoom(roomId);
        if (room == null) {
            return;
        }

        try {
            room.setPhaseProcessing(true);
            voiceService.closeWolfVoiceRoom(roomId);

            roomManager.updateRoomPhase(roomId, GamePhase.PHASE_DAY);
            room.setPhaseStartTime(System.currentTimeMillis());
            room.setPhaseEndTime(System.currentTimeMillis() + 30000);

            DayStartNotify notify = DayStartNotify.newBuilder()
                    .setRoomId(roomId)
                    .setDayNumber(room.getDayNumber())
                    .addAllDeadPlayerIds(deadPlayers)
                    .build();
            broadcastToRoom(room, MessageType.DAY_START_NOTIFY, notify);

            Map<String, Object> data = new HashMap<>();
            data.put("deadPlayers", deadPlayers);
            recordFrame(room, "DAY_START", data);

            if (checkGameEnd(room)) {
                return;
            }

            for (Long deadId : deadPlayers) {
                Role deadRole = room.getPlayerRole(deadId);
                if (deadRole == Role.ROLE_HUNTER) {
                    room.setHunterShot(true);
                    startHunterShotPhase(room, deadId);
                    return;
                }
            }

            room.setPhaseProcessing(false);
            startSpeechPhase(roomId);
        } catch (Exception e) {
            logger.error("Failed to start day phase for room {}", roomId, e);
            handlePhaseError(room, e);
        }
    }

    private void startHunterShotPhase(GameRoomSession room, Long hunterId) {
        HunterShotNotify hunterNotify = HunterShotNotify.newBuilder()
                .setRoomId(room.getRoomId())
                .setHunterId(hunterId)
                .build();
        broadcastToRoom(room, MessageType.HUNTER_SHOT_NOTIFY, hunterNotify);

        if (aiService.isAiPlayer(hunterId)) {
            aiService.handleHunterShotAi(room, hunterId);
        }

        Runnable timeout = () -> {
            try {
                hunterTimeouts.remove(room.getRoomId());
                if (room.isHunterShot()) {
                    logger.info("Hunter {} in room {} didn't shoot, continuing", hunterId, room.getRoomId());
                    room.setHunterShot(false);
                    startSpeechPhase(room.getRoomId());
                }
            } catch (Exception e) {
                logger.error("Hunter shot timeout error for room {}", room.getRoomId(), e);
            }
        };
        hunterTimeouts.put(room.getRoomId(), timeout);
        gameScheduler.schedule(timeout, HUNTER_SHOT_DURATION, TimeUnit.MILLISECONDS);
    }

    private void startSpeechPhase(Long roomId) {
        GameRoomSession room = roomManager.getRoom(roomId);
        if (room == null) {
            return;
        }

        try {
            room.setPhaseProcessing(true);
            roomManager.updateRoomPhase(roomId, GamePhase.PHASE_SPEECH);
            room.setPhaseStartTime(System.currentTimeMillis());

            List<Long> alivePlayers = room.getAlivePlayerIds();
            Collections.sort(alivePlayers);
            room.setSpeechOrder(alivePlayers);
            room.setSpeechIndex(0);

            long totalDuration = (long) alivePlayers.size() * SPEECH_DURATION;
            room.setPhaseEndTime(System.currentTimeMillis() + totalDuration);

            scheduleSpeeches(roomId, alivePlayers, 0);
            room.setPhaseProcessing(false);
        } catch (Exception e) {
            logger.error("Failed to start speech phase for room {}", roomId, e);
            handlePhaseError(room, e);
        }
    }

    private void scheduleSpeeches(Long roomId, List<Long> alivePlayers, int index) {
        if (index >= alivePlayers.size()) {
            startVotePhase(roomId);
            return;
        }

        GameRoomSession room = roomManager.getRoom(roomId);
        if (room == null) {
            return;
        }

        try {
            Long speakerId = alivePlayers.get(index);
            room.setCurrentSpeakerId(speakerId);
            room.setSpeechIndex(index);

            SpeechStartNotify notify = SpeechStartNotify.newBuilder()
                    .setRoomId(roomId)
                    .setSpeakerId(speakerId)
                    .setSpeechTime((int) (SPEECH_DURATION / 1000))
                    .build();
            broadcastToRoom(room, MessageType.SPEECH_START_NOTIFY, notify);

            Map<String, Object> data = new HashMap<>();
            data.put("speakerId", speakerId);
            data.put("index", index);
            recordFrame(room, "SPEECH_START", data);

            Runnable timeout = () -> {
                try {
                    speechTimeouts.remove(roomId);
                    SpeechEndNotify endNotify = SpeechEndNotify.newBuilder()
                            .setRoomId(roomId)
                            .setSpeakerId(speakerId)
                            .build();
                    broadcastToRoom(room, MessageType.SPEECH_END_NOTIFY, endNotify);

                    recordFrame(room, "SPEECH_END", data);
                    scheduleSpeeches(roomId, alivePlayers, index + 1);
                } catch (Exception e) {
                    logger.error("Speech timeout error for room {}", roomId, e);
                    handlePhaseError(room, e);
                }
            };

            speechTimeouts.put(roomId, timeout);
            gameScheduler.schedule(timeout, SPEECH_DURATION, TimeUnit.MILLISECONDS);
        } catch (Exception e) {
            logger.error("Failed to schedule speech for room {}", roomId, e);
            handlePhaseError(room, e);
        }
    }

    private void startVotePhase(Long roomId) {
        GameRoomSession room = roomManager.getRoom(roomId);
        if (room == null) {
            return;
        }

        try {
            room.setPhaseProcessing(true);
            roomManager.updateRoomPhase(roomId, GamePhase.PHASE_VOTE);
            room.setPhaseStartTime(System.currentTimeMillis());
            room.setPhaseEndTime(System.currentTimeMillis() + VOTE_DURATION);
            room.setCurrentSpeakerId(null);
            room.getVotes().clear();

            recordFrame(room, "VOTE_START", null);

            Runnable timeout = () -> {
                try {
                    voteTimeouts.remove(roomId);
                    processVoteEnd(roomId);
                } catch (Exception e) {
                    logger.error("Vote timeout error for room {}", roomId, e);
                    handlePhaseError(room, e);
                }
            };
            voteTimeouts.put(roomId, timeout);
            gameScheduler.schedule(timeout, VOTE_DURATION, TimeUnit.MILLISECONDS);

            room.setPhaseProcessing(false);
        } catch (Exception e) {
            logger.error("Failed to start vote phase for room {}", roomId, e);
            handlePhaseError(room, e);
        }
    }

    public void handleVote(Long roomId, Long playerId, Long targetId) {
        GameRoomSession room = roomManager.getRoom(roomId);
        if (room == null || room.getPhase() != GamePhase.PHASE_VOTE) {
            return;
        }

        if (!room.isPlayerAlive(playerId) || (targetId != null && !room.isPlayerAlive(targetId))) {
            return;
        }

        if (targetId == null) {
            room.getVotes().put(playerId, -1L);
        } else {
            room.getVotes().put(playerId, targetId);
        }
    }

    private void processVoteEnd(Long roomId) {
        voteTimeouts.remove(roomId);

        GameRoomSession room = roomManager.getRoom(roomId);
        if (room == null) {
            return;
        }

        try {
            room.setPhaseProcessing(true);

            Map<Long, Integer> voteCount = new HashMap<>();
            List<VoteInfo> voteInfos = new ArrayList<>();

            for (Map.Entry<Long, Long> entry : room.getVotes().entrySet()) {
                Long voterId = entry.getKey();
                Long targetId = entry.getValue();

                if (targetId != -1) {
                    voteCount.put(targetId, voteCount.getOrDefault(targetId, 0) + 1);
                }

                VoteInfo voteInfo = VoteInfo.newBuilder()
                        .setVoterId(voterId)
                        .setTargetId(targetId == -1 ? 0 : targetId)
                        .build();
                voteInfos.add(voteInfo);
            }

            Long eliminatedId = null;
            int maxVotes = 0;
            for (Map.Entry<Long, Integer> entry : voteCount.entrySet()) {
                if (entry.getValue() > maxVotes) {
                    maxVotes = entry.getValue();
                    eliminatedId = entry.getKey();
                }
            }

            if (eliminatedId != null) {
                killPlayer(room, eliminatedId, "投票处决");
            }

            VoteResultNotify notify = VoteResultNotify.newBuilder()
                    .setRoomId(roomId)
                    .setDayNumber(room.getDayNumber())
                    .addAllVotes(voteInfos)
                    .setEliminatedId(eliminatedId != null ? eliminatedId : 0)
                    .build();
            broadcastToRoom(room, MessageType.VOTE_RESULT_NOTIFY, notify);

            Map<String, Object> data = new HashMap<>();
            data.put("votes", room.getVotes());
            data.put("eliminatedId", eliminatedId);
            recordFrame(room, "VOTE_END", data);

            if (checkGameEnd(room)) {
                return;
            }

            if (eliminatedId != null) {
                Role eliminatedRole = room.getPlayerRole(eliminatedId);
                if (eliminatedRole == Role.ROLE_HUNTER) {
                    room.setHunterShot(true);
                    startHunterShotPhase(room, eliminatedId);
                    return;
                }
            }

            room.setPhaseProcessing(false);
            roomManager.incrementDayNumber(roomId);
            startNightPhase(roomId);
        } catch (Exception e) {
            logger.error("Failed to process vote end for room {}", roomId, e);
            handlePhaseError(room, e);
        }
    }

    private void killPlayer(GameRoomSession room, Long playerId, String reason) {
        room.setPlayerStatus(playerId, PlayerStatus.STATUS_DEAD);
        room.getDeadPlayers().add(playerId);

        PlayerDeathNotify notify = PlayerDeathNotify.newBuilder()
                .setRoomId(room.getRoomId())
                .setPlayerId(playerId)
                .setDeathReason(reason)
                .setDayNumber(room.getDayNumber())
                .build();
        broadcastToRoom(room, MessageType.PLAYER_DEATH_NOTIFY, notify);
    }

    private boolean checkGameEnd(GameRoomSession room) {
        int wolfCount = room.countAliveByRole(Role.ROLE_WEREWOLF);
        int villagerCount = room.getAlivePlayerIds().size() - wolfCount;

        GameResult result = GameResult.RESULT_NONE;

        if (wolfCount == 0) {
            result = GameResult.RESULT_VILLAGER_WIN;
        } else if (wolfCount >= villagerCount) {
            result = GameResult.RESULT_WEREWOLF_WIN;
        }

        if (result != GameResult.RESULT_NONE) {
            endGame(room, result);
            return true;
        }

        return false;
    }

    private void endGame(GameRoomSession room, GameResult result) {
        roomManager.updateRoomPhase(room.getRoomId(), GamePhase.PHASE_ENDED);

        List<PlayerInfo> finalStates = buildPlayerInfoList(room);

        Long recordId = replayService.endRecording(room, result);

        GameEndNotify notify = GameEndNotify.newBuilder()
                .setRoomId(room.getRoomId())
                .setResult(result)
                .addAllFinalStates(finalStates)
                .setRecordId(recordId)
                .build();
        broadcastToRoom(room, MessageType.GAME_END_NOTIFY, notify);

        Map<String, Object> data = new HashMap<>();
        data.put("result", result.name());
        recordFrame(room, "GAME_END", data);

        nightTimeouts.remove(room.getRoomId());
        speechTimeouts.remove(room.getRoomId());
        voteTimeouts.remove(room.getRoomId());
        hunterTimeouts.remove(room.getRoomId());

        Long matchId = roomMatchIds.remove(room.getRoomId());
        if (matchId != null) {
            try {
                rankService.updateRatingsAfterGame(room, result, matchId);
            } catch (Exception e) {
                logger.error("Failed to update rank ratings for room {}", room.getRoomId(), e);
            }
        }

        aiService.removeAllAiFromRoom(room.getRoomId());

        voiceService.closeWolfVoiceRoom(room.getRoomId());
    }

    private List<PlayerInfo> buildPlayerInfoList(GameRoomSession room) {
        List<PlayerInfo> playerInfos = new ArrayList<>();
        for (PlayerSession player : room.getPlayerList()) {
            PlayerInfo info = PlayerInfo.newBuilder()
                    .setPlayerId(player.getPlayerId())
                    .setNickname(player.getNickname())
                    .setSeat(player.getSeat() != null ? player.getSeat() : 0)
                    .setRole(room.getPlayerRole(player.getPlayerId()) != null ?
                            room.getPlayerRole(player.getPlayerId()) : Role.ROLE_UNKNOWN)
                    .setStatus(room.getPlayerStatus(player.getPlayerId()))
                    .setIsHost(player.isHost())
                    .setIsOnline(player.isOnline())
                    .build();
            playerInfos.add(info);
        }
        return playerInfos;
    }

    private void broadcastToRoom(GameRoomSession room, MessageType type, com.google.protobuf.Message message) {
        for (PlayerSession player : room.getPlayerList()) {
            if (player.isOnline() && player.getChannel() != null) {
                messageService.sendToChannel(player.getChannel(), type, message);
            }
        }
    }

    private void recordFrame(GameRoomSession room, String eventType, Map<String, Object> eventData) {
        try {
            String data = eventData != null ? objectMapper.writeValueAsString(eventData) : null;
            replayService.recordFrame(room, eventType, data, buildPlayerInfoList(room));
        } catch (JsonProcessingException e) {
            logger.error("Failed to record frame", e);
        }
    }

    public GameStateSnapshot getGameStateSnapshot(Long roomId, Long playerId) {
        GameRoomSession room = roomManager.getRoom(roomId);
        if (room == null) {
            return null;
        }

        GameStateSnapshot.Builder builder = GameStateSnapshot.newBuilder()
                .setRoomId(roomId)
                .setPhase(room.getPhase())
                .setDayNumber(room.getDayNumber())
                .setPhaseStartTime(room.getPhaseStartTime())
                .setPhaseEndTime(room.getPhaseEndTime())
                .setWitchAntidoteUsed(room.isWitchAntidoteUsed())
                .setWitchPoisonUsed(room.isWitchPoisonUsed())
                .setHunterPendingShot(room.isHunterShot());

        if (room.getCurrentSpeakerId() != null) {
            builder.setCurrentSpeakerId(room.getCurrentSpeakerId());
        }

        for (Long wolfTarget : room.getWolfVoteTargets()) {
            builder.addWolfVoteTargets(wolfTarget);
        }

        for (Map.Entry<Long, Long> voteEntry : room.getVotes().entrySet()) {
            VoteInfo voteInfo = VoteInfo.newBuilder()
                    .setVoterId(voteEntry.getKey())
                    .setTargetId(voteEntry.getValue() == -1 ? 0 : voteEntry.getValue())
                    .build();
            builder.addCurrentVotes(voteInfo);
        }

        List<PlayerInfo> playerInfos = buildPlayerInfoList(room);
        builder.addAllPlayers(playerInfos);

        Role playerRole = room.getPlayerRole(playerId);
        if (playerRole != null) {
            builder.setMyRole(playerRole);

            if (playerRole == Role.ROLE_WEREWOLF) {
                List<Long> wolfIds = room.getPlayerIdsByRole(Role.ROLE_WEREWOLF);
                for (Long wolfId : wolfIds) {
                    if (!wolfId.equals(playerId)) {
                        builder.addTeammateIds(wolfId);
                    }
                }
            }
        }

        for (Long deadId : room.getDeadPlayers()) {
            builder.addDeadPlayerIds(deadId);
        }

        return builder.build();
    }

    private Header buildSuccessHeader() {
        return Header.newBuilder()
                .setCode(0)
                .setMessage("success")
                .setTimestamp(System.currentTimeMillis())
                .build();
    }

    public void cancelAllTimeouts(Long roomId) {
        Runnable hunterTimeout = hunterTimeouts.remove(roomId);
        if (hunterTimeout != null) {
            gameScheduler.remove(hunterTimeout);
        }
        Runnable nightTimeout = nightTimeouts.remove(roomId);
        if (nightTimeout != null) {
            gameScheduler.remove(nightTimeout);
        }

        Runnable speechTimeout = speechTimeouts.remove(roomId);
        if (speechTimeout != null) {
            gameScheduler.remove(speechTimeout);
        }

        Runnable voteTimeout = voteTimeouts.remove(roomId);
        if (voteTimeout != null) {
            gameScheduler.remove(voteTimeout);
        }
    }
}
