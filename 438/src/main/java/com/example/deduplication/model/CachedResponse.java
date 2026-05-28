package com.example.deduplication.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.http.HttpStatus;

import java.io.Serializable;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CachedResponse implements Serializable {

    private static final long serialVersionUID = 1L;

    private int status;
    private Map<String, String> headers;
    private String body;
    private long timestamp;
    private String requestHash;

    public boolean isExpired(long windowSeconds) {
        return (System.currentTimeMillis() - timestamp) > (windowSeconds * 1000);
    }

    public HttpStatus getHttpStatus() {
        return HttpStatus.valueOf(status);
    }
}
