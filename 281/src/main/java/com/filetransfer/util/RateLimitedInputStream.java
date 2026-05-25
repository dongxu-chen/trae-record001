package com.filetransfer.util;

import java.io.IOException;
import java.io.InputStream;

public class RateLimitedInputStream extends InputStream {
    private final InputStream inputStream;
    private final RateLimiter rateLimiter;

    public RateLimitedInputStream(InputStream inputStream, long maxBytesPerSecond) {
        this.inputStream = inputStream;
        this.rateLimiter = new RateLimiter(maxBytesPerSecond);
    }

    @Override
    public int read() throws IOException {
        int b = inputStream.read();
        if (b != -1) {
            try {
                rateLimiter.acquire(1);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IOException("Interrupted while rate limiting", e);
            }
        }
        return b;
    }

    @Override
    public int read(byte[] b) throws IOException {
        int read = inputStream.read(b);
        if (read > 0) {
            try {
                rateLimiter.acquire(read);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IOException("Interrupted while rate limiting", e);
            }
        }
        return read;
    }

    @Override
    public int read(byte[] b, int off, int len) throws IOException {
        int read = inputStream.read(b, off, len);
        if (read > 0) {
            try {
                rateLimiter.acquire(read);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IOException("Interrupted while rate limiting", e);
            }
        }
        return read;
    }

    @Override
    public long skip(long n) throws IOException {
        return inputStream.skip(n);
    }

    @Override
    public int available() throws IOException {
        return inputStream.available();
    }

    @Override
    public void close() throws IOException {
        inputStream.close();
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
