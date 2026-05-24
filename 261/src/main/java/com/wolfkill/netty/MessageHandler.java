package com.wolfkill.netty;

import com.wolfkill.ai.AiPlayer;
import com.wolfkill.ai.AiService;
import com.wolfkill.manager.PlayerManager;
import com.wolfkill.manager.RoomManager;
import com.wolfkill.model.GameRoomSession;
import com.wolfkill.model.PlayerSession;
import com.wolfkill.protocol.*;
import com.wolfkill.service.GameService;
import com.wolfkill.service.MessageService;
import com.wolfkill.service.RankService;
import com.wolfkill.service.ReplayService;
import com.wolfkill.service.VoiceService;
import com.google.protobuf.InvalidProtocolBufferException;
import io.netty.channel.Channel;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.SimpleChannelInboundHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

@Component
public class MessageHandler extends SimpleChannelInboundHandler<MessageWrapper> {

    private static final Logger logger = LoggerFactory.getLogger(MessageHandler.class);

    private final PlayerManager playerManager;
    private final RoomManager roomManager;
    private final GameService gameService;
    private final MessageService messageService;
    private final ReplayService replayService;
    private final AiService aiService;
    private final VoiceService voiceService;
    private final RankService rankService;

    public MessageHandler(PlayerManager playerManager, RoomManager roomManager,
                          GameService gameService, MessageService messageService,
                          ReplayService replayService, AiService aiService,
                          VoiceService voiceService, RankService rankService) {
        this.playerManager = playerManager;
        this.roomManager = roomManager;
        this.gameService = gameService;
        this.messageService = messageService;
        this.replayService = replayService;
        this.aiService = aiService;
        this.voiceService = voiceService;
        this.rankService = rankService;
    }

    @Override
    protected void channelRead0(ChannelHandlerContext ctx, MessageWrapper wrapper) {
        try {
            switch (wrapper.getType()) {
                case HEARTBEAT_REQ -> handleHeartbeat(ctx, wrapper);
                case LOGIN_REQ -> handleLogin(ctx, wrapper);
                case RECONNECT_REQ -> handleReconnect(ctx, wrapper);
                case CREATE_ROOM_REQ -> handleCreateRoom(ctx, wrapper);
                case JOIN_ROOM_REQ -> handleJoinRoom(ctx, wrapper);
                case LEAVE_ROOM_REQ -> handleLeaveRoom(ctx, wrapper);
                case START_GAME_REQ -> handleStartGame(ctx, wrapper);
                case ROOM_LIST_REQ -> handleRoomList(ctx, wrapper);
                case WOLF_KILL_REQ -> handleWolfKill(ctx, wrapper);
                case SEER_CHECK_REQ -> handleSeerCheck(ctx, wrapper);
                case WITCH_ACTION_REQ -> handleWitchAction(ctx, wrapper);
                case HUNTER_SHOT_REQ -> handleHunterShot(ctx, wrapper);
                case VOTE_REQ -> handleVote(ctx, wrapper);
                case CHAT_REQ -> handleChat(ctx, wrapper);
                case RECORD_LIST_REQ -> handleRecordList(ctx, wrapper);
                case RECORD_PLAYBACK_REQ -> handleRecordPlayback(ctx, wrapper);
                case AI_FILL_REQ -> handleAiFill(ctx, wrapper);
                case VOICE_JOIN_REQ -> handleVoiceJoin(ctx, wrapper);
                case VOICE_LEAVE_REQ -> handleVoiceLeave(ctx, wrapper);
                case RANK_MATCH_REQ -> handleRankMatch(ctx, wrapper);
                case RANK_MATCH_CANCEL_REQ -> handleRankMatchCancel(ctx, wrapper);
                case RANK_LEADERBOARD_REQ -> handleRankLeaderboard(ctx, wrapper);
                case RANK_SEASON_INFO_REQ -> handleRankSeasonInfo(ctx, wrapper);
                default -> logger.warn("Unknown message type: {}", wrapper.getType());
            }
        } catch (Exception e) {
            logger.error("Error handling message: {}", wrapper.getType(), e);
        }
    }

