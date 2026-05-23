package com.analytics.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PipelineDynamicConfig implements Serializable {
    private String configId;
    private long windowSizeMs;
    private long allowedLatenessMs;
    private boolean enableDeduplication;
    private double bloomFilterFpp;
    private int bloomFilterExpectedInsertions;
    private long timestamp;
    private String version;
}
