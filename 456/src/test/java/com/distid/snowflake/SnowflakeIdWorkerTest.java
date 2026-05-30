package com.distid.snowflake;

import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import static org.junit.jupiter.api.Assertions.*;

class SnowflakeIdWorkerTest {

    @Test
    void shouldGenerateUniqueId() {
        SnowflakeIdWorker worker = new SnowflakeIdWorker(1, 1, 5);
        long id1 = worker.nextId();
        long id2 = worker.nextId();
        assertNotEquals(id1, id2);
        assertTrue(id2 > id1);
    }

    @Test
    void shouldGenerateTrendIncreasingIds() {
        SnowflakeIdWorker worker = new SnowflakeIdWorker(1, 1, 5);
        long prev = worker.nextId();
        for (int i = 0; i < 1000; i++) {
            long current = worker.nextId();
            assertTrue(current >= prev, "IDs should be trend increasing");
            prev = current;
        }
    }

    @Test
    void shouldGenerateUniqueIdsConcurrently() throws InterruptedException {
        SnowflakeIdWorker worker = new SnowflakeIdWorker(1, 1, 5);
        int threadCount = 16;
        int idsPerThread = 10000;
        Set<Long> allIds = ConcurrentHashMap.newKeySet();
        CountDownLatch latch = new CountDownLatch(threadCount);
        ExecutorService executor = Executors.newFixedThreadPool(threadCount);

        for (int t = 0; t < threadCount; t++) {
            executor.submit(() -> {
                try {
                    for (int i = 0; i < idsPerThread; i++) {
                        allIds.add(worker.nextId());
                    }
                } finally {
                    latch.countDown();
                }
            });
        }

        latch.await();
        executor.shutdown();
        assertEquals(threadCount * idsPerThread, allIds.size(), "All generated IDs should be unique");
    }

    @Test
    void shouldThrowOnInvalidWorkerId() {
        assertThrows(IllegalArgumentException.class, () -> new SnowflakeIdWorker(-1, 1, 5));
        assertThrows(IllegalArgumentException.class, () -> new SnowflakeIdWorker(32, 1, 5));
    }

    @Test
    void shouldThrowOnInvalidDatacenterId() {
        assertThrows(IllegalArgumentException.class, () -> new SnowflakeIdWorker(1, -1, 5));
        assertThrows(IllegalArgumentException.class, () -> new SnowflakeIdWorker(1, 32, 5));
    }

    @Test
    void shouldExtractWorkerIdFromGeneratedId() {
        SnowflakeIdWorker worker = new SnowflakeIdWorker(5, 3, 5);
        long id = worker.nextId();
        long workerIdBits = 5L;
        long sequenceBits = 12L;
        long extractedWorkerId = (id >> sequenceBits) & ~(-1L << workerIdBits);
        assertEquals(5, extractedWorkerId);
    }
}
