package com.wolfkill.ai;

import com.wolfkill.model.PlayerSession;
import com.wolfkill.protocol.PlayerStatus;
import com.wolfkill.protocol.Role;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.util.ArrayList;
import java.util.List;

@Data
@EqualsAndHashCode(callSuper = true)
public class AiPlayer extends PlayerSession {

    private int difficulty;
    private String aiPersonality;
    private double aggression;
    private double deception;
    private double cooperation;
    private List<Long> suspectedWolves = new ArrayList<>();
    private List<Long> trustedPlayers = new ArrayList<>();
    private List<String> speechTemplates = new ArrayList<>();
    private long lastActionTime;
    private int reactionDelay;
    private boolean isAi = true;
    private String aiId;

    public AiPlayer() {
        super();
    }

    public AiPlayer(Long playerId, String nickname, int difficulty) {
        super();
        this.setPlayerId(playerId);
        this.setNickname(nickname);
        this.difficulty = difficulty;
        this.aiId = "AI_" + playerId;
        initPersonality(difficulty);
    }

    private void initPersonality(int difficulty) {
        this.reactionDelay = switch (difficulty) {
            case 1 -> 3000 + (int) (Math.random() * 3000);
            case 2 -> 2000 + (int) (Math.random() * 2000);
            case 3 -> 1000 + (int) (Math.random() * 1500);
            default -> 2000;
        };

        this.aggression = 0.3 + Math.random() * 0.4 * difficulty / 3.0;
        this.deception = 0.2 + Math.random() * 0.5 * difficulty / 3.0;
        this.cooperation = 0.5 + Math.random() * 0.3 * (4 - difficulty) / 3.0;

        initSpeechTemplates();
    }

    private void initSpeechTemplates() {
        speechTemplates.add("我是好人，我相信大家。");
        speechTemplates.add("我觉得{player}有点可疑。");
        speechTemplates.add("我昨晚观察了一下，{player}的行为很奇怪。");
        speechTemplates.add("我建议大家投票给{player}。");
        speechTemplates.add("我是预言家，我查验了{player}，是{result}。");
        speechTemplates.add("我是女巫，昨晚我{action}。");
        speechTemplates.add("请大家相信我，我会带领好人获胜。");
        speechTemplates.add("{player}，请你解释一下你的行为。");
        speechTemplates.add("我觉得我们应该先听大家发言。");
        speechTemplates.add("从发言来看，{player}的逻辑有问题。");
    }

    public String generateSpeech(Long targetPlayer, boolean isWolf, boolean isGood) {
        if (speechTemplates.isEmpty()) {
            return "我是好人。";
        }

        int index = (int) (Math.random() * speechTemplates.size());
        String template = speechTemplates.get(index);

        if (targetPlayer != null) {
            template = template.replace("{player}", "玩家" + targetPlayer);
        }

        if (template.contains("{result}")) {
            template = template.replace("{result}", isWolf ? "狼人" : "好人");
        }

        if (template.contains("{action}")) {
            template = template.replace("{action}", isGood ? "用了解药救了人" : "没用解药");
        }

        return template;
    }

    public Long chooseTarget(List<Long> candidates, Role myRole, GameContext context) {
        if (candidates == null || candidates.isEmpty()) {
            return null;
        }

        if (difficulty == 1) {
            return candidates.get((int) (Math.random() * candidates.size()));
        }

        if (myRole == Role.ROLE_WEREWOLF) {
            return chooseWolfTarget(candidates, context);
        } else if (myRole == Role.ROLE_SEER) {
            return chooseSeerTarget(candidates, context);
        } else if (myRole == Role.ROLE_WITCH) {
            return chooseWitchTarget(candidates, context);
        } else if (myRole == Role.ROLE_HUNTER) {
            return chooseHunterTarget(candidates, context);
        }

        return chooseVoteTarget(candidates, context);
    }

    private Long chooseWolfTarget(List<Long> candidates, GameContext context) {
        List<Long> priorityTargets = new ArrayList<>();

        for (Long candidate : candidates) {
            Role role = context.getPlayerRole(candidate);
            if (role == Role.ROLE_SEER || role == Role.ROLE_WITCH) {
                if (difficulty >= 2) {
                    priorityTargets.add(candidate);
                }
            }
        }

        if (!priorityTargets.isEmpty()) {
            return priorityTargets.get((int) (Math.random() * priorityTargets.size()));
        }

        return candidates.get((int) (Math.random() * candidates.size()));
    }

    private Long chooseSeerTarget(List<Long> candidates, GameContext context) {
        List<Long> suspicious = new ArrayList<>();
        for (Long candidate : candidates) {
            if (suspectedWolves.contains(candidate)) {
                suspicious.add(candidate);
            }
        }

        if (!suspicious.isEmpty()) {
            return suspicious.get((int) (Math.random() * suspicious.size()));
        }

        return candidates.get((int) (Math.random() * candidates.size()));
    }

    private Long chooseWitchTarget(List<Long> candidates, GameContext context) {
        return chooseVoteTarget(candidates, context);
    }

    private Long chooseHunterTarget(List<Long> candidates, GameContext context) {
        if (!suspectedWolves.isEmpty()) {
            for (Long suspect : suspectedWolves) {
                if (candidates.contains(suspect)) {
                    return suspect;
                }
            }
        }
        return candidates.get((int) (Math.random() * candidates.size()));
    }

    private Long chooseVoteTarget(List<Long> candidates, GameContext context) {
        if (!suspectedWolves.isEmpty() && Math.random() < cooperation) {
            for (Long suspect : suspectedWolves) {
                if (candidates.contains(suspect)) {
                    return suspect;
                }
            }
        }
        return candidates.get((int) (Math.random() * candidates.size()));
    }

    public void updateSuspected(Long playerId, double suspicion) {
        if (suspicion > 0.5 && !suspectedWolves.contains(playerId)) {
            if (suspectedWolves.size() < 4) {
                suspectedWolves.add(playerId);
            }
        } else if (suspicion < 0.2) {
            suspectedWolves.remove(playerId);
            if (!trustedPlayers.contains(playerId) && trustedPlayers.size() < 4) {
                trustedPlayers.add(playerId);
            }
        }
    }

    public boolean shouldUsePoison(GameContext context) {
        if (difficulty == 1) {
            return Math.random() < 0.3;
        }
        return !suspectedWolves.isEmpty() && Math.random() < 0.6;
    }

    public boolean shouldUseAntidote(Long killedPlayer, GameContext context) {
        if (difficulty == 1) {
            return Math.random() < 0.7;
        }
        if (trustedPlayers.contains(killedPlayer)) {
            return true;
        }
        return Math.random() < 0.5;
    }

    public boolean shouldShoot(GameContext context) {
        return !suspectedWolves.isEmpty();
    }

    @Data
    public static class GameContext {
        private Long roomId;
        private int dayNumber;
        private java.util.Map<Long, Role> playerRoles;
        private java.util.Map<Long, PlayerStatus> playerStatuses;
        private java.util.List<Long> deadPlayers;
        private java.util.Map<Long, Long> votes;
        private java.util.List<String> historyEvents;

        public Role getPlayerRole(Long playerId) {
            return playerRoles != null ? playerRoles.get(playerId) : null;
        }

        public PlayerStatus getPlayerStatus(Long playerId) {
            return playerStatuses != null ? playerStatuses.get(playerId) : null;
        }

        public boolean isPlayerAlive(Long playerId) {
            return playerStatuses != null &&
                   playerStatuses.get(playerId) == PlayerStatus.STATUS_ALIVE;
        }
    }
}
