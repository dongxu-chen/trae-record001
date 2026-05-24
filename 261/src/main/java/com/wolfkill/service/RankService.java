package com.wolfkill.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.wolfkill.entity.PlayerStats;
import com.wolfkill.entity.RankMatch;
import com.wolfkill.entity.RankSeason;
import com.wolfkill.manager.PlayerManager;
import com.wolfkill.manager.RoomManager;
import com.wolfkill.model.GameRoomSession;
import com.wolfkill.model.PlayerSession;
import com.wolfkill.protocol.*;
import com.wolfkill.repository.PlayerStatsRepository;
import com.wolfkill.repository.RankMatchRepository;
import com.wolfkill.repository.RankSeasonRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

@Service
public class RankService {

    private static final Logger logger = LoggerFactory.getLogger(RankService.class);

    private static final int[] RANK_THRESHOLDS = new int[]{
            0, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 2000, 2200
    };

    private static final String[] RANK_NAMES = new String[]{
            "青铜", "白银", "黄金", "铂金", "钻石", "大师", "宗师", "王者"
    };

    private static final int ELO_K_FACTOR = 32;
    private static final int MATCH_TARGET_SIZE = 12;
    private static final int MAX_MATCH_WAIT_TIME = 120000;

    private final PlayerStatsRepository playerStatsRepository;
    private final RankSeasonRepository rankSeasonRepository;
    private final RankMatchRepository rankMatchRepository;
    private final PlayerManager playerManager;
    private final RoomManager roomManager;
    private final MessageService messageService;
    private final GameService gameService;
    private final ObjectMapper objectMapper;

    private final Map<String, List<Long>> matchQueue = new ConcurrentHashMap<>();
    private final Map<Long, Long> playerMatchTime = new ConcurrentHashMap<>();
    private final Map<Long, Long> playerCurrentMatch = new ConcurrentHashMap<>();
    private final AtomicLong matchIdGenerator = new AtomicLong(System.currentTimeMillis());

    private final ScheduledExecutorService matchScheduler = new ScheduledThreadPoolExecutor(4);

