package com.datacheck.check;

import com.datacheck.model.DataRecord;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.*;

@Slf4j
@Component
public class StratifiedSampler {

    public enum StratifyStrategy {
        KEY_HASH,
        KEY_RANGE,
        TIME_RANGE,
        RANDOM
    }

    public static class StratifiedResult {
        private final List<List<DataRecord>> strata;
        private final Map<String, Integer> stratumSizes;
        private final StratifyStrategy strategy;

        public StratifiedResult(List<List<DataRecord>> strata,
                                Map<String, Integer> stratumSizes,
                                StratifyStrategy strategy) {
            this.strata = strata;
            this.stratumSizes = stratumSizes;
            this.strategy = strategy;
        }

        public List<List<DataRecord>> getStrata() {
            return strata;
        }

        public Map<String, Integer> getStratumSizes() {
            return stratumSizes;
        }

        public StratifyStrategy getStrategy() {
            return strategy;
        }
    }

    public StratifiedResult stratifyByKeyHash(List<DataRecord> records, int stratumCount) {
        List<List<DataRecord>> strata = new ArrayList<>();
        Map<String, Integer> stratumSizes = new LinkedHashMap<>();

        for (int i = 0; i < stratumCount; i++) {
            strata.add(new ArrayList<>());
        }

        for (DataRecord record : records) {
            if (record.getKey() != null) {
                int stratumIndex = Math.abs(record.getKey().hashCode()) % stratumCount;
                strata.get(stratumIndex).add(record);
            }
        }

        for (int i = 0; i < stratumCount; i++) {
            stratumSizes.put("stratum_" + i, strata.get(i).size());
        }

        return new StratifiedResult(strata, stratumSizes, StratifyStrategy.KEY_HASH);
    }

    public StratifiedResult stratifyByKeyRange(List<DataRecord> records, int stratumCount) {
        List<List<DataRecord>> strata = new ArrayList<>();
        Map<String, Integer> stratumSizes = new LinkedHashMap<>();

        List<DataRecord> sortedRecords = new ArrayList<>(records);
        sortedRecords.sort(Comparator.comparing(DataRecord::getKey, Comparator.nullsLast(String::compareTo)));

        int batchSize = (int) Math.ceil((double) sortedRecords.size() / stratumCount);

        for (int i = 0; i < stratumCount; i++) {
            int start = i * batchSize;
            int end = Math.min(start + batchSize, sortedRecords.size());
            if (start < sortedRecords.size()) {
                strata.add(new ArrayList<>(sortedRecords.subList(start, end)));
            } else {
                strata.add(new ArrayList<>());
            }
        }

        for (int i = 0; i < stratumCount; i++) {
            stratumSizes.put("stratum_" + i, strata.get(i).size());
        }

        return new StratifiedResult(strata, stratumSizes, StratifyStrategy.KEY_RANGE);
    }

    public StratifiedResult stratifyByTimeRange(List<DataRecord> records, int stratumCount) {
        List<List<DataRecord>> strata = new ArrayList<>();
        Map<String, Integer> stratumSizes = new LinkedHashMap<>();

        List<DataRecord> validRecords = new ArrayList<>();
        for (DataRecord record : records) {
            if (record.getTimestamp() > 0) {
                validRecords.add(record);
            }
        }

        validRecords.sort(Comparator.comparingLong(DataRecord::getTimestamp));

        if (validRecords.isEmpty()) {
            for (int i = 0; i < stratumCount; i++) {
                strata.add(new ArrayList<>());
                stratumSizes.put("stratum_" + i, 0);
            }
            return new StratifiedResult(strata, stratumSizes, StratifyStrategy.TIME_RANGE);
        }

        long minTime = validRecords.get(0).getTimestamp();
        long maxTime = validRecords.get(validRecords.size() - 1).getTimestamp();
        long timeRange = maxTime - minTime;

        for (int i = 0; i < stratumCount; i++) {
            strata.add(new ArrayList<>());
        }

        for (DataRecord record : validRecords) {
            if (timeRange > 0) {
                int stratumIndex = (int) (((record.getTimestamp() - minTime) * stratumCount) / (timeRange + 1));
                stratumIndex = Math.min(stratumIndex, stratumCount - 1);
                strata.get(stratumIndex).add(record);
            } else {
                strata.get(0).add(record);
            }
        }

        for (int i = 0; i < stratumCount; i++) {
            stratumSizes.put("stratum_" + i, strata.get(i).size());
        }

        return new StratifiedResult(strata, stratumSizes, StratifyStrategy.TIME_RANGE);
    }

    public StratifiedResult randomSampleStratify(List<DataRecord> records, int stratumCount, double sampleRate) {
        List<List<DataRecord>> strata = new ArrayList<>();
        Map<String, Integer> stratumSizes = new LinkedHashMap<>();
        Random random = new Random();

        for (int i = 0; i < stratumCount; i++) {
            List<DataRecord> stratum = new ArrayList<>();
            for (DataRecord record : records) {
                if (random.nextDouble() < sampleRate) {
                    stratum.add(record);
                }
            }
            strata.add(stratum);
            stratumSizes.put("stratum_" + i, stratum.size());
        }

        return new StratifiedResult(strata, stratumSizes, StratifyStrategy.RANDOM);
    }

    public List<DataRecord> sampleFromStratum(List<DataRecord> stratum, int sampleSize) {
        if (stratum.size() <= sampleSize) {
            return new ArrayList<>(stratum);
        }

        List<DataRecord> shuffled = new ArrayList<>(stratum);
        Collections.shuffle(shuffled);
        return new ArrayList<>(shuffled.subList(0, sampleSize));
    }

    public List<DataRecord> fullCoverageFromStratum(List<DataRecord> stratum) {
        return new ArrayList<>(stratum);
    }
}
