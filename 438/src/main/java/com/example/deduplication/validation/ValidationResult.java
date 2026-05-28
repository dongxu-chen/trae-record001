package com.example.deduplication.validation;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ValidationResult implements Serializable {

    private static final long serialVersionUID = 1L;

    private String validationId;
    private String requestHash;
    private long timestamp;
    private boolean shouldBypass;
    private boolean responseMatch;
    private int cachedResponseStatus;
    private int actualResponseStatus;
    private long responseDiffMs;
    private String mismatchDetails;
    private double similarityScore;
}
