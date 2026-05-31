package com.drill.platform.jmeter;

import com.drill.platform.model.DrillResult;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.*;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Component
public class JMeterResultParser {

    @Value("${drill.jmeter.result-dir:./drill-results}")
    private String resultDir;

    public DrillResult parseCsvResult(String testId) {
        String csvPath = resultDir + File.separator + testId + File.separator + "results.csv";
        File csvFile = new File(csvPath);

        if (!csvFile.exists()) {
            log.warn("JMeter result file not found: {}", csvPath);
            return null;
        }

        List<JMeterSample> samples = new ArrayList<>();

        try (BufferedReader reader = new BufferedReader(new FileReader(csvFile))) {
            String headerLine = reader.readLine();
            if (headerLine == null) return null;

            String[] headers = headerLine.split(",");
            Map<String, Integer> headerIndex = new HashMap<>();
            for (int i = 0; i < headers.length; i++) {
                headerIndex.put(headers[i].trim(), i);
            }

            String line;
            while ((line = reader.readLine()) != null) {
                String[] fields = line.split(",", -1);
                JMeterSample sample = new JMeterSample();
                if (headerIndex.containsKey("timeStamp"))
                    sample.setTimestamp(getLong(fields, headerIndex.get("timeStamp")));
                if (headerIndex.containsKey("elapsed"))
                    sample.setElapsed(getLong(fields, headerIndex.get("elapsed")));
                if (headerIndex.containsKey("success"))
                    sample.setSuccess("true".equalsIgnoreCase(getString(fields, headerIndex.get("success"))));
                if (headerIndex.containsKey("responseCode"))
                    sample.setResponseCode(getString(fields, headerIndex.get("responseCode")));
                if (headerIndex.containsKey("responseMessage"))
                    sample.setResponseMessage(getString(fields, headerIndex.get("responseMessage")));
                if (headerIndex.containsKey("grpThreads"))
                    sample.setGroupThreads(getInt(fields, headerIndex.get("grpThreads")));
                samples.add(sample);
            }
        } catch (IOException e) {
            log.error("Failed to parse JMeter CSV result", e);
            return null;
        }

        return buildDrillResult(samples);
    }

    private DrillResult buildDrillResult(List<JMeterSample> samples) {
        DrillResult result = new DrillResult();

        int total = samples.size();
        long successCount = samples.stream().filter(s -> s.isSuccess()).count();
        long failCount = total - successCount;
        long blockedCount = samples.stream()
                .filter(s -> !s.isSuccess() && ("429".equals(s.getResponseCode()) || "503".equals(s.getResponseCode())))
                .count();

        List<Long> responseTimes = new ArrayList<>();
        for (JMeterSample sample : samples) {
            responseTimes.add(sample.getElapsed());
        }
        Collections.sort(responseTimes);

        result.setTotalRequests(total);
        result.setSuccessRequests((int) successCount);
        result.setFailedRequests((int) failCount);
        result.setBlockedRequests((int) blockedCount);
        result.setDegradedRequests(0);

        if (!responseTimes.isEmpty()) {
            result.setAvgResponseTimeMs((long) responseTimes.stream().mapToLong(Long::longValue).average().orElse(0));
            result.setMinResponseTimeMs(responseTimes.get(0));
            result.setMaxResponseTimeMs(responseTimes.get(responseTimes.size() - 1));
            result.setP50ResponseTimeMs(percentile(responseTimes, 0.50));
            result.setP90ResponseTimeMs(percentile(responseTimes, 0.90));
            result.setP95ResponseTimeMs(percentile(responseTimes, 0.95));
            result.setP99ResponseTimeMs(percentile(responseTimes, 0.99));
        }

        if (total > 0) {
            result.setBlockRate(blockedCount * 100.0 / total);
            result.setErrorRate(failCount * 100.0 / total);
        }

        result.setActualQps(total > 0 && !samples.isEmpty() ?
                total * 1000.0 / (samples.get(samples.size() - 1).getTimestamp() - samples.get(0).getTimestamp()) : 0);
        result.setThroughput(successCount * 1000.0 / (samples.isEmpty() ? 1 :
                samples.get(samples.size() - 1).getTimestamp() - samples.get(0).getTimestamp()));

        return result;
    }

    private long percentile(List<Long> sorted, double pct) {
        int index = (int) Math.ceil(pct * sorted.size()) - 1;
        return sorted.get(Math.max(0, index));
    }

    private long getLong(String[] fields, int index) {
        try {
            return index < fields.length ? Long.parseLong(fields[index].trim()) : 0;
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private int getInt(String[] fields, int index) {
        try {
            return index < fields.length ? Integer.parseInt(fields[index].trim()) : 0;
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private String getString(String[] fields, int index) {
        return index < fields.length ? fields[index].trim() : "";
    }

    @Data
    public static class JMeterSample {
        private long timestamp;
        private long elapsed;
        private boolean success;
        private String responseCode;
        private String responseMessage;
        private int groupThreads;
    }
}
