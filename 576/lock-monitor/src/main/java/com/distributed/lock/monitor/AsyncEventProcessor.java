package com.distributed.lock.monitor;

import com.distributed.lock.core.LockEvent;
import com.distributed.lock.core.LockEventListener;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.util.List;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

public class AsyncEventProcessor {

    private static final Logger logger = LoggerFactory.getLogger(AsyncEventProcessor.class);
    private static final int DEFAULT_QUEUE_CAPACITY = 10000;
    private static final int DEFAULT_WORKER_THREADS = 2;
    private static final long BATCH_TIMEOUT_MS = 100;
    private static final int BATCH_SIZE = 100;

    private final BlockingQueue<LockEvent> eventQueue;
    private final ExecutorService workerPool;
    private final List<LockEventListener> listeners;
    private final SamplingStrategy samplingStrategy;
    private final AtomicLong totalEventsProcessed = new AtomicLong(0);
    private final AtomicLong totalEventsSampled = new AtomicLong(0);
    private volatile boolean running = true;

    public AsyncEventProcessor(List<LockEventListener> listeners, SamplingStrategy samplingStrategy) {
        this(listeners, samplingStrategy, DEFAULT_QUEUE_CAPACITY, DEFAULT_WORKER_THREADS);
    }

    public AsyncEventProcessor(List<LockEventListener> listeners, SamplingStrategy samplingStrategy,
                               int queueCapacity, int workerThreads) {
        this.listeners = listeners;
        this.samplingStrategy = samplingStrategy;
        this.eventQueue = new ArrayBlockingQueue<>(queueCapacity);
        this.workerPool = Executors.newFixedThreadPool(workerThreads, r -> {
            Thread thread = new Thread(r, "lock-monitor-worker");
            thread.setDaemon(true);
            return thread;
        });
    }

    @PostConstruct
    public void start() {
        running = true;
        for (int i = 0; i < DEFAULT_WORKER_THREADS; i++) {
            workerPool.submit(this::processEvents);
        }
        workerPool.submit(this::adjustSamplingRate);
        logger.info("Async event processor started with {} worker threads", DEFAULT_WORKER_THREADS);
    }

    @PreDestroy
    public void stop() {
        running = false;
        workerPool.shutdown();
        try {
            if (!workerPool.awaitTermination(5, TimeUnit.SECONDS)) {
                workerPool.shutdownNow();
            }
        } catch (InterruptedException e) {
            workerPool.shutdownNow();
            Thread.currentThread().interrupt();
        }
        logger.info("Async event processor stopped. Total events processed: {}, sampled: {}",
                totalEventsProcessed.get(), totalEventsSampled.get());
    }

    public boolean submit(LockEvent event) {
        if (!running) {
            return false;
        }

        totalEventsProcessed.incrementAndGet();

        if (!samplingStrategy.shouldSample(event)) {
            return true;
        }

        totalEventsSampled.incrementAndGet();
        return eventQueue.offer(event);
    }

    private void processEvents() {
        while (running || !eventQueue.isEmpty()) {
            try {
                LockEvent event = eventQueue.poll(BATCH_TIMEOUT_MS, TimeUnit.MILLISECONDS);
                if (event != null) {
                    dispatchEvent(event);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            } catch (Exception e) {
                logger.warn("Error processing lock event", e);
            }
        }
    }

    private void dispatchEvent(LockEvent event) {
        for (LockEventListener listener : listeners) {
            try {
                listener.onEvent(event);
            } catch (Exception e) {
                logger.warn("Listener {} failed to process event", listener.getClass().getSimpleName(), e);
            }
        }
    }

    private void adjustSamplingRate() {
        while (running) {
            try {
                Thread.sleep(60000);
                long eventsPerMinute = totalEventsProcessed.getAndSet(0);
                samplingStrategy.adjustGlobalSampleRate(eventsPerMinute);
                logger.debug("Adjusted sampling rate. Events/min: {}, rate: {}",
                        eventsPerMinute, samplingStrategy.getGlobalSampleRate());
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
    }

    public long getQueueSize() {
        return eventQueue.size();
    }

    public long getTotalEventsProcessed() {
        return totalEventsProcessed.get();
    }

    public long getTotalEventsSampled() {
        return totalEventsSampled.get();
    }

    public double getSamplingRatio() {
        long total = totalEventsProcessed.get();
        if (total == 0) {
            return 1.0;
        }
        return (double) totalEventsSampled.get() / total;
    }
}