    private void handleHeartbeat(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        HeartbeatReq req = HeartbeatReq.parseFrom(wrapper.getPayload());

        if (req.getPlayerId() > 0) {
            playerManager.updateHeartbeat(req.getPlayerId());
        }

        HeartbeatRes res = HeartbeatRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .setServerTime(System.currentTimeMillis())
                .build();
        messageService.sendToChannel(ctx.channel(), MessageType.HEARTBEAT_RES, res);
    }

    private void handleLogin(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        LoginReq req = LoginReq.parseFrom(wrapper.getPayload());

        PlayerSession player = playerManager.login(req.getNickname(), req.getToken(), ctx.channel());

        LoginRes res = LoginRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .setPlayerId(player.getPlayerId())
                .setNickname(player.getNickname())
                .setSessionId(player.getSessionId())
                .build();
        messageService.sendToChannel(ctx.channel(), MessageType.LOGIN_RES, res);
    }

    private void handleReconnect(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        ReconnectReq req = ReconnectReq.parseFrom(wrapper.getPayload());

        PlayerSession player = playerManager.reconnect(req.getPlayerId(), req.getSessionId(), ctx.channel());
        if (player == null) {
            ReconnectRes res = ReconnectRes.newBuilder()
                    .setHeader(buildErrorHeader(1, "Invalid session or reconnect window expired"))
                    .build();
            messageService.sendToChannel(ctx.channel(), MessageType.RECONNECT_RES, res);
            return;
        }

        GameRoomSession room = player.getCurrentRoomId() != null ?
                roomManager.getRoom(player.getCurrentRoomId()) : null;

        ReconnectRes.Builder builder = ReconnectRes.newBuilder()
                .setHeader(buildSuccessHeader());

        if (room != null) {
            if (player.getSavedRole() != null) {
                if (room.getPlayerRole(player.getPlayerId()) == null) {
                    room.setPlayerRole(player.getPlayerId(), player.getSavedRole());
                }
                if (room.getPlayerStatus(player.getPlayerId()) == com.wolfkill.protocol.PlayerStatus.STATUS_OFFLINE ||
                    room.getPlayerStatus(player.getPlayerId()) == com.wolfkill.protocol.PlayerStatus.STATUS_DISCONNECTED) {
                    if (player.getSavedStatus() != null) {
                        room.setPlayerStatus(player.getPlayerId(), player.getSavedStatus());
                    }
                }
            }

            room.getPlayer(player.getPlayerId()).setOnline(true);
            room.getPlayer(player.getPlayerId()).setChannel(ctx.channel());

            builder.setRoom(buildRoomInfo(room));

            Role role = room.getPlayerRole(player.getPlayerId());
            if (role != null) {
                builder.setRole(role);
            }

            GameStateSnapshot stateSnapshot = gameService.getGameStateSnapshot(room.getRoomId(), player.getPlayerId());
            if (stateSnapshot != null) {
                builder.setStateSnapshot(stateSnapshot);
            }

            if (room.getRecordId() != null) {
                List<RecordFrame> allFrames = replayService.getPlaybackFrames(room.getRecordId());
                int startIndex = Math.max(0, player.getMissedFramesIndex());
                if (startIndex < allFrames.size()) {
                    int endIndex = Math.min(startIndex + 100, allFrames.size());
                    builder.addAllMissedFrames(allFrames.subList(startIndex, endIndex));
                }
            }
        }

        messageService.sendToChannel(ctx.channel(), MessageType.RECONNECT_RES, builder.build());

        if (room != null) {
            sendRoleAssignmentOnReconnect(player, room);
            broadcastRoomInfo(room);
        }

        logger.info("Player {} reconnected to room {}, state fully restored",
                player.getPlayerId(), player.getCurrentRoomId());
    }

    private void sendRoleAssignmentOnReconnect(PlayerSession player, GameRoomSession room) {
        Role role = room.getPlayerRole(player.getPlayerId());
        if (role == null) {
            return;
        }

        RoleAssignNotify.Builder roleBuilder = RoleAssignNotify.newBuilder()
                .setPlayerId(player.getPlayerId())
                .setRole(role);

        if (role == Role.ROLE_WEREWOLF) {
            List<Long> wolfIds = room.getPlayerIdsByRole(Role.ROLE_WEREWOLF);
            for (Long wolfId : wolfIds) {
                if (!wolfId.equals(player.getPlayerId())) {
                    roleBuilder.addTeammateIds(wolfId);
                }
            }
        }

        messageService.sendToPlayer(player.getPlayerId(), MessageType.ROLE_ASSIGN_NOTIFY, roleBuilder.build());
    }

