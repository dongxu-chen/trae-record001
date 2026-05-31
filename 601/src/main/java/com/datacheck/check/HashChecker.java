package com.datacheck.check;

import com.datacheck.model.DataRecord;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Component
public class HashChecker {

    private static final String HASH_ALGORITHM = "SHA-256";

    public String calculateRecordHash(DataRecord record) {
        if (record == null || record.getData() == null) {
            return null;
        }
        try {
            Map<String, Object> data = record.getData();
            List<String> sortedKeys = new ArrayList<>(data.keySet());
            Collections.sort(sortedKeys);

            StringBuilder sb = new StringBuilder();
            for (String key : sortedKeys) {
                Object value = data.get(key);
                sb.append(key).append("=").append(valueToString(value)).append("|");
            }
            return hashString(sb.toString());
        } catch (Exception e) {
            log.error("Failed to calculate record hash", e);
            return null;
        }
    }

    public String calculateBatchHash(List<DataRecord> records) {
        if (records == null || records.isEmpty()) {
            return null;
        }
        try {
            List<String> sortedKeys = records.stream()
                    .map(DataRecord::getKey)
                    .filter(Objects::nonNull)
                    .sorted()
                    .collect(Collectors.toList());

            StringBuilder sb = new StringBuilder();
            for (String key : sortedKeys) {
                DataRecord record = records.stream()
                        .filter(r -> key.equals(r.getKey()))
                        .findFirst()
                        .orElse(null);
                if (record != null) {
                    String recordHash = calculateRecordHash(record);
                    if (recordHash != null) {
                        sb.append(key).append(":").append(recordHash).append("|");
                    }
                }
            }
            return hashString(sb.toString());
        } catch (Exception e) {
            log.error("Failed to calculate batch hash", e);
            return null;
        }
    }

    public Map<String, String> calculatePartitionHashes(List<DataRecord> records, int partitionCount) {
        Map<String, String> partitionHashes = new LinkedHashMap<>();

        if (records == null || records.isEmpty()) {
            return partitionHashes;
        }

        Map<Integer, List<DataRecord>> partitions = new HashMap<>();
        for (DataRecord record : records) {
            if (record.getKey() != null) {
                int partition = Math.abs(record.getKey().hashCode()) % partitionCount;
                partitions.computeIfAbsent(partition, k -> new ArrayList<>()).add(record);
            }
        }

        for (Map.Entry<Integer, List<DataRecord>> entry : partitions.entrySet()) {
            String partitionHash = calculateBatchHash(entry.getValue());
            partitionHashes.put("partition_" + entry.getKey(), partitionHash);
        }

        return partitionHashes;
    }

    public boolean compareRecordHash(DataRecord sourceRecord, DataRecord targetRecord) {
        String sourceHash = calculateRecordHash(sourceRecord);
        String targetHash = calculateRecordHash(targetRecord);
        return sourceHash != null && sourceHash.equals(targetHash);
    }

    public boolean compareBatchHash(List<DataRecord> sourceRecords, List<DataRecord> targetRecords) {
        String sourceHash = calculateBatchHash(sourceRecords);
        String targetHash = calculateBatchHash(targetRecords);
        return sourceHash != null && sourceHash.equals(targetHash);
    }

    public List<String> findDifferentPartitions(
            Map<String, String> sourceHashes,
            Map<String, String> targetHashes) {
        List<String> differentPartitions = new ArrayList<>();

        Set<String> allPartitions = new HashSet<>();
        allPartitions.addAll(sourceHashes.keySet());
        allPartitions.addAll(targetHashes.keySet());

        for (String partition : allPartitions) {
            String sourceHash = sourceHashes.get(partition);
            String targetHash = targetHashes.get(partition);
            if (sourceHash == null || targetHash == null || !sourceHash.equals(targetHash)) {
                differentPartitions.add(partition);
            }
        }

        return differentPartitions;
    }

    private String valueToString(Object value) {
        if (value == null) {
            return "null";
        }
        if (value instanceof Number || value instanceof String || value instanceof Boolean) {
            return value.toString();
        }
        if (value instanceof Date) {
            return String.valueOf(((Date) value).getTime());
        }
        if (value instanceof Map) {
            Map<?, ?> map = (Map<?, ?>) value;
            List<String> keys = new ArrayList<>();
            for (Object key : map.keySet()) {
                keys.add(key.toString());
            }
            Collections.sort(keys);
            StringBuilder sb = new StringBuilder("{");
            for (String key : keys) {
                sb.append(key).append(":").append(valueToString(map.get(key))).append(",");
            }
            sb.append("}");
            return sb.toString();
        }
        if (value instanceof Collection) {
            Collection<?> col = (Collection<?>) value;
            StringBuilder sb = new StringBuilder("[");
            for (Object item : col) {
                sb.append(valueToString(item)).append(",");
            }
            sb.append("]");
            return sb.toString();
        }
        return value.toString();
    }

    private String hashString(String input) {
        try {
            MessageDigest digest = MessageDigest.getInstance(HASH_ALGORITHM);
            byte[] hashBytes = digest.digest(input.getBytes(StandardCharsets.UTF_8));
            return bytesToHex(hashBytes);
        } catch (NoSuchAlgorithmException e) {
            log.error("Hash algorithm not found: {}", HASH_ALGORITHM, e);
            return null;
        }
    }

    private String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}
