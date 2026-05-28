package com.example.deduplication.learning;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.concurrent.atomic.AtomicLong;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RequestPattern implements Serializable {

    private static final long serialVersionUID = 1L;

    private String patternId;
    private String pathPattern;
    private String method;
    private String userIdPattern;
    private AtomicLong occurrenceCount;
    private long firstSeenTimestamp;
    private long lastSeenTimestamp;
    private double similarityScore;
    private boolean isVerifiedPattern;
    private long deduplicationCount;

    public void incrementOccurrence() {
        occurrenceCount.incrementAndGet();
        lastSeenTimestamp = System.currentTimeMillis();
    }

    public long getOccurrenceCount() {
        return occurrenceCount.get();
    }
}
