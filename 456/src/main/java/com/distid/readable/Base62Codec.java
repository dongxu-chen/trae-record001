package com.distid.readable;

public class Base62Codec {

    private static final char[] ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz".toCharArray();
    private static final int BASE = ALPHABET.length;
    private static final int[] LOOKUP = new int[128];

    static {
        for (int i = 0; i < LOOKUP.length; i++) {
            LOOKUP[i] = -1;
        }
        for (int i = 0; i < BASE; i++) {
            LOOKUP[ALPHABET[i]] = i;
        }
    }

    public static String encode(long value) {
        if (value < 0) {
            throw new IllegalArgumentException("Value must be non-negative");
        }
        if (value == 0) {
            return "0";
        }
        StringBuilder sb = new StringBuilder();
        long remaining = value;
        while (remaining > 0) {
            sb.append(ALPHABET[(int) (remaining % BASE)]);
            remaining /= BASE;
        }
        return sb.reverse().toString();
    }

    public static long decode(String encoded) {
        long result = 0;
        for (int i = 0; i < encoded.length(); i++) {
            char c = encoded.charAt(i);
            if (c >= LOOKUP.length || LOOKUP[c] == -1) {
                throw new IllegalArgumentException("Invalid Base62 character: " + c);
            }
            result = result * BASE + LOOKUP[c];
        }
        return result;
    }

    public static String encodeWithPadding(long value, int minLength) {
        String encoded = encode(value);
        if (encoded.length() >= minLength) {
            return encoded;
        }
        StringBuilder sb = new StringBuilder();
        for (int i = encoded.length(); i < minLength; i++) {
            sb.append('0');
        }
        sb.append(encoded);
        return sb.toString();
    }
}