    private void handleCreateRoom(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        CreateRoomReq req = CreateRoomReq.parseFrom(wrapper.getPayload());

        PlayerSession player = playerManager.getPlayer(req.getPlayerId());
        if (player == null) {
            sendError(ctx, MessageType.CREATE_ROOM_RES, 1, "Player not found");
            return;
        }

        if (player.getCurrentRoomId() != null) {
            sendError(ctx, MessageType.CREATE_ROOM_RES, 2, "Player already in room");
            return;
        }

        int maxPlayers = req.getMaxPlayers() > 0 ? req.getMaxPlayers() : 12;
        if (maxPlayers < 6 || maxPlayers > 12) {
            sendError(ctx, MessageType.CREATE_ROOM_RES, 3, "Invalid max players");
            return;
        }

        GameRoomSession room = roomManager.createRoom(req.getPlayerId(), req.getRoomName(),
                maxPlayers, req.getPassword());
        roomManager.joinRoom(room.getRoomId(), player, req.getPassword());

        CreateRoomRes res = CreateRoomRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .setRoom(buildRoomInfo(room))
                .build();
        messageService.sendToChannel(ctx.channel(), MessageType.CREATE_ROOM_RES, res);
    }

    private void handleJoinRoom(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        JoinRoomReq req = JoinRoomReq.parseFrom(wrapper.getPayload());

        PlayerSession player = playerManager.getPlayer(req.getPlayerId());
        if (player == null) {
            sendError(ctx, MessageType.JOIN_ROOM_RES, 1, "Player not found");
            return;
        }

        if (player.getCurrentRoomId() != null) {
            sendError(ctx, MessageType.JOIN_ROOM_RES, 2, "Player already in room");
            return;
        }

        boolean success = roomManager.joinRoom(req.getRoomId(), player, req.getPassword());
        if (!success) {
            sendError(ctx, MessageType.JOIN_ROOM_RES, 3, "Failed to join room");
            return;
        }

        GameRoomSession room = roomManager.getRoom(req.getRoomId());
        JoinRoomRes res = JoinRoomRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .setRoom(buildRoomInfo(room))
                .build();
        messageService.sendToChannel(ctx.channel(), MessageType.JOIN_ROOM_RES, res);

        broadcastRoomInfo(room);
    }

    private void handleLeaveRoom(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        LeaveRoomReq req = LeaveRoomReq.parseFrom(wrapper.getPayload());

        PlayerSession player = playerManager.getPlayer(req.getPlayerId());
        if (player == null || player.getCurrentRoomId() == null) {
            sendError(ctx, MessageType.LEAVE_ROOM_RES, 1, "Player not in room");
            return;
        }

        GameRoomSession room = roomManager.getRoom(player.getCurrentRoomId());
        roomManager.leaveRoom(player.getCurrentRoomId(), req.getPlayerId());
        player.setCurrentRoomId(null);

        LeaveRoomRes res = LeaveRoomRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .build();
        messageService.sendToChannel(ctx.channel(), MessageType.LEAVE_ROOM_RES, res);

        if (room != null && room.getCurrentPlayers() > 0) {
            broadcastRoomInfo(room);
        }
    }

    private void handleStartGame(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        StartGameReq req = StartGameReq.parseFrom(wrapper.getPayload());

        boolean success = gameService.startGame(req.getRoomId(), req.getPlayerId());
        if (!success) {
            sendError(ctx, MessageType.START_GAME_RES, 1, "Failed to start game");
            return;
        }

        StartGameRes res = StartGameRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .build();
        messageService.sendToChannel(ctx.channel(), MessageType.START_GAME_RES, res);
    }

