package com.filetransfer.util;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Comparator;
import java.util.Map;
import java.util.SortedSet;
import java.util.TreeSet;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.locks.ReentrantLock;

@Slf4j
@Component
public class ChunkOrderManager {
    private final Map<String, UploadChunkState> uploadStates = new ConcurrentHashMap<>();
    private final int REORDER_WINDOW_SIZE = 10;

    public ChunkCheckResult checkChunkOrder(String uploadId, int chunkNumber, int totalChunks) {
        UploadChunkState state = uploadStates.computeIfAbsent(uploadId, k -> new UploadChunkState());
        return state.checkAndProcessChunk(chunkNumber, totalChunks);
    }

    public void removeUploadState(String uploadId) {
        uploadStates.remove(uploadId);
    }

    public boolean isNextChunkExpected(String uploadId, int chunkNumber) {
        UploadChunkState state = uploadStates.get(uploadId);
        return state != null && chunkNumber == state.expectedChunkNumber;
    }

    public int getExpectedChunkNumber(String uploadId) {
        UploadChunkState state = uploadStates.get(uploadId);
        return state != null ? state.expectedChunkNumber : 1;
    }

    public static class ChunkCheckResult {
        private final boolean canProcess;
        private final boolean isDuplicate;
        private final boolean isOutOfOrder;
        private final String message;
        private final int expectedChunk;

        public ChunkCheckResult(boolean canProcess, boolean isDuplicate, boolean isOutOfOrder,
                                String message, int expectedChunk) {
            this.canProcess = canProcess;
            this.isDuplicate = isDuplicate;
            this.isOutOfOrder = isOutOfOrder;
            this.message = message;
            this.expectedChunk = expectedChunk;
        }

        public boolean canProcess() {
            return canProcess;
        }

        public boolean isDuplicate() {
            return isDuplicate;
        }

        public boolean isOutOfOrder() {
            return isOutOfOrder;
        }

        public String getMessage() {
            return message;
        }

        public int getExpectedChunk() {
            return expectedChunk;
        }
    }

    private class UploadChunkState {
        private int expectedChunkNumber = 1;
        private final SortedSet<Integer> outOfOrderChunks = new TreeSet<>(Comparator.naturalOrder());
        private final ReentrantLock lock = new ReentrantLock();

        public ChunkCheckResult checkAndProcessChunk(int chunkNumber, int totalChunks) {
            lock.lock();
            try {
                if (chunkNumber < 1 || chunkNumber > totalChunks) {
                    return new ChunkCheckResult(false, false, false,
                            "分片号超出范围: " + chunkNumber + "/" + totalChunks, expectedChunkNumber);
                }

                if (chunkNumber < expectedChunkNumber) {
                    return new ChunkCheckResult(false, true, false,
                            "分片已上传: " + chunkNumber, expectedChunkNumber);
                }

                if (chunkNumber == expectedChunkNumber) {
                    processSequentialChunks();
                    return new ChunkCheckResult(true, false, false,
                            "分片顺序正确，可以处理", expectedChunkNumber);
                }

                if (chunkNumber - expectedChunkNumber <= REORDER_WINDOW_SIZE) {
                    outOfOrderChunks.add(chunkNumber);
                    return new ChunkCheckResult(true, false, true,
                            "乱序分片已缓存，将在后续重排", expectedChunkNumber);
                }

                return new ChunkCheckResult(false, false, true,
                        "分片号超出重排窗口，请稍后重试", expectedChunkNumber);
            } finally {
                lock.unlock();
            }
        }

        private void processSequentialChunks() {
            expectedChunkNumber++;
            while (!outOfOrderChunks.isEmpty() &&
                    outOfOrderChunks.first() == expectedChunkNumber) {
                outOfOrderChunks.remove(expectedChunkNumber);
                expectedChunkNumber++;
            }
        }
    }
}
