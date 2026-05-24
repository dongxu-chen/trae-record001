package com.wolfkill.service;

import com.wolfkill.model.GameRoomSession;
import com.wolfkill.model.PlayerSession;
import com.wolfkill.protocol.Role;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class RoleService {

    private static final Logger logger = LoggerFactory.getLogger(RoleService.class);

    private static final Map<Integer, RoleConfig> BALANCED_CONFIGS = new LinkedHashMap<>();

    static {
        BALANCED_CONFIGS.put(6, new RoleConfig(2, 1, 1, 1, 0, 0, 1));
        BALANCED_CONFIGS.put(7, new RoleConfig(2, 1, 1, 1, 0, 0, 2));
        BALANCED_CONFIGS.put(8, new RoleConfig(3, 1, 1, 1, 0, 0, 2));
        BALANCED_CONFIGS.put(9, new RoleConfig(3, 1, 1, 1, 1, 0, 2));
        BALANCED_CONFIGS.put(10, new RoleConfig(3, 1, 1, 1, 1, 0, 3));
        BALANCED_CONFIGS.put(11, new RoleConfig(4, 1, 1, 1, 1, 0, 3));
        BALANCED_CONFIGS.put(12, new RoleConfig(4, 1, 1, 1, 1, 1, 3));
    }

    private static class RoleConfig {
        int wolfCount;
        int seerCount;
        int witchCount;
        int hunterCount;
        int guardCount;
        int cupidCount;
        int villagerCount;

        RoleConfig(int wolf, int seer, int witch, int hunter, int guard, int cupid, int villager) {
            this.wolfCount = wolf;
            this.seerCount = seer;
            this.witchCount = witch;
            this.hunterCount = hunter;
            this.guardCount = guard;
            this.cupidCount = cupid;
            this.villagerCount = villager;
        }

        int getTotal() {
            return wolfCount + seerCount + witchCount + hunterCount + guardCount + cupidCount + villagerCount;
        }

        int getGoodCount() {
            return seerCount + witchCount + hunterCount + guardCount + cupidCount + villagerCount;
        }

        int getEvilCount() {
            return wolfCount;
        }
    }

    public void assignRoles(GameRoomSession room) {
        int playerCount = room.getCurrentPlayers();
        List<Role> roles = generateBalancedRoleConfig(playerCount);
        Collections.shuffle(roles);

        List<PlayerSession> players = room.getPlayerList();
        for (int i = 0; i < players.size(); i++) {
            Role role = roles.get(i);
            Long playerId = players.get(i).getPlayerId();
            room.setPlayerRole(playerId, role);
        }

        validateBalance(roles);
    }

    private List<Role> generateBalancedRoleConfig(int playerCount) {
        List<Role> roles = new ArrayList<>();

        RoleConfig config = BALANCED_CONFIGS.get(playerCount);
        if (config == null) {
            logger.warn("No balanced config for {} players, generating dynamically", playerCount);
            config = generateDynamicConfig(playerCount);
        }

        for (int i = 0; i < config.wolfCount; i++) roles.add(Role.ROLE_WEREWOLF);
        for (int i = 0; i < config.seerCount; i++) roles.add(Role.ROLE_SEER);
        for (int i = 0; i < config.witchCount; i++) roles.add(Role.ROLE_WITCH);
        for (int i = 0; i < config.hunterCount; i++) roles.add(Role.ROLE_HUNTER);
        for (int i = 0; i < config.guardCount; i++) roles.add(Role.ROLE_GUARD);
        for (int i = 0; i < config.cupidCount; i++) roles.add(Role.ROLE_CUPID);
        for (int i = 0; i < config.villagerCount; i++) roles.add(Role.ROLE_VILLAGER);

        return roles;
    }

    private RoleConfig generateDynamicConfig(int playerCount) {
        int wolfCount = calculateWolfCount(playerCount);
        int goodCount = playerCount - wolfCount;

        int seer = 1;
        int witch = 1;
        int hunter = Math.min(1, goodCount - 2);
        int guard = playerCount >= 9 ? 1 : 0;
        int cupid = playerCount >= 12 ? 1 : 0;

        int specialGood = seer + witch + hunter + guard + cupid;
        int villager = goodCount - specialGood;

        return new RoleConfig(wolfCount, seer, witch, hunter, guard, cupid, villager);
    }

    private int calculateWolfCount(int playerCount) {
        if (playerCount <= 6) return 2;
        if (playerCount <= 8) return 2;
        if (playerCount <= 10) return 3;
        return 4;
    }

    private void validateBalance(List<Role> roles) {
        int wolf = 0, good = 0;
        for (Role role : roles) {
            if (role == Role.ROLE_WEREWOLF) wolf++;
            else good++;
        }

        double ratio = (double) good / wolf;
        logger.info("Role balance - Good: {}, Wolf: {}, Ratio: {:.2f}:1", good, wolf, ratio);

        if (ratio < 1.5 || ratio > 3.0) {
            logger.warn("Role balance may be unfair! Ratio: {:.2f}:1", ratio);
        }
    }

    public RoleConfigResult getBalanceInfo(int playerCount) {
        RoleConfig config = BALANCED_CONFIGS.get(playerCount);
        if (config == null) {
            config = generateDynamicConfig(playerCount);
        }
        return new RoleConfigResult(config.wolfCount, config.getGoodCount(), config.getTotal());
    }

    public static class RoleConfigResult {
        public final int wolfCount;
        public final int goodCount;
        public final int totalCount;
        public final double ratio;

        public RoleConfigResult(int wolf, int good, int total) {
            this.wolfCount = wolf;
            this.goodCount = good;
            this.totalCount = total;
            this.ratio = good > 0 && wolf > 0 ? (double) good / wolf : 0;
        }
    }

    public boolean isValidRoleConfig(int playerCount) {
        return playerCount >= 6 && playerCount <= 12;
    }
}
