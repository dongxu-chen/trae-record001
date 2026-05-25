package com.filetransfer.util;

import lombok.extern.slf4j.Slf4j;

import java.io.IOException;
import java.io.InputStream;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.atomic.AtomicBoolean;

@Slf4j
public class TokenBucketLimitedInputStream extends InputStream {
    private final InputStream inputStream;
    private final TokenBucketRateLimiter rateLimiter;
    private static final int BUFFER_SIZE = 8192;
    private static final int MAX_QUEUE_SIZE = 16;

    private final LinkedBlockingQueue<byte[]> bufferQueue;
    private final ExecutorService readExecutor;
    private final AtomicBoolean isReading;
    private final AtomicBoolean isClosed;
    private byte[] currentBuffer;
    private int bufferPosition;
    private volatile IOException readException;

    public TokenBucketLimitedInputStream(InputStream inputStream, long maxBytesPerSecond) {
        this.inputStream = inputStream;
        this.rateLimiter = TokenBucketRateLimiter.create(maxBytesPerSecond);
        this.bufferQueue = new LinkedBlockingQueue<>(MAX_QUEUE_SIZE);
        this.readExecutor = Executors.newSingleThreadExecutor(r -> {
            Thread t = new Thread(r, "async-reader");
            t.setDaemon(true);
            return t;
        });
        this.isReading = new AtomicBoolean(false);
        this.isClosed = new AtomicBoolean(false);
        this.currentBuffer = null;
        this.bufferPosition = 0;

        startAsyncReading();
    }

    private void startAsyncReading() {
        if (isReading.compareAndSet(false, true)) {
            CompletableFuture.runAsync(() -> {
                try {
                    while (!isClosed.get() && !Thread.currentThread().isInterrupted()) {
                        byte[] buffer = new byte[BUFFER_SIZE];
                        int bytesRead = inputStream.read(buffer);
                        if (bytesRead == -1) {
                            bufferQueue.offer(new byte[0]);
                            break;
                        }
                        if (bytesRead < BUFFER_SIZE) {
                            byte[] trimmed = new byte[bytesRead];
                            System.arraycopy(buffer, 0, trimmed, 0, bytesRead);
                            bufferQueue.offer(trimmed);
                        } else {
                            bufferQueue.offer(buffer);
                        }
                    }
                } catch (IOException e) {
                    readException = e;
                    bufferQueue.offer(new byte[0]);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }, readExecutor).exceptionally(ex -> {
                log.error("异步读取失败", ex);
                return null;
            });
        }
    }

    @Override
    public int read() throws IOException {
        checkException();
        if (!fillBufferIfNeeded()) {
            return -1;
        }

        try {
            rateLimiter.acquire(1);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IOException("Interrupted while rate limiting", e);
        }

        return currentBuffer[bufferPosition++] & 0xFF;
    }

    @Override
    public int read(byte[] b) throws IOException {
        return read(b, 0, b.length);
    }

    @Override
    public int read(byte[] b, int off, int len) throws IOException {
        if (b == null) {
            throw new NullPointerException();
        }
        if (off < 0 || len < 0 || len > b.length - off) {
            throw new IndexOutOfBoundsException();
        }
        if (len == 0) {
            return 0;
        }

        checkException();
        if (!fillBufferIfNeeded()) {
            return -1;
        }

        int available = currentBuffer.length - bufferPosition;
        int toRead = Math.min(len, available);

        try {
            rateLimiter.acquire(toRead);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IOException("Interrupted while rate limiting", e);
        }

        System.arraycopy(currentBuffer, bufferPosition, b, off, toRead);
        bufferPosition += toRead;

        return toRead;
    }

    private boolean fillBufferIfNeeded() throws IOException {
        if (currentBuffer == null || bufferPosition >= currentBuffer.length) {
            try {
                currentBuffer = bufferQueue.take();
                bufferPosition = 0;
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IOException("Interrupted while waiting for buffer", e);
            }
            checkException();
            return currentBuffer.length > 0;
        }
        return true;
    }

    private void checkException() throws IOException {
        if (readException != null) {
            throw readException;
        }
    }

    @Override
    public long skip(long n) throws IOException {
        return inputStream.skip(n);
    }

    @Override
    public int available() throws IOException {
        int queued = 0;
        if (currentBuffer != null) {
            queued += currentBuffer.length - bufferPosition;
        }
        queued += bufferQueue.size() * BUFFER_SIZE;
        return Math.min(inputStream.available(), queued);
    }

    @Override
    public void close() throws IOException {
        if (isClosed.compareAndSet(false, true)) {
            readExecutor.shutdownNow();
            rateLimiter.stop();
            inputStream.close();
        }
    }

    @Override
    public void mark(int readlimit) {
        inputStream.mark(readlimit);
    }

    @Override
    public void reset() throws IOException {
        inputStream.reset();
    }

    @Override
    public boolean markSupported() {
        return inputStream.markSupported();
    }
}
