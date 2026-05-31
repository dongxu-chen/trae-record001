package com.benchmark.generator;

import com.benchmark.dto.TestConfig;

public class IdGeneratorFactory {

    public static IdGenerator createGenerator(String algorithm, TestConfig config) {
        return switch (algorithm.toUpperCase()) {
            case "SNOWFLAKE" -> {
                TestConfig.SnowflakeConfig snowflakeConfig = config.getSnowflakeConfig();
                if (snowflakeConfig == null) {
                    snowflakeConfig = new TestConfig.SnowflakeConfig();
                }

                SnowflakeIdGenerator.ClockSimulator.Mode clockMode = parseClockMode(snowflakeConfig.getClockMode());
                long clockOffsetMs = snowflakeConfig.getClockOffsetMs();
                double clockBackProbability = snowflakeConfig.getClockBackProbability();

                yield new SnowflakeIdGenerator(
                    snowflakeConfig.getWorkerId(),
                    snowflakeConfig.getDatacenterId(),
                    clockMode,
                    clockOffsetMs,
                    clockBackProbability
                );
            }
            case "SEGMENT" -> {
                TestConfig.SegmentConfig segmentConfig = config.getSegmentConfig();
                if (segmentConfig == null) {
                    segmentConfig = new TestConfig.SegmentConfig();
                }
                yield new SegmentIdGenerator(segmentConfig.getSegmentSize());
            }
            case "RANDOM" -> new RandomIdGenerator();
            default -> throw new IllegalArgumentException("Unknown algorithm: " + algorithm);
        };
    }

    private static SnowflakeIdGenerator.ClockSimulator.Mode parseClockMode(String mode) {
        if (mode == null) {
            return SnowflakeIdGenerator.ClockSimulator.Mode.NORMAL;
        }
        try {
            return SnowflakeIdGenerator.ClockSimulator.Mode.valueOf(mode.toUpperCase());
        } catch (IllegalArgumentException e) {
            return SnowflakeIdGenerator.ClockSimulator.Mode.NORMAL;
        }
    }
}
