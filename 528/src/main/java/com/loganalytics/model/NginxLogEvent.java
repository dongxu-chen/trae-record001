package com.loganalytics.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NginxLogEvent implements Serializable {
    private String remoteAddr;
    private String remoteUser;
    private long timestamp;
    private String request;
    private String method;
    private String uri;
    private String path;
    private int status;
    private long bodyBytesSent;
    private String httpReferer;
    private String httpUserAgent;
    private double requestTime;
    private double upstreamResponseTime;
    private String upstreamStatus;
    private String host;
}