    public RankService(PlayerStatsRepository playerStatsRepository,
                       RankSeasonRepository rankSeasonRepository,
                       RankMatchRepository rankMatchRepository,
                       PlayerManager playerManager,
                       RoomManager roomManager,
                       MessageService messageService,
                       GameService gameService,
                       ObjectMapper objectMapper) {
        this.playerStatsRepository = playerStatsRepository;
        this.rankSeasonRepository = rankSeasonRepository;
        this.rankMatchRepository = rankMatchRepository;
        this.playerManager = playerManager;
        this.roomManager = roomManager;
        this.messageService = messageService;
        this.gameService = gameService;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public RankMatchRes startMatchmaking(Long playerId, String gameMode) {
        String seasonId = getCurrentSeasonId();
        if (seasonId == null) {
            return RankMatchRes.newBuilder()
                    .setHeader(buildErrorHeader(1, "当前没有活跃赛季"))
                    .build();
        }

        if (matchQueue.values().stream().anyMatch(list -> list.contains(playerId))) {
            return RankMatchRes.newBuilder()
                    .setHeader(buildErrorHeader(2, "您已在匹配队列中"))
                    .build();
        }

        PlayerStats stats = getOrCreatePlayerStats(playerId, seasonId);
        if (stats.getTotalGames() < 5) {
            return RankMatchRes.newBuilder()
                    .setHeader(buildErrorHeader(3, "需要完成5场定级赛才能排位"))
                    .build();
        }

        matchQueue.computeIfAbsent(gameMode, k -> new ArrayList<>()).add(playerId);
        playerMatchTime.put(playerId, System.currentTimeMillis());

        long matchId = matchIdGenerator.incrementAndGet();
        playerCurrentMatch.put(playerId, matchId);

        matchScheduler.schedule(() -> checkMatchFound(gameMode), 500, TimeUnit.MILLISECONDS);

        logger.info("Player {} entered matchmaking queue for mode {}", playerId, gameMode);

        return RankMatchRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .setMatchId(matchId)
                .setExpectedWaitTime(estimateWaitTime(gameMode))
                .build();
    }

    @Transactional
    public RankMatchCancelRes cancelMatchmaking(Long playerId, Long matchId) {
        String seasonId = getCurrentSeasonId();
        if (seasonId == null) {
            return RankMatchCancelRes.newBuilder()
                    .setHeader(buildErrorHeader(1, "当前没有活跃赛季"))
                    .build();
        }

        boolean removed = false;
        for (List<Long> list : matchQueue.values()) {
            if (list.remove(playerId)) {
                removed = true;
            }
        }

        playerMatchTime.remove(playerId);
        playerCurrentMatch.remove(playerId);

        if (!removed) {
            return RankMatchCancelRes.newBuilder()
                    .setHeader(buildErrorHeader(2, "您不在匹配队列中"))
                    .build();
        }

        logger.info("Player {} cancelled matchmaking", playerId);

        return RankMatchCancelRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .build();
    }

    private void checkMatchFound(String gameMode) {
        List<Long> queue = matchQueue.get(gameMode);
        if (queue == null || queue.size() < MATCH_TARGET_SIZE) {
            Long oldestPlayer = queue != null ? queue.stream()
                    .min((a, b) -> Long.compare(playerMatchTime.getOrDefault(a, 0L), playerMatchTime.getOrDefault(b, 0L)))
                    .orElse(null);

            if (oldestPlayer != null) {
                long waitTime = System.currentTimeMillis() - playerMatchTime.getOrDefault(oldestPlayer, 0L);
                if (waitTime > MAX_MATCH_WAIT_TIME && queue.size() >= 6) {
                    createMatch(gameMode, new ArrayList<>(queue));
                }
            }
            return;
        }

        List<Long> matchedPlayers = new ArrayList<>(queue);
        createMatch(gameMode, matchedPlayers);
    }

    @Transactional
    public void createMatch(String gameMode, List<Long> playerIds) {
        if (playerIds.size() < 6) {
            return;
        }

        String seasonId = getCurrentSeasonId();
        if (seasonId == null) {
            return;
        }

        List<PlayerStats> allStats = new ArrayList<>();
        for (Long playerId : playerIds) {
            PlayerStats stats = getOrCreatePlayerStats(playerId, seasonId);
            allStats.add(stats);
        }

        Collections.sort(allStats, (a, b) -> Integer.compare(b.getElo(), a.getElo()));

        List<Long> team1 = new ArrayList<>();
        List<Long> team2 = new ArrayList<>();
        int team1Elo = 0, team2Elo = 0;

        for (int i = 0; i < allStats.size(); i++) {
            PlayerStats stats = allStats.get(i);
            if (i % 2 == 0) {
                team1.add(stats.getPlayerId());
                team1Elo += stats.getElo();
            } else {
                team2.add(stats.getPlayerId());
                team2Elo += stats.getElo();
            }
        }

        int team1AvgElo = team1Elo / team1.size();
        int team2AvgElo = team2Elo / team2.size();

        Long matchId = matchIdGenerator.incrementAndGet();

        RankMatch match = new RankMatch();
        match.setMatchId(matchId);
        match.setSeasonId(seasonId);
        match.setGameMode(gameMode);
        match.setStatus("MATCHED");
        match.setTeam1AvgElo(team1AvgElo);
        match.setTeam2AvgElo(team2AvgElo);

        try {
            match.setTeam1Players(objectMapper.writeValueAsString(team1));
            match.setTeam2Players(objectMapper.writeValueAsString(team2));
        } catch (JsonProcessingException e) {
            logger.error("Failed to serialize team players", e);
            return;
        }

        match = rankMatchRepository.save(match);

        Long roomId = createRankRoom(playerIds, team1, team2);
        match.setRoomId(roomId);
        rankMatchRepository.save(match);

        notifyMatchFound(matchId, roomId, team1, team2, team1AvgElo, team2AvgElo);

        for (Long playerId : playerIds) {
            matchQueue.values().forEach(list -> list.remove(playerId));
            playerMatchTime.remove(playerId);
            playerCurrentMatch.put(playerId, matchId);
        }

        logger.info("Match {} created with {} players, team1 avg elo: {}, team2 avg elo: {}",
                matchId, playerIds.size(), team1AvgElo, team2AvgElo);
    }

    private Long createRankRoom(List<Long> playerIds, List<Long> team1, List<Long> team2) {
        Long hostId = playerIds.get(0);
        PlayerSession host = playerManager.getPlayer(hostId);

        GameRoomSession room = roomManager.createRoom(hostId, "排位赛 #" + System.currentTimeMillis(), 12, "");

        for (Long playerId : playerIds) {
            PlayerSession player = playerManager.getPlayer(playerId);
            if (player != null) {
                roomManager.joinRoom(room.getRoomId(), player, "");
            }
        }

        return room.getRoomId();
    }

    private void notifyMatchFound(long matchId, long roomId, List<Long> team1, List<Long> team2,
                                  int team1AvgElo, int team2AvgElo) {
        List<PlayerInfo> team1Infos = buildPlayerInfoList(team1);
        List<PlayerInfo> team2Infos = buildPlayerInfoList(team2);

        RankMatchFoundNotify notify = RankMatchFoundNotify.newBuilder()
                .setMatchId(matchId)
                .setRoomId(roomId)
                .setCountdown(10)
                .addAllTeam1(team1Infos)
                .addAllTeam2(team2Infos)
                .build();

        for (Long playerId : team1) {
            PlayerSession player = playerManager.getPlayer(playerId);
            if (player != null && player.isOnline() && player.getChannel() != null) {
                messageService.sendToChannel(player.getChannel(), MessageType.RANK_MATCH_FOUND_NOTIFY, notify);
            }
        }

        for (Long playerId : team2) {
            PlayerSession player = playerManager.getPlayer(playerId);
            if (player != null && player.isOnline() && player.getChannel() != null) {
                messageService.sendToChannel(player.getChannel(), MessageType.RANK_MATCH_FOUND_NOTIFY, notify);
            }
        }

        matchScheduler.schedule(() -> {
            GameRoomSession room = roomManager.getRoom(roomId);
            if (room != null) {
                gameService.startGame(roomId, team1.get(0));
            }
        }, 10, TimeUnit.SECONDS);
    }

    private List<PlayerInfo> buildPlayerInfoList(List<Long> playerIds) {
        List<PlayerInfo> result = new ArrayList<>();
        for (Long playerId : playerIds) {
            PlayerSession player = playerManager.getPlayer(playerId);
            if (player != null) {
                PlayerInfo info = PlayerInfo.newBuilder()
                        .setPlayerId(playerId)
                        .setNickname(player.getNickname())
                        .setIsOnline(player.isOnline())
                        .build();
                result.add(info);
            }
        }
        return result;
    }

    @Transactional
    public void updateRatingsAfterGame(GameRoomSession room, GameResult result, long matchId) {
        RankMatch match = rankMatchRepository.findByMatchId(matchId).orElse(null);
        if (match == null) {
            return;
        }

        try {
            List<Long> team1 = objectMapper.readValue(match.getTeam1Players(),
                    objectMapper.getTypeFactory().constructCollectionType(List.class, Long.class));
            List<Long> team2 = objectMapper.readValue(match.getTeam2Players(),
                    objectMapper.getTypeFactory().constructCollectionType(List.class, Long.class));

            boolean team1Win = result == GameResult.RESULT_VILLAGER_WIN;
            String seasonId = match.getSeasonId();

            for (Long playerId : team1) {
                updatePlayerRating(playerId, seasonId, team1Win, room);
            }

            for (Long playerId : team2) {
                updatePlayerRating(playerId, seasonId, !team1Win, room);
            }

            match.setWinnerTeam(team1Win ? 1 : 2);
            match.setEndTime(LocalDateTime.now());
            match.setStatus("COMPLETED");
            match.setDurationSeconds((int) TimeUnit.MILLISECONDS.toSeconds(
                    System.currentTimeMillis() - match.getStartTime().atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()));
            match.setTotalDays(room.getDayNumber());
            rankMatchRepository.save(match);

            RankSeason season = rankSeasonRepository.findBySeasonId(seasonId).orElse(null);
            if (season != null) {
                season.setTotalGames(season.getTotalGames() + 1);
                rankSeasonRepository.save(season);
            }

        } catch (JsonProcessingException e) {
            logger.error("Failed to process match result", e);
        }
    }

    @Transactional
    public void updatePlayerRating(Long playerId, String seasonId, boolean won, GameRoomSession room) {
        PlayerStats stats = getOrCreatePlayerStats(playerId, seasonId);

        Role role = room.getPlayerRole(playerId);
        int oldElo = stats.getElo();

        double expectedScore = 1.0 / (1.0 + Math.pow(10, (1200 - oldElo) / 400.0));
        double actualScore = won ? 1.0 : 0.0;

        int kFactor = getKFactor(stats, won);
        int eloChange = (int) Math.round(kFactor * (actualScore - expectedScore));

        int newElo = Math.max(0, oldElo + eloChange);

        stats.setElo(newElo);
        stats.setTotalGames(stats.getTotalGames() + 1);

        if (won) {
            stats.setWins(stats.getWins() + 1);
            stats.setWinStreak(stats.getWinStreak() + 1);
            stats.setMaxWinStreak(Math.max(stats.getMaxWinStreak(), stats.getWinStreak()));
        } else {
            stats.setLosses(stats.getLosses() + 1);
            stats.setWinStreak(0);
        }

        updateRoleStats(stats, role, won);

        updateRankLevel(stats);

        stats.setLastGameTime(LocalDateTime.now());

        playerStatsRepository.save(stats);

        RankSeason season = rankSeasonRepository.findBySeasonId(seasonId).orElse(null);
        if (season != null) {
            int currentTotal = season.getTotalPlayers() != null ? season.getTotalPlayers() : 0;
            season.setTotalPlayers(Math.max(currentTotal, (int) playerStatsRepository.count()));
            rankSeasonRepository.save(season);
        }

        logger.info("Player {} rating updated: {} -> {}, change: {}, won: {}",
                playerId, oldElo, newElo, eloChange, won);
    }

    private int getKFactor(PlayerStats stats, boolean won) {
        int totalGames = stats.getTotalGames();
        if (totalGames < 30) return 40;
        if (totalGames < 100) return 32;
        if (stats.getElo() >= 2000) return 24;
        if (stats.getElo() >= 2400) return 16;
        return 32;
    }

    private void updateRoleStats(PlayerStats stats, Role role, boolean won) {
        if (role == null) return;

        switch (role) {
            case ROLE_WEREWOLF -> {
                stats.setWolfGames(stats.getWolfGames() + 1);
                if (won) stats.setWolfWins(stats.getWolfWins() + 1);
            }
            case ROLE_VILLAGER -> {
                stats.setVillagerGames(stats.getVillagerGames() + 1);
                if (won) stats.setVillagerWins(stats.getVillagerWins() + 1);
            }
            case ROLE_SEER -> {
                stats.setSeerGames(stats.getSeerGames() + 1);
                if (won) stats.setSeerWins(stats.getSeerWins() + 1);
            }
            case ROLE_WITCH -> {
                stats.setWitchGames(stats.getWitchGames() + 1);
                if (won) stats.setWitchWins(stats.getWitchWins() + 1);
            }
            case ROLE_HUNTER -> {
                stats.setHunterGames(stats.getHunterGames() + 1);
                if (won) stats.setHunterWins(stats.getHunterWins() + 1);
            }
            case ROLE_GUARD -> {
                stats.setGuardGames(stats.getGuardGames() + 1);
                if (won) stats.setGuardWins(stats.getGuardWins() + 1);
            }
        }
    }

    private void updateRankLevel(PlayerStats stats) {
        int elo = stats.getElo();
        int rankLevel = 0;

        for (int i = RANK_THRESHOLDS.length - 1; i >= 0; i--) {
            if (elo >= RANK_THRESHOLDS[i]) {
                rankLevel = i;
                break;
            }
        }

        stats.setRankLevel(rankLevel);
        stats.setRankName(RANK_NAMES[Math.min(rankLevel, RANK_NAMES.length - 1)]);
    }

    public PlayerStats getOrCreatePlayerStats(Long playerId, String seasonId) {
        return playerStatsRepository.findByPlayerIdAndSeasonId(playerId, seasonId)
                .orElseGet(() -> {
                    PlayerStats stats = new PlayerStats();
                    stats.setPlayerId(playerId);
                    stats.setSeasonId(seasonId);
                    stats.setElo(getBaseElo());
                    stats.setRankLevel(0);
                    stats.setRankName("青铜");
                    return playerStatsRepository.save(stats);
                });
    }

    private int getBaseElo() {
        RankSeason season = rankSeasonRepository.findByActiveTrue().orElse(null);
        return season != null ? season.getBaseElo() : 1200;
    }

    public String getCurrentSeasonId() {
        RankSeason season = rankSeasonRepository.findByActiveTrue().orElse(null);
        return season != null ? season.getSeasonId() : null;
    }

    public RankSeasonInfoRes getSeasonInfo(Long playerId) {
        RankSeason season = rankSeasonRepository.findByActiveTrue().orElse(null);
        if (season == null) {
            return RankSeasonInfoRes.newBuilder()
                    .setHeader(buildErrorHeader(1, "当前没有活跃赛季"))
                    .build();
        }

        PlayerStats stats = null;
        RankPlayerInfo myStats = null;
        if (playerId != null) {
            stats = getOrCreatePlayerStats(playerId, season.getSeasonId());
            myStats = buildRankPlayerInfo(stats);
        }

        return RankSeasonInfoRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .setCurrentSeasonId(season.getSeasonId())
                .setSeasonName(season.getSeasonName())
                .setStartTime(season.getStartTime().atZone(ZoneId.systemDefault()).toInstant().toEpochMilli())
                .setEndTime(season.getEndTime().atZone(ZoneId.systemDefault()).toInstant().toEpochMilli())
                .setTotalPlayers(season.getTotalPlayers() != null ? season.getTotalPlayers() : 0)
                .setMyStats(myStats != null ? myStats : RankPlayerInfo.newBuilder().build())
                .build();
    }

    public RankLeaderboardRes getLeaderboard(Long playerId, String seasonId, int page, int size, String region) {
        if (seasonId == null) {
            seasonId = getCurrentSeasonId();
        }
        if (seasonId == null) {
            return RankLeaderboardRes.newBuilder()
                    .setHeader(buildErrorHeader(1, "赛季不存在"))
                    .build();
        }

        org.springframework.data.domain.Page<PlayerStats> statsPage =
                playerStatsRepository.findBySeasonIdOrderByEloDesc(seasonId,
                        org.springframework.data.domain.PageRequest.of(page, size));

        List<RankPlayerInfo> players = new ArrayList<>();
        int rank = page * size + 1;
        for (PlayerStats stats : statsPage.getContent()) {
            RankPlayerInfo info = buildRankPlayerInfo(stats);
            players.add(info.toBuilder().setRank(rank++).build());
        }

        RankPlayerInfo myRank = null;
        if (playerId != null) {
            PlayerStats myStats = playerStatsRepository.findByPlayerIdAndSeasonId(playerId, seasonId).orElse(null);
            if (myStats != null) {
                Long higherCount = playerStatsRepository.countPlayersWithHigherElo(seasonId, myStats.getElo());
                myRank = buildRankPlayerInfo(myStats).toBuilder()
                        .setRank(higherCount.intValue() + 1)
                        .build();
            }
        }

        return RankLeaderboardRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .addAllPlayers(players)
                .setMyRank(myRank != null ? myRank : RankPlayerInfo.newBuilder().build())
                .setTotal((int) statsPage.getTotalElements())
                .setSeasonId(seasonId)
                .build();
    }

    private RankPlayerInfo buildRankPlayerInfo(PlayerStats stats) {
        return RankPlayerInfo.newBuilder()
                .setPlayerId(stats.getPlayerId())
                .setNickname(playerManager.getPlayer(stats.getPlayerId()) != null ?
                        playerManager.getPlayer(stats.getPlayerId()).getNickname() : "玩家" + stats.getPlayerId())
                .setRank(0)
                .setRankName(stats.getRankName() != null ? stats.getRankName() : "青铜")
                .setElo(stats.getElo())
                .setWins(stats.getWins())
                .setLosses(stats.getLosses())
                .setWinStreak(stats.getWinStreak())
                .build();
    }

    private int estimateWaitTime(String gameMode) {
        List<Long> queue = matchQueue.get(gameMode);
        if (queue == null || queue.isEmpty()) {
            return 60;
        }
        int needed = MATCH_TARGET_SIZE - queue.size();
        return Math.max(0, needed * 10);
    }

    @Scheduled(fixedRate = 1000)
    public void checkMatchmakingQueues() {
        for (String gameMode : matchQueue.keySet()) {
            checkMatchFound(gameMode);
        }

        long now = System.currentTimeMillis();
        for (Map.Entry<Long, Long> entry : new ArrayList<>(playerMatchTime.entrySet())) {
            if (now - entry.getValue() > MAX_MATCH_WAIT_TIME * 2) {
                Long playerId = entry.getKey();
                cancelMatchmaking(playerId, 0L);
                logger.warn("Player {} removed from queue due to timeout", playerId);
            }
        }
    }

    private Header buildSuccessHeader() {
        return Header.newBuilder()
                .setCode(0)
                .setMessage("success")
                .setTimestamp(System.currentTimeMillis())
                .build();
    }

    private Header buildErrorHeader(int code, String message) {
        return Header.newBuilder()
                .setCode(code)
                .setMessage(message)
                .setTimestamp(System.currentTimeMillis())
                .build();
    }

    @Transactional
    public void initDefaultSeason() {
        if (rankSeasonRepository.findByActiveTrue().isPresent()) {
            return;
        }

        RankSeason season = new RankSeason();
        season.setSeasonId("S" + System.currentTimeMillis());
        season.setSeasonName("第一赛季");
        season.setStartTime(LocalDateTime.now());
        season.setEndTime(LocalDateTime.now().plusMonths(3));
        season.setActive(true);
        season.setTotalPlayers(0);
        season.setTotalGames(0);
        season.setBaseElo(1200);
        season.setKFactor(ELO_K_FACTOR);
        season.setDescription("狼人杀排位赛第一赛季");

        try {
            Map<String, Object> thresholds = new LinkedHashMap<>();
            for (int i = 0; i < RANK_NAMES.length; i++) {
                thresholds.put(RANK_NAMES[i], RANK_THRESHOLDS[i]);
            }
            season.setRankThresholds(objectMapper.writeValueAsString(thresholds));
        } catch (JsonProcessingException e) {
            logger.error("Failed to serialize rank thresholds", e);
        }

        rankSeasonRepository.save(season);
        logger.info("Default season initialized: {}", season.getSeasonName());
    }
}
