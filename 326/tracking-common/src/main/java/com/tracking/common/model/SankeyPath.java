package com.tracking.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SankeyPath implements Serializable {

    private static final long serialVersionUID = 1L;

    private List<SankeyNode> nodes;

    private List<SankeyLink> links;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SankeyNode implements Serializable {
        private String id;
        private String name;
        private String category;
        private Long value;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SankeyLink implements Serializable {
        private String source;
        private String target;
        private Long value;
        private String sourceName;
        private String targetName;
    }
}
