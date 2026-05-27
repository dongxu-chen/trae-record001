package com.grayrelease.common.util;

import java.util.UUID;

public class IdGenerator {

    public static String generateId() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 16);
    }

    public static String generateReleaseId(String serviceName) {
        return "rel-" + serviceName + "-" + generateId();
    }

    public static String generateVersionId(String serviceName, String version) {
        return "ver-" + serviceName + "-" + version + "-" + generateId().substring(0, 8);
    }
}