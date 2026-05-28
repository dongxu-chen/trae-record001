package com.mqmonitor.common.util;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedDeque;

public class TimeWindow<T> {
    private final long windowSizeMs;
    private final ConcurrentLinkedDeque<TimedValue<T>> deque = new ConcurrentLinkedDeque<>();

    public TimeWindow(long windowSizeMs) {
        this.windowSizeMs = windowSizeMs;
    }

    public void add(T value) {
        add(value, Instant.now().toEpochMilli());
    }

    public void add(T value, long timestamp) {
        deque.addLast(new TimedValue<>(value, timestamp));
        evictExpired();
    }

    public List<T> getValues() {
        evictExpired();
        List<T> values = new ArrayList<>();
        for (TimedValue<T> tv : deque) {
            values.add(tv.value);
        }
        return values;
    }

    public int size() {
        evictExpired();
        return deque.size();
    }

    public boolean isEmpty() {
        evictExpired();
        return deque.isEmpty();
    }

    public void clear() {
        deque.clear();
    }

    private void evictExpired() {
        long cutoff = Instant.now().toEpochMilli() - windowSizeMs;
        while (!deque.isEmpty() && deque.peekFirst().timestamp < cutoff) {
            deque.pollFirst();
        }
    }

    private static class TimedValue<T> {
        T value;
        long timestamp;

        TimedValue(T value, long timestamp) {
            this.value = value;
            this.timestamp = timestamp;
        }
    }
}