    private void handleRoomList(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        RoomListReq req = RoomListReq.parseFrom(wrapper.getPayload());

        List<GameRoomSession> rooms = roomManager.getActiveRooms();
        List<RoomInfo> roomInfos = new ArrayList<>();
        for (GameRoomSession room : rooms) {
            roomInfos.add(buildRoomInfo(room));
        }

        int page = Math.max(0, req.getPage());
        int size = Math.max(1, req.getSize());
        int start = page * size;
        int end = Math.min(start + size, roomInfos.size());

        RoomListRes res = RoomListRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .addAllRooms(roomInfos.subList(Math.max(0, start), Math.max(0, end)))
                .setTotal(roomInfos.size())
                .build();
        messageService.sendToChannel(ctx.channel(), MessageType.ROOM_LIST_RES, res);
    }

    private void handleWolfKill(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        WolfKillReq req = WolfKillReq.parseFrom(wrapper.getPayload());
        gameService.handleWolfKill(req.getRoomId(), req.getPlayerId(), req.getTargetId());

        WolfKillRes res = WolfKillRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .build();
        messageService.sendToChannel(ctx.channel(), MessageType.WOLF_KILL_RES, res);
    }

    private void handleSeerCheck(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        SeerCheckReq req = SeerCheckReq.parseFrom(wrapper.getPayload());
        gameService.handleSeerCheck(req.getRoomId(), req.getPlayerId(), req.getTargetId());
    }

    private void handleWitchAction(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        WitchActionReq req = WitchActionReq.parseFrom(wrapper.getPayload());
        gameService.handleWitchAction(req.getRoomId(), req.getPlayerId(),
                req.getUseAntidote(), req.getUsePoison(), req.getPoisonTargetId());
    }

    private void handleHunterShot(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        HunterShotReq req = HunterShotReq.parseFrom(wrapper.getPayload());
        gameService.handleHunterShot(req.getRoomId(), req.getPlayerId(), req.getTargetId());

        HunterShotRes res = HunterShotRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .build();
        messageService.sendToChannel(ctx.channel(), MessageType.HUNTER_SHOT_RES, res);
    }

    private void handleVote(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        VoteReq req = VoteReq.parseFrom(wrapper.getPayload());
        gameService.handleVote(req.getRoomId(), req.getPlayerId(),
                req.getTargetId() > 0 ? req.getTargetId() : null);

        VoteRes res = VoteRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .build();
        messageService.sendToChannel(ctx.channel(), MessageType.VOTE_RES, res);
    }

    private void handleChat(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        ChatReq req = ChatReq.parseFrom(wrapper.getPayload());

        GameRoomSession room = roomManager.getRoom(req.getRoomId());
        if (room == null) {
            return;
        }

        PlayerSession sender = playerManager.getPlayer(req.getPlayerId());
        if (sender == null) {
            return;
        }

        ChatNotify notify = ChatNotify.newBuilder()
                .setRoomId(req.getRoomId())
                .setPlayerId(req.getPlayerId())
                .setNickname(sender.getNickname())
                .setContent(req.getContent())
                .setTimestamp(System.currentTimeMillis())
                .build();

        for (PlayerSession player : room.getPlayerList()) {
            if (player.isOnline() && player.getChannel() != null) {
                messageService.sendToChannel(player.getChannel(), MessageType.CHAT_NOTIFY, notify);
            }
        }
    }

    private void handleRecordList(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        RecordListReq req = RecordListReq.parseFrom(wrapper.getPayload());

        List<com.wolfkill.entity.GameRecord> records = replayService.getRecordList(
                Math.max(0, req.getPage()), Math.max(1, req.getSize()));

        List<GameRecord> recordProtos = new ArrayList<>();
        for (com.wolfkill.entity.GameRecord record : records) {
            GameRecord proto = GameRecord.newBuilder()
                    .setRecordId(record.getId())
                    .setRoomId(record.getRoomId())
                    .setStartTime(record.getStartTime() != null ?
                            record.getStartTime().atZone(java.time.ZoneId.systemDefault()).toInstant().toEpochMilli() : 0)
                    .setEndTime(record.getEndTime() != null ?
                            record.getEndTime().atZone(java.time.ZoneId.systemDefault()).toInstant().toEpochMilli() : 0)
                    .setResult(GameResult.forNumber(record.getGameResult() != null ? record.getGameResult() : 0))
                    .setTotalDays(record.getTotalDays() != null ? record.getTotalDays() : 0)
                    .build();
            recordProtos.add(proto);
        }

        RecordListRes res = RecordListRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .addAllRecords(recordProtos)
                .setTotal(recordProtos.size())
                .build();
        messageService.sendToChannel(ctx.channel(), MessageType.RECORD_LIST_RES, res);
    }

