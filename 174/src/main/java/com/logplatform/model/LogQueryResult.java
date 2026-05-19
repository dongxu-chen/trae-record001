package com.logplatform.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LogQueryResult {

    private long total;

    private int page;

    private int size;

    private long tookMs;

    private List<LogEntry> logs;
}
