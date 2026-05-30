package com.dtmonitor.trace.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TraceDag {

    private String traceId;
    private List<DagNode> nodes;
    private List<DagEdge> edges;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DagNode {
        private String id;
        private String name;
        private String serviceName;
        private long durationMs;
        private String status;
        private String transactionMode;
        private String branchId;
        private int depth;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DagEdge {
        private String source;
        private String target;
        private String label;
    }

    public void addNode(DagNode node) {
        if (nodes == null) nodes = new ArrayList<>();
        nodes.add(node);
    }

    public void addEdge(DagEdge edge) {
        if (edges == null) edges = new ArrayList<>();
        edges.add(edge);
    }
}