    private void handleRecordPlayback(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        RecordPlaybackReq req = RecordPlaybackReq.parseFrom(wrapper.getPayload());

        List<RecordFrame> frames = replayService.getPlaybackFrames(req.getRecordId());
        int frameIndex = Math.max(0, Math.min(req.getFrameIndex(), frames.size() - 1));

        RecordFrame frame = frames.isEmpty() ? null : frames.get(frameIndex);
        RecordPlaybackRes res = RecordPlaybackRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .setFrame(frame != null ? frame : RecordFrame.newBuilder().build())
                .setTotalFrames(frames.size())
                .build();
        messageService.sendToChannel(ctx.channel(), MessageType.RECORD_PLAYBACK_RES, res);
    }

    public void handleDisconnect(Channel channel) {
        PlayerSession player = playerManager.getPlayerByChannel(channel.id());
        if (player != null) {
            if (player.getCurrentRoomId() != null) {
                GameRoomSession room = roomManager.getRoom(player.getCurrentRoomId());
                playerManager.handlePlayerDisconnect(player.getPlayerId(), room);
                if (room != null) {
                    room.setPlayerStatus(player.getPlayerId(), com.wolfkill.protocol.PlayerStatus.STATUS_DISCONNECTED);
                    broadcastRoomInfo(room);
                }
            } else {
                playerManager.setPlayerOffline(player.getPlayerId());
            }

            logger.info("Player {} ({}) disconnected, channel: {}",
                    player.getPlayerId(), player.getNickname(), channel.remoteAddress());
        }
    }

    private RoomInfo buildRoomInfo(GameRoomSession room) {
        List<PlayerInfo> playerInfos = new ArrayList<>();
        for (PlayerSession p : room.getPlayerList()) {
            PlayerInfo info = PlayerInfo.newBuilder()
                    .setPlayerId(p.getPlayerId())
                    .setNickname(p.getNickname())
                    .setSeat(p.getSeat() != null ? p.getSeat() : 0)
                    .setStatus(room.getPlayerStatus(p.getPlayerId()))
                    .setIsHost(p.isHost())
                    .setIsOnline(p.isOnline())
                    .build();
            playerInfos.add(info);
        }

        return RoomInfo.newBuilder()
                .setRoomId(room.getRoomId())
                .setRoomName(room.getRoomName())
                .setMaxPlayers(room.getMaxPlayers())
                .setCurrentPlayers(room.getCurrentPlayers())
                .setPhase(room.getPhase())
                .addAllPlayers(playerInfos)
                .setHostId(room.getHostId())
                .setHasPassword(room.hasPassword())
                .build();
    }

