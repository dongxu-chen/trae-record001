package com.abtest.util;

import com.google.common.hash.HashFunction;
import com.google.common.hash.Hashing;
import lombok.extern.slf4j.Slf4j;

import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.ConcurrentSkipListMap;

@Slf4j
public class ConsistentHashRing<T> {

    private static final HashFunction HASH_FUNCTION = Hashing.murmur3_128();
    private static final int DEFAULT_VIRTUAL_NODES = 150;

    private final int virtualNodes;
    private final ConcurrentSkipListMap<Long, T> ring = new ConcurrentSkipListMap<>();
    private final Map<T, List<Long>> nodeVirtualKeys = new HashMap<>();

    public ConsistentHashRing() {
        this(DEFAULT_VIRTUAL_NODES);
    }

    public ConsistentHashRing(int virtualNodes) {
        this.virtualNodes = virtualNodes;
    }

    public synchronized void addNode(T node) {
        if (node == null) {
            throw new IllegalArgumentException("Node cannot be null");
        }
        List<Long> virtualKeys = new ArrayList<>();
        for (int i = 0; i < virtualNodes; i++) {
            String virtualNodeKey = node.toString() + "-vn-" + i;
            long hash = hash(virtualNodeKey);
            ring.put(hash, node);
            virtualKeys.add(hash);
        }
        nodeVirtualKeys.put(node, virtualKeys);
        log.info("Added node {} with {} virtual nodes", node, virtualNodes);
    }

    public synchronized void removeNode(T node) {
        if (node == null) {
            return;
        }
        List<Long> virtualKeys = nodeVirtualKeys.remove(node);
        if (virtualKeys != null) {
            for (Long key : virtualKeys) {
                ring.remove(key);
            }
            log.info("Removed node {} with {} virtual nodes", node, virtualKeys.size());
        }
    }

    public synchronized void updateNodes(Collection<T> nodes) {
        Set<T> currentNodes = new HashSet<>(nodeVirtualKeys.keySet());
        Set<T> newNodes = new HashSet<>(nodes);

        Set<T> toRemove = new HashSet<>(currentNodes);
        toRemove.removeAll(newNodes);

        Set<T> toAdd = new HashSet<>(newNodes);
        toAdd.removeAll(currentNodes);

        for (T node : toRemove) {
            removeNode(node);
        }

        for (T node : toAdd) {
            addNode(node);
        }

        log.info("Updated hash ring: added={}, removed={}, total={}",
            toAdd.size(), toRemove.size(), ring.size() / virtualNodes);
    }

    public T getNode(String key) {
        if (ring.isEmpty()) {
            return null;
        }
        long hash = hash(key);
        Map.Entry<Long, T> entry = ring.ceilingEntry(hash);
        if (entry == null) {
            entry = ring.firstEntry();
        }
        return entry.getValue();
    }

    public T getNode(int bucket) {
        return getNode(String.valueOf(bucket));
    }

    private long hash(String key) {
        return HASH_FUNCTION.hashString(key, StandardCharsets.UTF_8).asLong();
    }

    public int size() {
        return nodeVirtualKeys.size();
    }

    public boolean isEmpty() {
        return ring.isEmpty();
    }

    public Set<T> getNodes() {
        return Collections.unmodifiableSet(nodeVirtualKeys.keySet());
    }

    public Map<T, Integer> getKeyDistribution(int sampleSize) {
        Map<T, Integer> distribution = new HashMap<>();
        if (ring.isEmpty()) {
            return distribution;
        }

        for (int i = 0; i < sampleSize; i++) {
            T node = getNode("sample-" + i);
            distribution.merge(node, 1, Integer::sum);
        }

        return distribution;
    }
}
