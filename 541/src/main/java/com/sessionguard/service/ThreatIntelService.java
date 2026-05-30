package com.sessionguard.service;

import com.sessionguard.model.ThreatIntel;
import com.sessionguard.store.SessionStore;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
@RequiredArgsConstructor
public class ThreatIntelService {

    private final SessionStore sessionStore;

    private final Set<String> knownMaliciousIps = ConcurrentHashMap.newKeySet();
    private final Map<String, ThreatIntel> threatCache = new ConcurrentHashMap<>();

    @PostConstruct
    public void init() {
        initializeKnownThreats();
        log.info("Threat intelligence service initialized with {} known malicious IPs", knownMaliciousIps.size());
    }

    public ThreatIntel checkIpThreat(String ipAddress) {
        if (knownMaliciousIps.contains(ipAddress)) {
            sessionStore.incrementThreatHit(ipAddress);
            ThreatIntel cached = threatCache.get(ipAddress);
            if (cached != null) {
                return cached;
            }
        }

        return sessionStore.getThreatIntel(ipAddress).orElse(null);
    }

    public boolean isMaliciousIp(String ipAddress) {
        ThreatIntel threat = checkIpThreat(ipAddress);
        if (threat == null || !threat.isActive()) {
            return false;
        }
        return threat.getSeverity() == ThreatIntel.ThreatSeverity.HIGH
                || threat.getSeverity() == ThreatIntel.ThreatSeverity.CRITICAL;
    }

    public int getThreatRiskScore(String ipAddress) {
        ThreatIntel threat = checkIpThreat(ipAddress);
        if (threat == null || !threat.isActive()) {
            return 0;
        }
        return threat.getSeverity().getBaseScore();
    }

    public void addThreatIp(String ipAddress, ThreatIntel.ThreatType type, ThreatIntel.ThreatSeverity severity, String source, String description) {
        ThreatIntel intel = ThreatIntel.builder()
                .ipAddress(ipAddress)
                .threatType(type)
                .severity(severity)
                .source(source)
                .description(description)
                .confidence(80)
                .firstSeen(LocalDateTime.now())
                .lastSeen(LocalDateTime.now())
                .hitCount(0)
                .active(true)
                .tags(new String[]{type.name()})
                .build();

        sessionStore.saveThreatIntel(intel);
        knownMaliciousIps.add(ipAddress);
        threatCache.put(ipAddress, intel);
        log.warn("Added threat IP: {} ({}, {})", ipAddress, type, severity);
    }

    public void removeThreatIp(String ipAddress) {
        sessionStore.removeThreatIntel(ipAddress);
        knownMaliciousIps.remove(ipAddress);
        threatCache.remove(ipAddress);
        log.info("Removed threat IP: {}", ipAddress);
    }

    public List<ThreatIntel> getAllActiveThreats(int limit) {
        return sessionStore.getAllActiveThreats(limit);
    }

    public Optional<ThreatIntel> getThreatDetails(String ipAddress) {
        return sessionStore.getThreatIntel(ipAddress);
    }

    public void bulkAddThreats(List<ThreatIntel> threats) {
        for (ThreatIntel threat : threats) {
            sessionStore.saveThreatIntel(threat);
            knownMaliciousIps.add(threat.getIpAddress());
            threatCache.put(threat.getIpAddress(), threat);
        }
        log.info("Bulk added {} threat IPs", threats.size());
    }

    @Scheduled(fixedRate = 3600000)
    public void refreshThreatCache() {
        List<ThreatIntel> threats = sessionStore.getAllActiveThreats(10000);
        knownMaliciousIps.clear();
        threatCache.clear();
        for (ThreatIntel threat : threats) {
            if (threat.isActive()) {
                knownMaliciousIps.add(threat.getIpAddress());
                threatCache.put(threat.getIpAddress(), threat);
            }
        }
        log.debug("Threat cache refreshed: {} active threats", knownMaliciousIps.size());
    }

    private void initializeKnownThreats() {
        addThreatIp("192.168.1.100", ThreatIntel.ThreatType.BRUTE_FORCE,
                ThreatIntel.ThreatSeverity.HIGH, "SYSTEM", "Known brute force IP");
        addThreatIp("10.0.0.50", ThreatIntel.ThreatType.SESSION_HIJACKING,
                ThreatIntel.ThreatSeverity.CRITICAL, "SYSTEM", "Known session hijacking IP");
        addThreatIp("172.16.0.100", ThreatIntel.ThreatType.SQL_INJECTION,
                ThreatIntel.ThreatSeverity.HIGH, "SYSTEM", "Known SQL injection source");
        addThreatIp("203.0.113.10", ThreatIntel.ThreatType.TOR_EXIT_NODE,
                ThreatIntel.ThreatSeverity.MEDIUM, "SYSTEM", "Tor exit node");
        addThreatIp("198.51.100.25", ThreatIntel.ThreatType.BOTNET,
                ThreatIntel.ThreatSeverity.CRITICAL, "SYSTEM", "Known botnet IP");
    }
}
