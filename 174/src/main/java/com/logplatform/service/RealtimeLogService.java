package com.logplatform.service;

import com.logplatform.model.LogEntry;
import com.logplatform.websocket.LogStreamWebSocketHandler;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;

@Slf4j
@Service
@RequiredArgsConstructor
public class RealtimeLogService {

    private final LogStreamWebSocketHandler webSocketHandler;
    private final BlockingQueue<LogEntry> logBuffer = new LinkedBlockingQueue<>(10000);
    private volatile boolean running = true;
    private final Thread broadcastThread;

    {
        broadcastThread = new Thread(this::broadcastLoop, "realtime-log-broadcaster");
        broadcastThread.setDaemon(true);
        broadcastThread.start();
    }

    public void publishLog(LogEntry logEntry) {
        if (logEntry == null) return;

        if (!logBuffer.offer(logEntry)) {
            log.debug("Log buffer is full, dropping log entry");
        }
    }

    private void broadcastLoop() {
        while (running) {
            try {
                LogEntry logEntry = logBuffer.take();
                webSocketHandler.broadcastLog(logEntry);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            } catch (Exception e) {
                log.error("Error in broadcast loop", e);
            }
        }
    }

    public int getActiveConnections() {
        return webSocketHandler.getActiveConnections();
    }

    public int getBufferSize() {
        return logBuffer.size();
    }

    public void stop() {
        running = false;
        broadcastThread.interrupt();
    }
}
