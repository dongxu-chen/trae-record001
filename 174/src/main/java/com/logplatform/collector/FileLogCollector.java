package com.logplatform.collector;

import com.logplatform.config.LogCollectorProperties;
import com.logplatform.model.LogEntry;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import java.util.regex.Pattern;

@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnProperty(prefix = "log.collector.file", name = "enabled", havingValue = "true")
public class FileLogCollector implements LogCollector {

    private final LogCollectorProperties properties;
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(2);
    private final Map<String, Long> filePositions = new ConcurrentHashMap<>();
    private volatile boolean running = false;
    private LogHandler logHandler;

    @Override
    public String getName() {
        return "FileLogCollector";
    }

    @PostConstruct
    @Override
    public void start() {
        if (running) return;
        running = true;

        scheduler.scheduleAtFixedRate(this::scanAndCollect, 0,
                properties.getFile().getScanInterval(), TimeUnit.MILLISECONDS);

        log.info("FileLogCollector started");
    }

    @PreDestroy
    @Override
    public void stop() {
        running = false;
        scheduler.shutdown();
        log.info("FileLogCollector stopped");
    }

    @Override
    public boolean isRunning() {
        return running;
    }

    private void scanAndCollect() {
        for (LogCollectorProperties.FileSource source : properties.getFile().getSources()) {
            try {
                collectFromSource(source);
            } catch (Exception e) {
                log.error("Error collecting logs from source: {}", source.getName(), e);
            }
        }
    }

    private void collectFromSource(LogCollectorProperties.FileSource source) throws IOException {
        PathMatcher matcher = FileSystems.getDefault().getPathMatcher("glob:" + source.getPath());
        Path dir = Paths.get(source.getPath()).getParent();

        if (dir == null || !Files.exists(dir)) {
            log.warn("Directory does not exist: {}", dir);
            return;
        }

        try (DirectoryStream<Path> stream = Files.newDirectoryStream(dir,
                path -> matcher.matches(path.getFileName() != null ? path : Paths.get(""))) {

            for (Path file : stream) {
                if (Files.isRegularFile(file)) {
                    processFile(file, source);
                }
            }
        }
    }

    private void processFile(Path file, LogCollectorProperties.FileSource source) throws IOException {
        String filePath = file.toString();
        long lastPosition = filePositions.getOrDefault(filePath, 0L);
        long currentSize = Files.size(file);

        if (currentSize < lastPosition) {
            lastPosition = 0;
        }

        if (currentSize == lastPosition) {
            return;
        }

        try (BufferedReader reader = Files.newBufferedReader(file,
                java.nio.charset.Charset.forName(source.getEncoding()))) {
            reader.skip(lastPosition);

            Pattern multilinePattern = source.getMultilinePattern() != null
                    ? Pattern.compile(source.getMultilinePattern()) : null;

            String line;
            StringBuilder currentLog = new StringBuilder();

            while ((line = reader.readLine()) != null) {
                if (multilinePattern != null && multilinePattern.matcher(line).find()
                        && currentLog.length() > 0) {
                    emitLogEntry(currentLog.toString(), source);
                    currentLog.setLength(0);
                }
                currentLog.append(line).append("\n");
            }

            if (currentLog.length() > 0) {
                emitLogEntry(currentLog.toString(), source);
            }

            filePositions.put(filePath, currentSize);
        }
    }

    private void emitLogEntry(String message, LogCollectorProperties.FileSource source) {
        LogEntry entry = new LogEntry();
        entry.setAppName(source.getName());
        entry.setMessage(message.trim());
        entry.setTimestamp(Instant.now());
        entry.setLevel(parseLevel(message));

        if (logHandler != null) {
            logHandler.onLog(entry);
        }
    }

    private String parseLevel(String message) {
        if (message.contains("ERROR")) return "ERROR";
        if (message.contains("WARN")) return "WARN";
        if (message.contains("INFO")) return "INFO";
        if (message.contains("DEBUG")) return "DEBUG";
        if (message.contains("TRACE")) return "TRACE";
        return "INFO";
    }

    @Override
    public void collect(List<LogEntry> logs) {
    }

    public void setLogHandler(LogHandler handler) {
        this.logHandler = handler;
    }
}
