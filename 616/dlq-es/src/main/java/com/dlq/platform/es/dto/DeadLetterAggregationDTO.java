package com.dlq.platform.es.dto;

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
public class DeadLetterAggregationDTO {

    private List<ReasonTypeBucket> reasonTypeStats;

    private List<TimeBucket> timeStats;

    private List<MqTypeBucket> mqTypeStats;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ReasonTypeBucket {
        private String reasonType;
        private long count;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TimeBucket {
        private String time;
        private long count;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MqTypeBucket {
        private String mqType;
        private long count;
    }
}
