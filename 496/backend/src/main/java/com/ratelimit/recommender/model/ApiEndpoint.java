package com.ratelimit.recommender.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ApiEndpoint {
    private String path;
    private String method;
    private String description;
    private List<String> tags;
    private ApiMetrics metrics;
    private LocalDateTime lastUpdate;
}
