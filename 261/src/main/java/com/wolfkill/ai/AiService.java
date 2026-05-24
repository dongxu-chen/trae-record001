package com.wolfkill.ai;

import com.wolfkill.entity.Player;
import com.wolfkill.manager.PlayerManager;
import com.wolfkill.manager.RoomManager;
import com.wolfkill.model.GameRoomSession;
import com.wolfkill.model.PlayerSession;
import com.wolfkill.protocol.*;
import com.wolfkill.repository.PlayerRepository;
import com.wolfkill.service.GameService;
import com.wolfkill.service.MessageService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

@Service
public class AiService {

    private static final Logger logger = LoggerFactory.getLogger(AiService.class);

    private static final String[] AI_NAMES = {
            "小智", "小慧", "小明", "小红", "小刚", "小丽", "阿强", "阿美",
            "老王", "老李", "老张", "阿珍", "阿强", "美美", "帅帅", "酷酷"
    };

    private final PlayerManager playerManager;
    private final RoomManager roomManager;
    private final PlayerRepository playerRepository;
    private final GameService gameService;
    private final MessageService messageService;

    private final Map<Long, AiPlayer> aiPlayers = new ConcurrentHashMap<>();
    private final Map<Long, List<AiPlayer>> roomAiPlayers = new ConcurrentHashMap<>();
    private final ScheduledExecutorService aiScheduler = new ScheduledThreadPoolExecutor(8);
    private final AtomicLong aiIdGenerator = new AtomicLong(1000000);

    public AiService(PlayerManager playerManager, RoomManager roomManager,
                     PlayerRepository playerRepository, GameService gameService,
                     MessageService messageService) {
        this.playerManager = playerManager;
        this.roomManager = roomManager;
        this.playerRepository = playerRepository;
        this.gameService = gameService;
        this.messageService = messageService;
    }

    private static class AtomicLong {
        private long value;
        public AtomicLong(long initial) { this.value = initial; }
        public long incrementAndGet() { return ++value; }
    }

    public List<AiPlayer> fillRoomWithAi(Long roomId, Long requesterId, int count, int difficulty) {
        GameRoomSession room = roomManager.getRoom(roomId);
        if (room == null) {
            return Collections.emptyList();
        }

        if (!requesterId.equals(room.getHostId())) {
            return Collections.emptyList();
        }

        int availableSlots = room.getMaxPlayers() - room.getCurrentPlayers();
        int aiCount = Math.min(count, availableSlots);
        if (aiCount <= 0) {
            return Collections.emptyList();
        }

        List<AiPlayer> createdAis = new ArrayList<>();
        List<String> usedNames = new ArrayList<>();
        for (PlayerSession p : room.getPlayerList()) {
            usedNames.add(p.getNickname());
        }

        for (int i = 0; i < aiCount; i++) {
            AiPlayer ai = createAiPlayer(difficulty, usedNames);
            if (ai != null) {
                boolean joined = roomManager.joinRoom(roomId, ai, "");
                if (joined) {
                    aiPlayers.put(ai.getPlayerId(), ai);
                    roomAiPlayers.computeIfAbsent(roomId, k -> new ArrayList<>()).add(ai);
                    createdAis.add(ai);
                    usedNames.add(ai.getNickname());
                    logger.info("AI player {} joined room {}", ai.getNickname(), roomId);
                }
            }
        }

        if (!createdAis.isEmpty()) {
            scheduleAiActions(roomId);
        }

        return createdAis;
    }

    private AiPlayer createAiPlayer(int difficulty, List<String> usedNames) {
        long aiPlayerId = aiIdGenerator.incrementAndGet();
        String nickname = generateUniqueName(usedNames);

        Player player = new Player();
        player.setId(aiPlayerId);
        player.setNickname(nickname);
        player.setOnline(true);
        player.setSessionId(UUID.randomUUID().toString().replace("-", ""));
        playerRepository.save(player);

        AiPlayer ai = new AiPlayer(aiPlayerId, nickname, difficulty);
        ai.setSessionId(player.getSessionId());
        ai.setOnline(true);

        PlayerSession session = new PlayerSession();
        session.setPlayerId(aiPlayerId);
        session.setNickname(nickname);
        session.setSessionId(player.getSessionId());
        session.setOnline(true);
        session.setChannel(null);

        playerManager.getAllPlayers().put(aiPlayerId, session);

        return ai;
    }

    private String generateUniqueName(List<String> usedNames) {
        Random random = new Random();
        for (int i = 0; i < 100; i++) {
            String name = AI_NAMES[random.nextInt(AI_NAMES.length)];
            int suffix = random.nextInt(100);
            String fullName = suffix > 0 ? name + suffix : name;
            if (!usedNames.contains(fullName)) {
                return fullName;
            }
        }
        return "AI" + System.currentTimeMillis();
    }

