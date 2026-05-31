package com.benchmark.generator;

import java.security.SecureRandom;
import java.util.Random;

public class RandomIdGenerator implements IdGenerator {

    private final Random random;
    private final int length;

    public RandomIdGenerator() {
        this(16);
    }

    public RandomIdGenerator(int length) {
        this.random = new SecureRandom();
        this.length = length;
    }

    @Override
    public String nextId() {
        StringBuilder sb = new StringBuilder(length);
        for (int i = 0; i < length; i++) {
            int digit = random.nextInt(10);
            sb.append(digit);
        }
        return sb.toString();
    }
}
