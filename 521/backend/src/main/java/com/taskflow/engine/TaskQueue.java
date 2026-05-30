package com.taskflow.engine;

import lombok.Data;
import lombok.Getter;

import java.util.concurrent.BlockingQueue;
import java.util.concurrent.PriorityBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

public class TaskQueue {

    private final PriorityBlockingQueue<QueueItem> queue = new PriorityBlockingQueue<>(10000);

    @Data
    public static class QueueItem implements Comparable<QueueItem> {
        private final Long workflowExecutionId;
        private final String taskKey;
        private final int priority;
        private final long timestamp;
        private final long seq;

        private static final AtomicLong seqGenerator = new AtomicLong(0);

        public QueueItem(Long workflowExecutionId, String taskKey, int priority) {
            this.workflowExecutionId = workflowExecutionId;
            this.taskKey = taskKey;
            this.priority = priority;
            this.timestamp = System.currentTimeMillis();
            this.seq = seqGenerator.incrementAndGet();
        }

        @Override
        public int compareTo(QueueItem other) {
            if (this.priority != other.priority) {
                return Integer.compare(other.priority, this.priority);
            }
            if (this.timestamp != other.timestamp) {
                return Long.compare(this.timestamp, other.timestamp);
            }
            return Long.compare(this.seq, other.seq);
        }
    }

    public boolean enqueue(Long workflowExecutionId, String taskKey, int priority) {
        return queue.offer(new QueueItem(workflowExecutionId, taskKey, priority));
    }

    public QueueItem dequeue(long timeoutMs) throws InterruptedException {
        return queue.poll(timeoutMs, TimeUnit.MILLISECONDS);
    }

    public int size() {
        return queue.size();
    }

    public boolean isEmpty() {
        return queue.isEmpty();
    }

    public int getHighPriorityCount(int threshold) {
        return (int) queue.stream().filter(item -> item.getPriority() >= threshold).count();
    }
}