    private void broadcastRoomInfo(GameRoomSession room) {
        if (room == null) {
            return;
        }

        RoomInfoNotify notify = RoomInfoNotify.newBuilder()
                .setRoom(buildRoomInfo(room))
                .build();

        for (PlayerSession player : room.getPlayerList()) {
            if (player.isOnline() && player.getChannel() != null) {
                messageService.sendToChannel(player.getChannel(), MessageType.ROOM_INFO_NOTIFY, notify);
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

    private void sendError(ChannelHandlerContext ctx, MessageType type, int code, String message) {
        try {
            Header header = buildErrorHeader(code, message);
            com.google.protobuf.Message res = switch (type) {
                case CREATE_ROOM_RES -> CreateRoomRes.newBuilder().setHeader(header).build();
                case JOIN_ROOM_RES -> JoinRoomRes.newBuilder().setHeader(header).build();
                case LEAVE_ROOM_RES -> LeaveRoomRes.newBuilder().setHeader(header).build();
                case START_GAME_RES -> StartGameRes.newBuilder().setHeader(header).build();
                case RECONNECT_RES -> ReconnectRes.newBuilder().setHeader(header).build();
                default -> null;
            };

            if (res != null) {
                messageService.sendToChannel(ctx.channel(), type, res);
            }
        } catch (Exception e) {
            logger.error("Failed to send error response", e);
        }
    }

    private void handleAiFill(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        AiFillReq req = AiFillReq.parseFrom(wrapper.getPayload());

        List<AiPlayer> aiPlayers = aiService.fillRoomWithAi(
                req.getRoomId(), req.getPlayerId(), req.getAiCount(),
                req.getAiDifficulty() > 0 ? req.getAiDifficulty() : 2);

        List<PlayerInfo> aiPlayerInfos = new ArrayList<>();
        for (AiPlayer ai : aiPlayers) {
            PlayerInfo info = PlayerInfo.newBuilder()
                    .setPlayerId(ai.getPlayerId())
                    .setNickname(ai.getNickname())
                    .setSeat(ai.getSeat() != null ? ai.getSeat() : 0)
                    .setStatus(PlayerStatus.STATUS_ALIVE)
                    .setIsOnline(true)
                    .build();
            aiPlayerInfos.add(info);
        }

        AiFillRes res = AiFillRes.newBuilder()
                .setHeader(buildSuccessHeader())
                .setFilledCount(aiPlayers.size())
                .addAllAiPlayers(aiPlayerInfos)
                .build();
        messageService.sendToChannel(ctx.channel(), MessageType.AI_FILL_RES, res);

        GameRoomSession room = roomManager.getRoom(req.getRoomId());
        broadcastRoomInfo(room);
    }

    private void handleVoiceJoin(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        VoiceJoinReq req = VoiceJoinReq.parseFrom(wrapper.getPayload());
        VoiceJoinRes res = voiceService.joinVoiceRoom(
                req.getPlayerId(), req.getRoomId(), req.getIsWolfRoom());
        messageService.sendToChannel(ctx.channel(), MessageType.VOICE_JOIN_RES, res);
    }

    private void handleVoiceLeave(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        VoiceLeaveReq req = VoiceLeaveReq.parseFrom(wrapper.getPayload());
        VoiceLeaveRes res = voiceService.leaveVoiceRoom(
                req.getPlayerId(), req.getRoomId());
        messageService.sendToChannel(ctx.channel(), MessageType.VOICE_LEAVE_RES, res);
    }

    private void handleRankMatch(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        RankMatchReq req = RankMatchReq.parseFrom(wrapper.getPayload());
        RankMatchRes res = rankService.startMatchmaking(
                req.getPlayerId(),
                req.getGameMode() != null && !req.getGameMode().isEmpty() ? req.getGameMode() : "CLASSIC_12");
        messageService.sendToChannel(ctx.channel(), MessageType.RANK_MATCH_RES, res);
    }

    private void handleRankMatchCancel(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        RankMatchCancelReq req = RankMatchCancelReq.parseFrom(wrapper.getPayload());
        RankMatchCancelRes res = rankService.cancelMatchmaking(
                req.getPlayerId(), req.getMatchId());
        messageService.sendToChannel(ctx.channel(), MessageType.RANK_MATCH_CANCEL_RES, res);
    }

    private void handleRankLeaderboard(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        RankLeaderboardReq req = RankLeaderboardReq.parseFrom(wrapper.getPayload());
        RankLeaderboardRes res = rankService.getLeaderboard(
                req.getPlayerId() > 0 ? req.getPlayerId() : null,
                req.getSeasonId() != null && !req.getSeasonId().isEmpty() ? req.getSeasonId() : null,
                Math.max(0, req.getPage()),
                Math.max(1, Math.min(100, req.getSize())),
                req.getRegion());
        messageService.sendToChannel(ctx.channel(), MessageType.RANK_LEADERBOARD_RES, res);
    }

    private void handleRankSeasonInfo(ChannelHandlerContext ctx, MessageWrapper wrapper) throws InvalidProtocolBufferException {
        RankSeasonInfoReq req = RankSeasonInfoReq.parseFrom(wrapper.getPayload());
        RankSeasonInfoRes res = rankService.getSeasonInfo(
                req.getPlayerId() > 0 ? req.getPlayerId() : null);
        messageService.sendToChannel(ctx.channel(), MessageType.RANK_SEASON_INFO_RES, res);
    }
}
