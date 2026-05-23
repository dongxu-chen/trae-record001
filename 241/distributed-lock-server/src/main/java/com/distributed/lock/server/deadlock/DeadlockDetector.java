package com.distributed.lock.server.deadlock;

import com.distributed.lock.server.lock.LockInfo;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.function.BiConsumer;

public class DeadlockDetector {
    
    private static final Logger logger = LoggerFactory.getLogger(DeadlockDetector.class);
    
    private final ConcurrentHashMap<String, LockInfo> lockRegistry;
    private final ScheduledExecutorService detectionExecutor;
    private final List<BiConsumer<DeadlockInfo, Boolean>> deadlockListeners;
    private final long detectionIntervalMs;
    private final boolean autoResolve;
    private volatile boolean running;

    public DeadlockDetector(ConcurrentHashMap<String, LockInfo> lockRegistry) {
        this(lockRegistry, 30000, false);
    }

    public DeadlockDetector(ConcurrentHashMap<String, LockInfo> lockRegistry, 
                            long detectionIntervalMs, boolean autoResolve) {
        this.lockRegistry = lockRegistry;
        this.detectionIntervalMs = detectionIntervalMs;
        this.autoResolve = autoResolve;
        this.deadlockListeners = new ArrayList<>();
        this.detectionExecutor = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "deadlock-detector");
            t.setDaemon(true);
            return t;
        });
    }

    public void addDeadlockListener(BiConsumer<DeadlockInfo, Boolean> listener) {
        deadlockListeners.add(listener);
    }

    public void start() {
        if (!running) {
            running = true;
            detectionExecutor.scheduleAtFixedRate(
                    this::detectDeadlocks,
                    detectionIntervalMs,
                    detectionIntervalMs,
                    TimeUnit.MILLISECONDS
            );
            logger.info("Deadlock detector started with interval {}ms", detectionIntervalMs);
        }
    }

    public void stop() {
        running = false;
        detectionExecutor.shutdown();
        try {
            if (!detectionExecutor.awaitTermination(5, TimeUnit.SECONDS)) {
                detectionExecutor.shutdownNow();
            }
        } catch (InterruptedException e) {
            detectionExecutor.shutdownNow();
            Thread.currentThread().interrupt();
        }
        logger.info("Deadlock detector stopped");
    }

    public List<DeadlockInfo> detectDeadlocks() {
        return detectDeadlocks(autoResolve);
    }

    public List<DeadlockInfo> detectDeadlocks(boolean autoResolveDeadlocks) {
        List<DeadlockInfo> deadlocks = new ArrayList<>();
        
        try {
            Map<String, Set<String>> waitForGraph = buildWaitForGraph();
            
            Set<String> visited = new HashSet<>();
            Set<String> recursionStack = new HashSet<>();
            List<String> path = new ArrayList<>();
            
            for (String node : waitForGraph.keySet()) {
                if (!visited.contains(node)) {
                    List<String> cycle = findCycleDFS(node, waitForGraph, visited, recursionStack, path);
                    if (cycle != null && !cycle.isEmpty()) {
                        DeadlockInfo deadlockInfo = buildDeadlockInfo(cycle, waitForGraph);
                        deadlocks.add(deadlockInfo);
                        
                        if (autoResolveDeadlocks) {
                            resolveDeadlock(deadlockInfo);
                            deadlockInfo.setAutoResolved(true);
                        }
                        
                        notifyDeadlockDetected(deadlockInfo, autoResolveDeadlocks);
                    }
                }
            }
            
            if (!deadlocks.isEmpty()) {
                logger.warn("Detected {} deadlock(s)!", deadlocks.size());
                for (DeadlockInfo deadlock : deadlocks) {
                    logger.warn("Deadlock cycle: {}", deadlock.getDetectedCycle());
                }
            }
            
        } catch (Exception e) {
            logger.error("Error during deadlock detection", e);
        }
        
        return deadlocks;
    }

    private Map<String, Set<String>> buildWaitForGraph() {
        Map<String, Set<String>> graph = new HashMap<>();
        
        for (Map.Entry<String, LockInfo> entry : lockRegistry.entrySet()) {
            String lockName = entry.getKey();
            LockInfo lockInfo = entry.getValue();
            
            Set<String> holders = new HashSet<>(lockInfo.getHolders().keySet());
            
            for (LockInfo.Waiter waiter : lockInfo.getWaitQueue()) {
                String waiterClientId = waiter.getClientId();
                
                String waitingNode = "client:" + waiterClientId;
                String holdingNode = "lock:" + lockName;
                
                graph.computeIfAbsent(waitingNode, k -> new HashSet<>()).add(holdingNode);
                
                for (String holder : holders) {
                    String holderNode = "client:" + holder;
                    graph.computeIfAbsent(holdingNode, k -> new HashSet<>()).add(holderNode);
                }
            }
            
            for (String holder : lockInfo.getHolders().keySet()) {
                String holderNode = "client:" + holder;
                String lockNode = "lock:" + lockName;
                graph.computeIfAbsent(lockNode, k -> new HashSet<>()).add(holderNode);
            }
        }
        
        return graph;
    }

    private List<String> findCycleDFS(String node, Map<String, Set<String>> graph,
                                      Set<String> visited, Set<String> recursionStack,
                                      List<String> path) {
        visited.add(node);
        recursionStack.add(node);
        path.add(node);
        
        Set<String> neighbors = graph.getOrDefault(node, Collections.emptySet());
        for (String neighbor : neighbors) {
            if (!visited.contains(neighbor)) {
                List<String> cycle = findCycleDFS(neighbor, graph, visited, recursionStack, path);
                if (cycle != null) {
                    return cycle;
                }
            } else if (recursionStack.contains(neighbor)) {
                int cycleStart = path.indexOf(neighbor);
                if (cycleStart != -1) {
                    List<String> cycle = new ArrayList<>(path.subList(cycleStart, path.size()));
                    cycle.add(neighbor);
                    return cycle;
                }
            }
        }
        
        recursionStack.remove(node);
        path.remove(path.size() - 1);
        return null;
    }

    private DeadlockInfo buildDeadlockInfo(List<String> cycle, Map<String, Set<String>> waitForGraph) {
        List<String> involvedClients = new ArrayList<>();
        List<String> involvedLocks = new ArrayList<>();
        
        for (String node : cycle) {
            if (node.startsWith("client:")) {
                involvedClients.add(node.substring(7));
            } else if (node.startsWith("lock:")) {
                involvedLocks.add(node.substring(5));
            }
        }
        
        String cycleStr = String.join(" → ", cycle);
        
        String victimClient = null;
        String victimLock = null;
        if (!involvedClients.isEmpty()) {
            victimClient = involvedClients.get(0);
            if (!involvedLocks.isEmpty()) {
                victimLock = involvedLocks.get(0);
            }
        }
        
        return new DeadlockInfo(
                involvedLocks,
                involvedClients,
                cycleStr,
                victimClient,
                victimLock,
                false
        );
    }

    private void resolveDeadlock(DeadlockInfo deadlockInfo) {
        String victimClientId = deadlockInfo.getVictimClientId();
        String victimLockName = deadlockInfo.getVictimLockName();
        
        if (victimClientId != null && victimLockName != null) {
            LockInfo lockInfo = lockRegistry.get(victimLockName);
            if (lockInfo != null && lockInfo.isHeldBy(victimClientId)) {
                lockInfo.removeHolder(victimClientId);
                logger.warn("Auto-resolved deadlock: forced release of lock {} by client {}", 
                        victimLockName, victimClientId);
                
                synchronized (lockInfo) {
                    lockInfo.notifyAll();
                }
            }
        }
    }

    private void notifyDeadlockDetected(DeadlockInfo deadlockInfo, boolean resolved) {
        for (BiConsumer<DeadlockInfo, Boolean> listener : deadlockListeners) {
            try {
                listener.accept(deadlockInfo, resolved);
            } catch (Exception e) {
                logger.error("Error in deadlock listener", e);
            }
        }
    }

    public static class DeadlockInfo {
        private final List<String> involvedLocks;
        private final List<String> involvedClients;
        private final String detectedCycle;
        private final String victimClientId;
        private final String victimLockName;
        private boolean autoResolved;

        public DeadlockInfo(List<String> involvedLocks, List<String> involvedClients,
                            String detectedCycle, String victimClientId, 
                            String victimLockName, boolean autoResolved) {
            this.involvedLocks = involvedLocks;
            this.involvedClients = involvedClients;
            this.detectedCycle = detectedCycle;
            this.victimClientId = victimClientId;
            this.victimLockName = victimLockName;
            this.autoResolved = autoResolved;
        }

        public List<String> getInvolvedLocks() {
            return involvedLocks;
        }

        public List<String> getInvolvedClients() {
            return involvedClients;
        }

        public String getDetectedCycle() {
            return detectedCycle;
        }

        public String getVictimClientId() {
            return victimClientId;
        }

        public String getVictimLockName() {
            return victimLockName;
        }

        public boolean isAutoResolved() {
            return autoResolved;
        }

        public void setAutoResolved(boolean autoResolved) {
            this.autoResolved = autoResolved;
        }
    }
}