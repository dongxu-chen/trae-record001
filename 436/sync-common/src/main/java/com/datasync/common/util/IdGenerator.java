package com.datasync.common.util;

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.concurrent.atomic.AtomicLong;

public class IdGenerator {
    private static final AtomicLong SEQUENCE = new AtomicLong(0);
    private static final String HOST_ID;
    private static final long MAX_SEQUENCE = 99999L;

    static {
        String hostId;
        try {
            String hostName = InetAddress.getLocalHost().getHostName();
            hostId = Math.abs(hostName.hashCode()) % 1000 + "";
        } catch (UnknownHostException e) {
            hostId = "000";
        }
        HOST_ID = String.format("%03d", Integer.parseInt(hostId));
    }

    private IdGenerator() {
    }

    public static String generateEventId() {
        long sequence = SEQUENCE.incrementAndGet();
        if (sequence > MAX_SEQUENCE) {
            SEQUENCE.set(0);
            sequence = SEQUENCE.incrementAndGet();
        }
        long timestamp = System.currentTimeMillis();
        return String.format("EVT_%d_%s_%05d", timestamp, HOST_ID, sequence);
    }

    public static String generateMessageId(String prefix) {
        long sequence = SEQUENCE.incrementAndGet();
        if (sequence > MAX_SEQUENCE) {
            SEQUENCE.set(0);
            sequence = SEQUENCE.incrementAndGet();
        }
        long timestamp = System.currentTimeMillis();
        return String.format("%s_%d_%s_%05d", prefix, timestamp, HOST_ID, sequence);
    }
}
