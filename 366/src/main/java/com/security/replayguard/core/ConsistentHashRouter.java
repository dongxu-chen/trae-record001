package com.security.replayguard.core;

import com.security.replayguard.config.ReplayGuardProperties;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.nio.charset.StandardCharsets;
import java.util.*;

@Slf4j
@Component
@RequiredArgsConstructor
public class ConsistentHashRouter {

    private final ReplayGuardProperties properties;

    private TreeMap<Long, String> hashRing = new TreeMap<>();

    private final Map<String, Integer> nodeCounts = new HashMap<>();

    @PostConstruct
    public void init() {
        for (String node : properties.getConsistentHash().getNodes()) {
            addNode(node);
        }
        log.info("Consistent hash router initialized with {} nodes", properties.getConsistentHash().getNodes().size());
    }

    public void addNode(String node) {
        int virtualNodeCount = properties.getConsistentHash().getVirtualNodeCount();

        for (int i = 0; i < virtualNodeCount; i++) {
            String virtualNode = node + "#VN-" + i;
            long hash = hash(virtualNode);
            hashRing.put(hash, node);
        }

        nodeCounts.merge(node, 1, Integer::sum);
        log.debug("Added node: {} with {} virtual nodes", node, virtualNodeCount);
    }

    public void removeNode(String node) {
        int virtualNodeCount = properties.getConsistentHash().getVirtualNodeCount();

        for (int i = 0; i < virtualNodeCount; i++) {
            String virtualNode = node + "#VN-" + i;
            long hash = hash(virtualNode);
            hashRing.remove(hash);
        }

        nodeCounts.remove(node);
        log.debug("Removed node: {} with {} virtual nodes", node, virtualNodeCount);
    }

    public String getNode(String key) {
        if (hashRing.isEmpty()) {
            return null;
        }

        long hash = hash(key);

        Map.Entry<Long, String> entry = hashRing.ceilingEntry(hash);
        if (entry == null) {
            entry = hashRing.firstEntry();
        }

        return entry.getValue();
    }

    public List<String> getNodes(String key, int replicaCount) {
        Set<String> nodes = new LinkedHashSet<>();

        if (hashRing.isEmpty()) {
            return Collections.emptyList();
        }

        long hash = hash(key);
        int count = 0;

        for (Map.Entry<Long, String> entry : hashRing.tailMap(hash, true).entrySet()) {
            if (nodes.add(entry.getValue())) {
                count++;
            }
            if (count >= replicaCount) {
                break;
            }
        }

        if (count < replicaCount) {
            for (Map.Entry<Long, String> entry : hashRing.headMap(hash).entrySet()) {
                if (nodes.add(entry.getValue())) {
                    count++;
                }
                if (count >= replicaCount) {
                    break;
                }
            }
        }

        return new ArrayList<>(nodes);
    }

    public Set<String> getAllNodes() {
        return new HashSet<>(nodeCounts.keySet());
    }

    public int getNodeCount() {
        return nodeCounts.size();
    }

    private long hash(String key) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] digest = md.digest(key.getBytes(StandardCharsets.UTF_8));

            long hash = 0;
            for (int i = 0; i < 8; i++) {
                hash = (hash << 8) | (digest[i] & 0xFF);
            }
            return hash & 0x7FFFFFFFFFFFFFFFL;
        } catch (NoSuchAlgorithmException e) {
            return (long) key.hashCode() & 0x7FFFFFFFFFFFFFFFL;
        }
    }

    public Map<String, Integer> getNodeDistribution() {
        Map<String, Integer> distribution = new HashMap<>();

        for (String node : nodeCounts.keySet()) {
            distribution.put(node, 0);
        }

        if (hashRing.isEmpty()) {
            return distribution;
        }

        List<Long> hashes = new ArrayList<>(hashRing.keySet());
        hashes.sort(Long::compareTo);

        for (int i = 0; i < hashes.size(); i++) {
            long current = hashes.get(i);
            long next = i < hashes.size() - 1 ? hashes.get(i + 1) : hashes.get(0);

            long range = next > current ? next - current : (Long.MAX_VALUE - current) + next;
            String node = hashRing.get(current);
            distribution.merge(node, (int) (range / 1000000), Integer::sum);
        }

        return distribution;
    }
}
