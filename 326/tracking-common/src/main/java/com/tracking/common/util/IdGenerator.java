package com.tracking.common.util;

import java.util.UUID;

public class IdGenerator {

    private static final String PREFIX_ANONYMOUS = "anon_";
    private static final String PREFIX_SESSION = "sess_";
    private static final String PREFIX_EVENT = "evt_";
    private static final String PREFIX_DEVICE = "dev_";

    public static String generateEventId() {
        return PREFIX_EVENT + System.currentTimeMillis() + "_" + generateShortUUID();
    }

    public static String generateAnonymousId() {
        return PREFIX_ANONYMOUS + generateShortUUID();
    }

    public static String generateSessionId() {
        return PREFIX_SESSION + System.currentTimeMillis() + "_" + generateShortUUID();
    }

    public static String generateDeviceId() {
        return PREFIX_DEVICE + generateShortUUID();
    }

    public static String generateShortUUID() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 16);
    }

    public static String generateUUID() {
        return UUID.randomUUID().toString().replace("-", "");
    }

    public static boolean isAnonymousId(String id) {
        return id != null && id.startsWith(PREFIX_ANONYMOUS);
    }

    public static boolean isSessionId(String id) {
        return id != null && id.startsWith(PREFIX_SESSION);
    }
}
