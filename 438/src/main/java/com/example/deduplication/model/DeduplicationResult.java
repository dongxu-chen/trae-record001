package com.example.deduplication.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DeduplicationResult {

    private boolean isDuplicate;
    private CachedResponse cachedResponse;
    private String requestHash;
    private boolean shouldProcess;
    private String fingerprint;
    private boolean isBypassValidation;

    public static DeduplicationResult duplicate(CachedResponse response, String hash) {
        return DeduplicationResult.builder()
                .isDuplicate(true)
                .cachedResponse(response)
                .requestHash(hash)
                .shouldProcess(false)
                .build();
    }

    public static DeduplicationResult firstRequest(String hash) {
        return DeduplicationResult.builder()
                .isDuplicate(false)
                .requestHash(hash)
                .shouldProcess(true)
                .build();
    }
}
