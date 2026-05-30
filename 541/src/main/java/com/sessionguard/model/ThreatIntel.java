package com.sessionguard.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ThreatIntel implements Serializable {

    private static final long serialVersionUID = 1L;

    private String ipAddress;
    private ThreatType threatType;
    private ThreatSeverity severity;
    private String source;
    private String description;
    private int confidence;
    private LocalDateTime firstSeen;
    private LocalDateTime lastSeen;
    private long hitCount;
    private boolean active;
    private String[] tags;
    private String asn;
    private String country;

    public enum ThreatType {
        BRUTE_FORCE,
        SQL_INJECTION,
        XSS,
        BOTNET,
        SPAM,
        SCANNER,
        DDOS,
        SESSION_HIJACKING,
        CREDENTIAL_STUFFING,
        MALWARE,
        PHISHING,
        TOR_EXIT_NODE,
        VPN_SERVICE,
        DATACENTER_PROXY,
        ABUSED,
        UNKNOWN
    }

    public enum ThreatSeverity {
        LOW(20),
        MEDIUM(40),
        HIGH(70),
        CRITICAL(100);

        private final int baseScore;

        ThreatSeverity(int baseScore) {
            this.baseScore = baseScore;
        }

        public int getBaseScore() {
            return baseScore;
        }
    }
}
