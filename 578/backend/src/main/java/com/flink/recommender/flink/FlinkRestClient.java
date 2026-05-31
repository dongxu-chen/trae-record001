package com.flink.recommender.flink;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.flink.recommender.flink.dto.JobDetails;
import com.flink.recommender.flink.dto.JobOverview;
import com.flink.recommender.flink.dto.VertexDetails;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.Optional;

@Component
public class FlinkRestClient {

    private static final Logger logger = LoggerFactory.getLogger(FlinkRestClient.class);

    private final OkHttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final String baseUrl;

    public FlinkRestClient(
            OkHttpClient httpClient,
            ObjectMapper objectMapper,
            @Value("${flink.rest.base-url:http://localhost:8081}") String baseUrl) {
        this.httpClient = httpClient;
        this.objectMapper = objectMapper;
        this.baseUrl = baseUrl;
    }

    public Optional<JobOverview> getJobOverview() {
        String url = baseUrl + "/jobs/overview";
        return executeGetRequest(url, JobOverview.class);
    }

    public Optional<JobDetails> getJobDetails(String jobId) {
        String url = baseUrl + "/jobs/" + jobId;
        return executeGetRequest(url, JobDetails.class);
    }

    public Optional<VertexDetails> getVertexDetails(String jobId, String vertexId) {
        String url = baseUrl + "/jobs/" + jobId + "/vertices/" + vertexId + "/subtasks/metrics";
        return executeGetRequest(url, VertexDetails.class);
    }

    public boolean isFlinkAvailable() {
        try {
            String url = baseUrl + "/overview";
            Request request = new Request.Builder().url(url).build();
            try (Response response = httpClient.newCall(request).execute()) {
                return response.isSuccessful();
            }
        } catch (Exception e) {
            logger.warn("Flink cluster is not available: {}", e.getMessage());
            return false;
        }
    }

    private <T> Optional<T> executeGetRequest(String url, Class<T> responseType) {
        logger.debug("Executing GET request to: {}", url);

        Request request = new Request.Builder()
                .url(url)
                .get()
                .build();

        try (Response response = httpClient.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                logger.warn("Request failed with code: {}", response.code());
                return Optional.empty();
            }

            String responseBody = response.body() != null ? response.body().string() : "";
            logger.trace("Response body: {}", responseBody);

            T result = objectMapper.readValue(responseBody, responseType);
            return Optional.of(result);

        } catch (IOException e) {
            logger.error("Error executing request to {}: {}", url, e.getMessage(), e);
            return Optional.empty();
        }
    }
}
