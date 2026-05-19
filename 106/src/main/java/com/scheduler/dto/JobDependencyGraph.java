package com.scheduler.dto;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class JobDependencyGraph {

    private List<Node> nodes = new ArrayList<>();
    private List<Edge> edges = new ArrayList<>();

    @Data
    public static class Node {
        private String id;
        private String name;
        private String group;
        private String status;
        private String cronExpression;
        private String description;
        private Integer retryCount;
        private Integer timeoutSeconds;
    }

    @Data
    public static class Edge {
        private String source;
        private String target;
        private String label;
    }

}