    public void autoFillRoomIfNeeded(Long roomId) {
        GameRoomSession room = roomManager.getRoom(roomId);
        if (room == null || room.getPhase() != GamePhase.PHASE_WAITING) {
            return;
        }

        int playerCount = room.getCurrentPlayers();
        int minPlayers = 6;

        if (playerCount >= minPlayers && playerCount < room.getMaxPlayers()) {
            if (playerCount == minPlayers && room.isActive()) {
                return;
            }
        }

        if (playerCount > 0 && playerCount < minPlayers) {
            int needAi = minPlayers - playerCount;
            fillRoomWithAi(roomId, room.getHostId(), needAi, 2);
        }
    }

    public void scheduleAiActions(Long roomId) {
        GameRoomSession room = roomManager.getRoom(roomId);
        if (room == null) {
            return;
        }

        aiScheduler.scheduleAtFixedRate(() -> {
            try {
                processAiActions(roomId);
            } catch (Exception e) {
                logger.error("Error processing AI actions for room {}", roomId, e);
            }
        }, 1000, 500, TimeUnit.MILLISECONDS);
    }

    private void processAiActions(Long roomId) {
        GameRoomSession room = roomManager.getRoom(roomId);
        if (room == null || room.getPhase() == GamePhase.PHASE_ENDED) {
            return;
        }

        List<AiPlayer> ais = roomAiPlayers.get(roomId);
        if (ais == null || ais.isEmpty()) {
            return;
        }

        AiPlayer.GameContext context = buildGameContext(room);

        for (AiPlayer ai : ais) {
            if (!room.isPlayerAlive(ai.getPlayerId())) {
                continue;
            }

            Role role = room.getPlayerRole(ai.getPlayerId());
            if (role == null) {
                continue;
            }

            long now = System.currentTimeMillis();
            if (now - ai.getLastActionTime() < ai.getReactionDelay()) {
                continue;
            }

            switch (room.getPhase()) {
                case PHASE_NIGHT -> processNightAiAction(room, ai, role, context);
                case PHASE_SPEECH -> processSpeechAiAction(room, ai, context);
                case PHASE_VOTE -> processVoteAiAction(room, ai, role, context);
                default -> {}
            }

            ai.setLastActionTime(now);
        }
    }

    private void processNightAiAction(GameRoomSession room, AiPlayer ai, Role role, AiPlayer.GameContext context) {
        switch (role) {
            case ROLE_WEREWOLF -> {
                List<Long> targets = new ArrayList<>();
                for (Long playerId : room.getAlivePlayerIds()) {
                    Role targetRole = room.getPlayerRole(playerId);
                    if (targetRole != Role.ROLE_WEREWOLF) {
                        targets.add(playerId);
                    }
                }
                if (!targets.isEmpty() && Math.random() < ai.getAggression()) {
                    Long target = ai.chooseTarget(targets, role, context);
                    if (target != null) {
                        gameService.handleWolfKill(room.getRoomId(), ai.getPlayerId(), target);
                    }
                }
            }
            case ROLE_SEER -> {
                List<Long> targets = new ArrayList<>();
                for (Long playerId : room.getAlivePlayerIds()) {
                    if (!playerId.equals(ai.getPlayerId())) {
                        targets.add(playerId);
                    }
                }
                if (!targets.isEmpty() && Math.random() < 0.8) {
                    Long target = ai.chooseTarget(targets, role, context);
                    if (target != null) {
                        gameService.handleSeerCheck(room.getRoomId(), ai.getPlayerId(), target);

                        Role targetRole = room.getPlayerRole(target);
                        if (targetRole == Role.ROLE_WEREWOLF) {
                            ai.updateSuspected(target, 0.9);
                        } else {
                            ai.updateSuspected(target, 0.1);
                        }
                    }
                }
            }
            case ROLE_WITCH -> {
                if (!room.isWitchAntidoteUsed() && !room.getWolfVoteTargets().isEmpty()) {
                    Long killed = room.getWolfVoteTargets().get(room.getWolfVoteTargets().size() - 1);
                    if (ai.shouldUseAntidote(killed, context)) {
                        gameService.handleWitchAction(room.getRoomId(), ai.getPlayerId(), true, false, null);
                    }
                }
                if (!room.isWitchPoisonUsed() && ai.shouldUsePoison(context)) {
                    List<Long> targets = new ArrayList<>(ai.getSuspectedWolves());
                    targets.removeIf(id -> !room.isPlayerAlive(id));
                    if (!targets.isEmpty()) {
                        Long target = ai.chooseTarget(targets, role, context);
                        if (target != null) {
                            gameService.handleWitchAction(room.getRoomId(), ai.getPlayerId(), false, true, target);
                        }
                    }
                }
            }
            default -> {}
        }
    }

