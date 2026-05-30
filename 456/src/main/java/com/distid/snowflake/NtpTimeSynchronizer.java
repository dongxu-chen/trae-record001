package com.distid.snowflake;

import lombok.extern.slf4j.Slf4j;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.locks.ReentrantLock;

@Slf4j
public class NtpTimeSynchronizer {

    private static final int NTP_PORT = 123;
    private static final int NTP_PACKET_SIZE = 48;
    private static final long NTP_EPOCH_OFFSET = 2208988800L;

    private final String[] ntpServers;
    private final int syncIntervalMinutes;
    private final long maxAcceptableOffsetMs;
    private final ScheduledExecutorService scheduler;
    private final ReentrantLock syncLock = new ReentrantLock();

    private volatile long networkOffsetMs = 0;
    private volatile long lastSyncTime = 0;
    private volatile boolean synchronizedOk = false;
    private final AtomicLong localTimeOffset = new AtomicLong(0);

    public NtpTimeSynchronizer() {
        this(new String[]{
                "pool.ntp.org",
                "time.windows.com",
                "time.apple.com",
                "ntp.aliyun.com"
        }, 5, 500);
    }

    public NtpTimeSynchronizer(String[] ntpServers, int syncIntervalMinutes, long maxAcceptableOffsetMs) {
        this.ntpServers = ntpServers;
        this.syncIntervalMinutes = syncIntervalMinutes;
        this.maxAcceptableOffsetMs = maxAcceptableOffsetMs;
        this.scheduler = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "ntp-sync");
            t.setDaemon(true);
            return t;
        });
    }

    @PostConstruct
    public void start() {
        syncNow();
        scheduler.scheduleAtFixedRate(this::syncNow, syncIntervalMinutes, syncIntervalMinutes, TimeUnit.MINUTES);
    }

    @PreDestroy
    public void stop() {
        scheduler.shutdownNow();
    }

    public void syncNow() {
        if (!syncLock.tryLock()) {
            log.debug("NTP sync already in progress, skipping");
            return;
        }
        try {
            List<Long> offsets = new ArrayList<>();
            for (String server : ntpServers) {
                try {
                    long offset = getNtpOffset(server);
                    if (Math.abs(offset) < maxAcceptableOffsetMs * 10) {
                        offsets.add(offset);
                    }
                } catch (Exception e) {
                    log.warn("Failed to sync with NTP server {}: {}", server, e.getMessage());
                }
            }

            if (!offsets.isEmpty()) {
                Collections.sort(offsets);
                long medianOffset = offsets.get(offsets.size() / 2);
                this.networkOffsetMs = medianOffset;
                this.localTimeOffset.set(medianOffset);
                this.lastSyncTime = System.currentTimeMillis();
                this.synchronizedOk = true;
                log.info("NTP sync completed. ServerCount={}, MedianOffset={}ms", offsets.size(), medianOffset);
            } else {
                log.warn("Failed to sync with any NTP server");
                this.synchronizedOk = false;
            }
        } finally {
            syncLock.unlock();
        }
    }

    private long getNtpOffset(String server) throws Exception {
        try (DatagramSocket socket = new DatagramSocket()) {
            socket.setSoTimeout(3000);
            InetAddress address = InetAddress.getByName(server);

            byte[] buf = new byte[NTP_PACKET_SIZE];
            buf[0] = 0x1B;

            long t1 = System.currentTimeMillis();
            DatagramPacket request = new DatagramPacket(buf, buf.length, address, NTP_PORT);
            socket.send(request);

            DatagramPacket response = new DatagramPacket(buf, buf.length);
            socket.receive(response);
            long t4 = System.currentTimeMillis();

            long t2 = getNtpTimestamp(buf, 32);
            long t3 = getNtpTimestamp(buf, 40);

            long offset = ((t2 - t1) + (t3 - t4)) / 2;
            long delay = (t4 - t1) - (t3 - t2);

            if (delay < 500) {
                return offset;
            }
            return 0;
        }
    }

    private long getNtpTimestamp(byte[] buf, int index) {
        long seconds = ((buf[index] & 0xFFL) << 24)
                | ((buf[index + 1] & 0xFFL) << 16)
                | ((buf[index + 2] & 0xFFL) << 8)
                | (buf[index + 3] & 0xFFL);
        long fraction = ((buf[index + 4] & 0xFFL) << 24)
                | ((buf[index + 5] & 0xFFL) << 16)
                | ((buf[index + 6] & 0xFFL) << 8)
                | (buf[index + 7] & 0xFFL);

        long ms = (seconds - NTP_EPOCH_OFFSET) * 1000 + (fraction * 1000L / 0x100000000L);
        return ms;
    }

    public long currentTimeMillis() {
        return System.currentTimeMillis() + localTimeOffset.get();
    }

    public long getNetworkOffsetMs() {
        return networkOffsetMs;
    }

    public long getLastSyncTime() {
        return lastSyncTime;
    }

    public boolean isSynchronizedOk() {
        return synchronizedOk;
    }
}
