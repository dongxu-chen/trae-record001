package com.logplatform.model;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.Data;

import java.time.Instant;
import java.util.Map;

@Data
@JsonInclude(JsonInclude.Include.NON_NULL)
public class LogEntry {

    private String id;

    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", timezone = "UTC")
    private Instant timestamp;

    private String appName;

    private String level;

    private String logger;

    private String thread;

    private String message;

    private String stackTrace;

    private String host;

    private String ip;

    private String traceId;

    private Map<String, Object> highlight;

    private Map<String, Object> extra;
}