    private void processSpeechAiAction(GameRoomSession room, AiPlayer ai, AiPlayer.GameContext context) {
        if (room.getCurrentSpeakerId() == null || !room.getCurrentSpeakerId().equals(ai.getPlayerId())) {
            return;
        }

        if (Math.random() < 0.7) {
            Long target = null;
            if (!ai.getSuspectedWolves().isEmpty()) {
                target = ai.getSuspectedWolves().get((int) (Math.random() * ai.getSuspectedWolves().size()));
            }

            Role role = room.getPlayerRole(ai.getPlayerId());
            boolean isWolf = role == Role.ROLE_WEREWOLF;
            String speech = ai.generateSpeech(target, isWolf, !isWolf);

            ChatNotify notify = ChatNotify.newBuilder()
                    .setRoomId(room.getRoomId())
                    .setPlayerId(ai.getPlayerId())
                    .setNickname(ai.getNickname())
                    .setContent("[发言] " + speech)
                    .setTimestamp(System.currentTimeMillis())
                    .build();

            for (PlayerSession player : room.getPlayerList()) {
                if (player.isOnline() && player.getChannel() != null) {
                    messageService.sendToChannel(player.getChannel(), MessageType.CHAT_NOTIFY, notify);
                }
            }
        }
    }

    private void processVoteAiAction(GameRoomSession room, AiPlayer ai, Role role, AiPlayer.GameContext context) {
        if (room.getVotes().containsKey(ai.getPlayerId())) {
            return;
        }

        if (Math.random() < 0.9) {
            List<Long> alivePlayers = room.getAlivePlayerIds();
            alivePlayers.remove(ai.getPlayerId());

            if (!alivePlayers.isEmpty()) {
                Long target = ai.chooseTarget(alivePlayers, role, context);
                gameService.handleVote(room.getRoomId(), ai.getPlayerId(), target);
            }
        }
    }

    public void handleHunterShotAi(GameRoomSession room, Long hunterId) {
        AiPlayer ai = aiPlayers.get(hunterId);
        if (ai == null) {
            return;
        }

        if (!room.isPlayerAlive(hunterId) || room.getPlayerRole(hunterId) != Role.ROLE_HUNTER) {
            return;
        }

        AiPlayer.GameContext context = buildGameContext(room);

        aiScheduler.schedule(() -> {
            if (ai.shouldShoot(context)) {
                List<Long> candidates = new ArrayList<>(ai.getSuspectedWolves());
                candidates.removeIf(id -> !room.isPlayerAlive(id));

                if (candidates.isEmpty()) {
                    candidates = new ArrayList<>(room.getAlivePlayerIds());
                    candidates.remove(hunterId);
                }

                if (!candidates.isEmpty()) {
                    Long target = ai.chooseTarget(candidates, Role.ROLE_HUNTER, context);
                    if (target != null) {
                        gameService.handleHunterShot(room.getRoomId(), hunterId, target);
                    }
                }
            } else {
                gameService.handleHunterShot(room.getRoomId(), hunterId, null);
            }
        }, ai.getReactionDelay(), TimeUnit.MILLISECONDS);
    }

    private AiPlayer.GameContext buildGameContext(GameRoomSession room) {
        AiPlayer.GameContext context = new AiPlayer.GameContext();
        context.setRoomId(room.getRoomId());
        context.setDayNumber(room.getDayNumber());
        context.setPlayerRoles(new HashMap<>(room.getPlayerRoles()));
        context.setPlayerStatuses(new HashMap<>(room.getPlayerStatuses()));
        context.setDeadPlayers(new ArrayList<>(room.getDeadPlayers()));
        context.setVotes(new HashMap<>(room.getVotes()));
        return context;
    }

    public void removeAiFromRoom(Long roomId, Long aiPlayerId) {
        List<AiPlayer> ais = roomAiPlayers.get(roomId);
        if (ais != null) {
            ais.removeIf(ai -> ai.getPlayerId().equals(aiPlayerId));
        }
        aiPlayers.remove(aiPlayerId);
    }

    public void removeAllAiFromRoom(Long roomId) {
        List<AiPlayer> ais = roomAiPlayers.remove(roomId);
        if (ais != null) {
            for (AiPlayer ai : ais) {
                aiPlayers.remove(ai.getPlayerId());
                roomManager.leaveRoom(roomId, ai.getPlayerId());
            }
        }
    }

    public boolean isAiPlayer(Long playerId) {
        return aiPlayers.containsKey(playerId);
    }

    public List<AiPlayer> getRoomAiPlayers(Long roomId) {
        return roomAiPlayers.getOrDefault(roomId, Collections.emptyList());
    }
}
