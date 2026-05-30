package com.migration.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConsistencyCheckResult {

    private String checkId;
    private long timestamp;
    private boolean consistent;
    private int totalServices;
    private int matchedServices;
    private int mismatchedServices;
    private int onlyInEureka;
    private int onlyInNacos;
    private List<ServiceDifference> differences;
    private List<String> alerts;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ServiceDifference {
        private String serviceId;
        private DifferenceType type;
        private String eurekaInstances;
        private String nacosInstances;
        private String detail;
        private List<MetadataDiff> metadataDiffs;

        public enum DifferenceType {
            ONLY_IN_EUREKA,
            ONLY_IN_NACOS,
            INSTANCE_COUNT_MISMATCH,
            METADATA_MISMATCH,
            STATUS_MISMATCH
        }
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MetadataDiff {
        private String instanceKey;
        private String key;
        private String eurekaValue;
        private String nacosValue;
        private DiffType diffType;

        public enum DiffType {
            VALUE_MISMATCH,
            MISSING_IN_EUREKA,
            MISSING_IN_NACOS
        }
    }
}
