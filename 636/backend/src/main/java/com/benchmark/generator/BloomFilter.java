package com.benchmark.generator;

import java.util.BitSet;

public class BloomFilter {

    private final BitSet bitSet;
    private final int bitSetSize;
    private final int[] hashSeeds;
    private final int hashFunctionCount;
    private long insertedCount = 0;
    private long expectedInsertions;
    private double falsePositiveProbability;

    public BloomFilter(long expectedInsertions, double falsePositiveProbability) {
        this.expectedInsertions = expectedInsertions;
        this.falsePositiveProbability = falsePositiveProbability;

        this.bitSetSize = optimalBitSetSize(expectedInsertions, falsePositiveProbability);
        this.hashFunctionCount = optimalHashFunctionCount(bitSetSize, expectedInsertions);
        this.bitSet = new BitSet(bitSetSize);
        this.hashSeeds = generateHashSeeds(hashFunctionCount);
    }

    private static int optimalBitSetSize(long n, double p) {
        if (p == 0) p = Double.MIN_VALUE;
        return (int) Math.ceil(-n * Math.log(p) / (Math.log(2) * Math.log(2)));
    }

    private static int optimalHashFunctionCount(int m, long n) {
        return Math.max(1, (int) Math.round((double) m / n * Math.log(2)));
    }

    private int[] generateHashSeeds(int count) {
        int[] seeds = new int[count];
        for (int i = 0; i < count; i++) {
            seeds[i] = 0x9e3779b9 + (i << 6) + (i >> 2);
        }
        return seeds;
    }

    private int murmurHash(String item, int seed) {
        int h = seed;
        for (int i = 0; i < item.length(); i++) {
            h ^= item.charAt(i);
            h *= 0x5bd1e995;
            h ^= h >>> 15;
        }
        h *= 0x27d4eb2d;
        h ^= h >>> 13;
        h *= 0xc2b2ae35;
        h ^= h >>> 16;
        return Math.abs(h);
    }

    public boolean put(String item) {
        boolean mightContain = true;
        for (int seed : hashSeeds) {
            int hash = murmurHash(item, seed);
            int index = hash % bitSetSize;
            if (!bitSet.get(index)) {
                mightContain = false;
                bitSet.set(index);
            }
        }
        insertedCount++;
        return mightContain;
    }

    public boolean mightContain(String item) {
        for (int seed : hashSeeds) {
            int hash = murmurHash(item, seed);
            int index = hash % bitSetSize;
            if (!bitSet.get(index)) {
                return false;
            }
        }
        return true;
    }

    public long getInsertedCount() {
        return insertedCount;
    }

    public int getBitSetSize() {
        return bitSetSize;
    }

    public int getHashFunctionCount() {
        return hashFunctionCount;
    }

    public double getEstimatedFalsePositiveProbability() {
        return Math.pow(
            1 - Math.exp(-(double) hashFunctionCount * insertedCount / bitSetSize),
            hashFunctionCount
        );
    }

    public long getMemoryUsageBytes() {
        return (long) Math.ceil(bitSetSize / 8.0);
    }

    public void reset() {
        bitSet.clear();
        insertedCount = 0;
    }
}
