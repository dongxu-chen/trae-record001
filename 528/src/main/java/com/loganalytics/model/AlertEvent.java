package com.loganalytics.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AlertEvent implements Serializable {
    private String alertType;
    private String dimension;
    private String value;
    private double currentValue;
    private double threshold;
    private String severity;
    private String message;
    private long timestamp;
}
