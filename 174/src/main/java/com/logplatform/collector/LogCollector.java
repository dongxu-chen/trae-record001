package com.logplatform.collector;

import com.logplatform.model.LogEntry;

import java.util.List;

public interface LogCollector {

    String getName();

    void start();

    void stop();

    boolean isRunning();

    void collect(List<LogEntry> logs);

    interface LogHandler {
        void onLog(LogEntry logEntry);
    }
}
