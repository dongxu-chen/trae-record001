package com.security.replayguard.core;

import com.security.replayguard.config.ReplayGuardProperties;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

class ConsistentHashRouterTest {

    private ConsistentHashRouter router;
    private ReplayGuardProperties properties;

    @BeforeEach
    void setUp() {
        properties = new ReplayGuardProperties();
        properties.getConsistentHash().setVirtualNodeCount(150);
        properties.getConsistentHash().setNodes(List.of("node-1", "node-2", "node-3"));

        router = new ConsistentHashRouter(properties);
        router.init();
    }

    @Test
    @DisplayName("Get node - returns one of the configured nodes")
    void testGetNode_ReturnsValidNode() {
        Set<String> validNodes = Set.of("node-1", "node-2", "node-3");

        String node = router.getNode("test-key");

        assertNotNull(node);
        assertTrue(validNodes.contains(node), "Should return a valid node");
    }

    @Test
    @DisplayName("Get node - same key returns same node (consistency)")
    void testGetNode_Consistency() {
        String node1 = router.getNode("my-key");
        String node2 = router.getNode("my-key");

        assertEquals(node1, node2, "Same key should always return same node");
    }

    @Test
    @DisplayName("Get node - different keys distribute across nodes")
    void testGetNode_Distribution() {
        int node1Count = 0;
        int node2Count = 0;
        int node3Count = 0;

        for (int i = 0; i < 1000; i++) {
            String node = router.getNode("key-" + i);
            if ("node-1".equals(node)) node1Count++;
            if ("node-2".equals(node)) node2Count++;
            if ("node-3".equals(node)) node3Count++;
        }

        assertTrue(node1Count > 200, "node-1 should have reasonable distribution");
        assertTrue(node2Count > 200, "node-2 should have reasonable distribution");
        assertTrue(node3Count > 200, "node-3 should have reasonable distribution");
    }

    @Test
    @DisplayName("Get nodes with replicas - returns unique nodes")
    void testGetNodes_Replicas() {
        List<String> nodes = router.getNodes("test-key", 2);

        assertNotNull(nodes);
        assertEquals(2, nodes.size());
        assertEquals(2, nodes.stream().distinct().count(), "Should return distinct nodes");
    }

    @Test
    @DisplayName("Get nodes with replicas - caps at available nodes")
    void testGetNodes_MaxNodes() {
        List<String> nodes = router.getNodes("test-key", 10);

        assertNotNull(nodes);
        assertEquals(3, nodes.size(), "Should not exceed available node count");
    }

    @Test
    @DisplayName("Get all nodes - returns all configured nodes")
    void testGetAllNodes() {
        Set<String> nodes = router.getAllNodes();

        assertEquals(3, nodes.size());
        assertTrue(nodes.contains("node-1"));
        assertTrue(nodes.contains("node-2"));
        assertTrue(nodes.contains("node-3"));
    }

    @Test
    @DisplayName("Get node count")
    void testGetNodeCount() {
        assertEquals(3, router.getNodeCount());
    }

    @Test
    @DisplayName("Add node - new node becomes routable")
    void testAddNode() {
        router.addNode("node-4");

        assertEquals(4, router.getNodeCount());
        assertTrue(router.getAllNodes().contains("node-4"));
    }

    @Test
    @DisplayName("Remove node - node is no longer routable")
    void testRemoveNode() {
        router.removeNode("node-3");

        assertEquals(2, router.getNodeCount());
        assertFalse(router.getAllNodes().contains("node-3"));
    }

    @Test
    @DisplayName("Remove node - keys are redistributed to remaining nodes")
    void testRemoveNode_Redistribution() {
        Set<String> keys = new java.util.HashSet<>();
        for (int i = 0; i < 100; i++) {
            keys.add("key-" + i);
        }

        java.util.Map<String, String> originalMapping = new java.util.HashMap<>();
        for (String key : keys) {
            originalMapping.put(key, router.getNode(key));
        }

        router.removeNode("node-3");

        int redistributed = 0;
        for (String key : keys) {
            String newNode = router.getNode(key);
            String oldNode = originalMapping.get(key);
            
            if (!newNode.equals(oldNode)) {
                redistributed++;
            }
            assertNotEquals("node-3", newNode, "Key should not map to removed node");
        }

        assertTrue(redistributed > 0, "Some keys should be redistributed");
    }

    @Test
    @DisplayName("Get node distribution - returns distribution map")
    void testGetNodeDistribution() {
        java.util.Map<String, Integer> distribution = router.getNodeDistribution();

        assertNotNull(distribution);
        assertEquals(3, distribution.size());
        assertTrue(distribution.containsKey("node-1"));
        assertTrue(distribution.containsKey("node-2"));
        assertTrue(distribution.containsKey("node-3"));
    }

    @Test
    @DisplayName("Empty hash ring - returns null for getNode")
    void testEmptyHashRing() {
        ConsistentHashRouter emptyRouter = new ConsistentHashRouter(properties);
        emptyRouter.init();

        for (String node : List.of("node-1", "node-2", "node-3")) {
            emptyRouter.removeNode(node);
        }

        assertNull(emptyRouter.getNode("test-key"));
    }

    @Test
    @DisplayName("Get nodes with empty ring - returns empty list")
    void testGetNodes_EmptyRing() {
        ConsistentHashRouter emptyRouter = new ConsistentHashRouter(properties);
        emptyRouter.init();

        for (String node : List.of("node-1", "node-2", "node-3")) {
            emptyRouter.removeNode(node);
        }

        List<String> nodes = emptyRouter.getNodes("test-key", 2);
        assertTrue(nodes.isEmpty());
    }
}
