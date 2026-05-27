package com.security.replayguard.attack;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.HashMap;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AttackEvent {

    private String attackId;

    private String attackType;

    private String ipAddress;

    private String userId;

    private String deviceFingerprint;

    private String requestPath;

    private String requestHash;

    private long timestamp;

    private String reason;

    private String sourceNode;

    private Map<String, Object> metadata;

    public enum AttackType {
        NONCE_REPLAY("nonce_replay", "Nonce重放攻击"),
        SLIDING_WINDOW_BREACH("sliding_window_breach", "滑动窗口超限"),
        RATE_LIMIT_BREACH("rate_limit_breach", "速率限制超限"),
        HONEYPOT_TRIGGERED("honeypot_triggered", "蜜罐触发"),
        INVALID_TIMESTAMP("invalid_timestamp", "无效时间戳"),
        BURST_ATTACK("burst_attack", "突发攻击"),
        DISTRIBUTED_ATTACK("distributed_attack", "分布式攻击");

        private final String code;
        private final String description;

        AttackType(String code, String description) {
            this.code = code;
            this.description = description;
        }

        public String getCode() {
            return code;
        }

        public String getDescription() {
            return description;
        }
    }

    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("attackId", attackId);
        map.put("attackType", attackType);
        map.put("ipAddress", ipAddress);
        map.put("userId", userId);
        map.put("deviceFingerprint", deviceFingerprint);
        map.put("requestPath", requestPath);
        map.put("requestHash", requestHash);
        map.put("timestamp", timestamp);
        map.put("reason", reason);
        map.put("sourceNode", sourceNode);
        if (metadata != null) {
            map.putAll(metadata);
        }
        return map;
    }
}
