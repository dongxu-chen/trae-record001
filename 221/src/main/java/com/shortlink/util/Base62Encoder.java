package com.shortlink.util;

import com.google.common.hash.Hashing;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;

@Component
public class Base62Encoder {

    private static final String BASE62_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
    private static final int BASE = 62;

    @Value("${shortlink.default-shortcode-length:6}")
    private int defaultShortCodeLength;

    public String encode(long num) {
        StringBuilder sb = new StringBuilder();
        while (num > 0) {
            sb.append(BASE62_CHARS.charAt((int) (num % BASE)));
            num /= BASE;
        }
        return sb.reverse().toString();
    }

    public String encodeWithPadding(long num, int length) {
        String encoded = encode(num);
        if (encoded.length() >= length) {
            return encoded.substring(encoded.length() - length);
        }
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < length - encoded.length(); i++) {
            sb.append('0');
        }
        sb.append(encoded);
        return sb.toString();
    }

    public String generateShortCodeFromSnowflake(long snowflakeId) {
        return encodeWithPadding(snowflakeId, defaultShortCodeLength);
    }

    @Deprecated
    public String generateShortCode(String url, long id) {
        String combined = url + id + System.nanoTime();
        long hash = Hashing.murmur3_128().hashString(combined, StandardCharsets.UTF_8).asLong();
        hash = Math.abs(hash);
        return encodeWithPadding(hash, defaultShortCodeLength);
    }

    @Deprecated
    public String generateShortCode(long id) {
        return encodeWithPadding(id, defaultShortCodeLength);
    }

    @Deprecated
    public String generateRandomShortCode() {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < defaultShortCodeLength; i++) {
            int index = (int) (Math.random() * BASE);
            sb.append(BASE62_CHARS.charAt(index));
        }
        return sb.toString();
    }

    public String generateFingerprint(String... inputs) {
        StringBuilder combined = new StringBuilder();
        for (String input : inputs) {
            if (input != null) {
                combined.append(input);
            }
        }
        long hash = Hashing.murmur3_128().hashString(combined.toString(), StandardCharsets.UTF_8).asLong();
        return Long.toHexString(hash);
    }

    public boolean isValidShortCode(String code) {
        if (code == null || code.length() < 4 || code.length() > 16) {
            return false;
        }
        for (char c : code.toCharArray()) {
            if (BASE62_CHARS.indexOf(c) == -1) {
                return false;
            }
        }
        return true;
    }

    public long decode(String str) {
        long num = 0;
        for (char c : str.toCharArray()) {
            num = num * BASE + BASE62_CHARS.indexOf(c);
        }
        return num;
    }
}
