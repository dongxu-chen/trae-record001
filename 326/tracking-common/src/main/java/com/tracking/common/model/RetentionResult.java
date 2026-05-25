package com.tracking.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RetentionResult implements Serializable {

    private static final long serialVersionUID = 1L;

    private String retentionType;

    private String initialEvent;

    private String returnEvent;

    private Long startTime;

    private Long endTime;

    private Long initialUsers;

    private List<RetentionItem> retentionItems;

    private Map<String, List<RetentionItem>> groupResults;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RetentionItem implements Serializable {
        private int day;
        private String label;
        private Long returnUsers;
        private Double retentionRate;
    }
}
