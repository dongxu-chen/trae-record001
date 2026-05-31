package com.dlq.platform.common.utils;

import com.google.common.hash.Hashing;
import lombok.AccessLevel;
import lombok.NoArgsConstructor;
import org.apache.commons.lang3.StringUtils;

import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.UUID;

@NoArgsConstructor(access = AccessLevel.PRIVATE)
public class MessageIdGenerator {

    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");

    public static String generate() {
        return UUID.randomUUID().toString().replace("-", "");
    }

    public static String generateWithPrefix(String prefix) {
        String timePart = LocalDateTime.now().format(DATE_FORMATTER);
        String randomPart = UUID.randomUUID().toString().replace("-", "").substring(0, 12);
        if (StringUtils.isBlank(prefix)) {
            return timePart + randomPart;
        }
        return prefix + "_" + timePart + randomPart;
    }

    public static String generateByContent(String content) {
        if (StringUtils.isBlank(content)) {
            return generate();
        }
        return Hashing.murmur3_32_fixed().hashString(content, StandardCharsets.UTF_8).toString()
                + "_" + System.currentTimeMillis();
    }
}
