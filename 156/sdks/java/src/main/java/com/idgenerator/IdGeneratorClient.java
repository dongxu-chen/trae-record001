package com.idgenerator;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.ObjectMapper;

public class IdGeneratorClient {
    private final String baseURL;
    private final ObjectMapper objectMapper;
    private final int timeout;

    public static class IDResponse {
        @JsonProperty("success")
        public boolean success;
        
        @JsonProperty("id")
        public String id;
        
        @JsonProperty("workerId")
        public Integer workerId;
        
        @JsonProperty("bizType")
        public String bizType;
        
        @JsonProperty("formattedId")
        public String formattedId;
        
        @JsonProperty("shortId")
        public String shortId;
        
        @JsonProperty("humanReadable")
        public String humanReadable;
        
        @JsonProperty("error")
        public String error;
    }

    public static class BatchResponse {
        @JsonProperty("success")
        public boolean success;
        
        @JsonProperty("count")
        public Integer count;
        
        @JsonProperty("ids")
        public List<String> ids;
        
        @JsonProperty("error")
        public String error;
    }

    public static class ParseResponse {
        @JsonProperty("success")
        public boolean success;
        
        @JsonProperty("data")
        public ParseData data;
        
        @JsonProperty("error")
        public String error;
        
        public static class ParseData {
            @JsonProperty("snowflake")
            public SnowflakeInfo snowflake;
            
            @JsonProperty("formatted")
            public FormattedInfo formatted;
        }
        
        public static class SnowflakeInfo {
            @JsonProperty("id")
            public String id;
            
            @JsonProperty("timestamp")
            public Long timestamp;
            
            @JsonProperty("date")
            public String date;
            
            @JsonProperty("workerId")
            public Integer workerId;
            
            @JsonProperty("sequence")
            public Integer sequence;
        }
        
        public static class FormattedInfo {
            @JsonProperty("prefix")
            public String prefix;
            
            @JsonProperty("timestamp")
            public Long timestamp;
            
            @JsonProperty("id")
            public String id;
            
            @JsonProperty("checksum")
            public String checksum;
            
            @JsonProperty("valid")
            public Boolean valid;
        }
    }

    public static class WorkerCapacityResponse {
        @JsonProperty("success")
        public boolean success;
        
        @JsonProperty("data")
        public CapacityData data;
        
        @JsonProperty("error")
        public String error;
        
        public static class CapacityData {
            @JsonProperty("current")
            public Integer current;
            
            @JsonProperty("max")
            public Integer max;
            
            @JsonProperty("remaining")
            public Integer remaining;
        }
    }

    public static class BenchmarkResponse {
        @JsonProperty("success")
        public boolean success;
        
        @JsonProperty("benchmark")
        public BenchmarkData benchmark;
        
        @JsonProperty("error")
        public String error;
        
        public static class BenchmarkData {
            @JsonProperty("type")
            public String type;
            
            @JsonProperty("count")
            public Integer count;
            
            @JsonProperty("elapsedMs")
            public Double elapsedMs;
            
            @JsonProperty("throughputPerSecond")
            public Integer throughputPerSecond;
            
            @JsonProperty("avgNsPerId")
            public Integer avgNsPerId;
        }
    }

    public IdGeneratorClient(String baseURL) {
        this(baseURL, 10000);
    }

    public IdGeneratorClient(String baseURL, int timeout) {
        this.baseURL = baseURL;
        this.timeout = timeout;
        this.objectMapper = new ObjectMapper();
    }

    public IDResponse nextId() throws IOException {
        return nextId(null, false);
    }

    public IDResponse nextId(String bizType, boolean format) throws IOException {
        StringBuilder url = new StringBuilder(baseURL + "/api/id/next");
        boolean hasParams = false;
        
        if (bizType != null && !bizType.isEmpty()) {
            url.append("?bizType=").append(bizType);
            hasParams = true;
        }
        if (format) {
            url.append(hasParams ? "&" : "?").append("format=1");
        }

        return executeGet(url.toString(), IDResponse.class);
    }

    public IDResponse nextSegmentId(String bizType, boolean format, int step) throws IOException {
        StringBuilder url = new StringBuilder(baseURL + "/api/id/segment/next");
        boolean hasParams = false;
        
        if (bizType != null && !bizType.isEmpty()) {
            url.append("?bizType=").append(bizType);
            hasParams = true;
        }
        if (format) {
            url.append(hasParams ? "&" : "?").append("format=1");
            hasParams = true;
        }
        if (step > 0) {
            url.append(hasParams ? "&" : "?").append("step=").append(step);
        }

        return executeGet(url.toString(), IDResponse.class);
    }

    public BatchResponse batch(int count, String bizType, boolean format) throws IOException {
        StringBuilder url = new StringBuilder(baseURL + "/api/id/batch/" + count);
        boolean hasParams = false;
        
        if (bizType != null && !bizType.isEmpty()) {
            url.append("?bizType=").append(bizType);
            hasParams = true;
        }
        if (format) {
            url.append(hasParams ? "&" : "?").append("format=1");
        }

        return executeGet(url.toString(), BatchResponse.class);
    }

    public ParseResponse parse(String id) throws IOException {
        String url = baseURL + "/api/id/parse/" + id;
        return executeGet(url, ParseResponse.class);
    }

    public WorkerCapacityResponse getWorkerCapacity() throws IOException {
        String url = baseURL + "/api/id/worker/capacity";
        return executeGet(url, WorkerCapacityResponse.class);
    }

    public WorkerCapacityResponse expandWorkerCapacity(int targetCount) throws IOException {
        String url = baseURL + "/api/id/worker/expand";
        String payload = "{\"targetCount\":" + targetCount + "}";
        return executePost(url, payload, WorkerCapacityResponse.class);
    }

    public BenchmarkResponse benchmark(int count, String type) throws IOException {
        StringBuilder url = new StringBuilder(baseURL + "/api/id/benchmark/" + count);
        if (type != null && !type.isEmpty()) {
            url.append("?type=").append(type);
        }
        return executeGet(url.toString(), BenchmarkResponse.class);
    }

    private <T> T executeGet(String urlStr, Class<T> responseClass) throws IOException {
        URL url = new URL(urlStr);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");
        conn.setConnectTimeout(timeout);
        conn.setReadTimeout(timeout);

        int status = conn.getResponseCode();
        BufferedReader reader;
        if (status >= 200 && status < 300) {
            reader = new BufferedReader(new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8));
        } else {
            reader = new BufferedReader(new InputStreamReader(conn.getErrorStream(), StandardCharsets.UTF_8));
        }

        StringBuilder response = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            response.append(line);
        }
        reader.close();
        conn.disconnect();

        T result = objectMapper.readValue(response.toString(), responseClass);
        return result;
    }

    private <T> T executePost(String urlStr, String payload, Class<T> responseClass) throws IOException {
        URL url = new URL(urlStr);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setConnectTimeout(timeout);
        conn.setReadTimeout(timeout);
        conn.setDoOutput(true);

        try (OutputStream os = conn.getOutputStream()) {
            byte[] input = payload.getBytes(StandardCharsets.UTF_8);
            os.write(input, 0, input.length);
        }

        int status = conn.getResponseCode();
        BufferedReader reader;
        if (status >= 200 && status < 300) {
            reader = new BufferedReader(new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8));
        } else {
            reader = new BufferedReader(new InputStreamReader(conn.getErrorStream(), StandardCharsets.UTF_8));
        }

        StringBuilder response = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            response.append(line);
        }
        reader.close();
        conn.disconnect();

        T result = objectMapper.readValue(response.toString(), responseClass);
        return result;
    }
}