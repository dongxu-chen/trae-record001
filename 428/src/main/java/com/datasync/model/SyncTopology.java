package com.datasync.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SyncTopology implements Serializable {

    private static final long serialVersionUID = 1L;

    private String syncId;
    private long timestamp;
    private String status;
    private String version;

    private List<Node> nodes = new ArrayList<>();
    private List<Link> links = new ArrayList<>();
    private Map<String, Object> stats = new HashMap<>();

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Node implements Serializable {
        private static final long serialVersionUID = 1L;
        private String id;
        private String name;
        private NodeType type;
        private String status;
        private Map<String, Object> metrics = new HashMap<>();
        private int x;
        private int y;
        private String description;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Link implements Serializable {
        private static final long serialVersionUID = 1L;
        private String id;
        private String source;
        private String target;
        private LinkType type;
        private String status;
        private long latencyMs;
        private long throughput;
        private long totalRows;
        private Map<String, Object> metrics = new HashMap<>();
        private String description;
    }

    public enum NodeType {
        MYSQL,
        CANAL,
        KAFKA,
        KAFKA_TOPIC,
        SYNC_SERVICE,
        CLICKHOUSE,
        MONITORING
    }

    public enum LinkType {
        BINLOG,
        KAFKA_PRODUCE,
        KAFKA_CONSUME,
        DATA_WRITE,
        METRICS
    }

    public static String generateNodeId(NodeType type, String name) {
        return type.name().toLowerCase() + "_" + name;
    }

    public static String generateLinkId(String sourceId, String targetId) {
        return sourceId + " -> " + targetId;
    }
}
