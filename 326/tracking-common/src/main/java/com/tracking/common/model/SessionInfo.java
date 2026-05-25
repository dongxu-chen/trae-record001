package com.tracking.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SessionInfo implements Serializable {

    private static final long serialVersionUID = 1L;

    private String sessionId;

    private String anonymousId;

    private String userId;

    private String deviceId;

    private Long startTime;

    private Long endTime;

    private Integer eventCount;

    private Long lastEventTime;

    private String firstPage;

    private String lastPage;

    private String entrySource;

    public boolean isExpired(long currentTime, long timeoutMillis) {
        return lastEventTime != null && (currentTime - lastEventTime) > timeoutMillis;
    }

    public void update(TrackEvent event) {
        this.eventCount = this.eventCount == null ? 1 : this.eventCount + 1;
        this.lastEventTime = event.getTimestamp();
        this.endTime = event.getTimestamp();

        if (event.getUserId() != null && this.userId == null) {
            this.userId = event.getUserId();
        }

        if (event.getUrl() != null) {
            this.lastPage = event.getUrl();
        }

        if (this.firstPage == null && event.getUrl() != null) {
            this.firstPage = event.getUrl();
        }

        if (this.entrySource == null && event.getReferrer() != null) {
            this.entrySource = event.getReferrer();
        }
    }

    public static SessionInfo create(TrackEvent event) {
        return SessionInfo.builder()
                .sessionId(event.getSessionId())
                .anonymousId(event.getAnonymousId())
                .userId(event.getUserId())
                .deviceId(event.getDeviceId())
                .startTime(event.getTimestamp())
                .endTime(event.getTimestamp())
                .eventCount(1)
                .lastEventTime(event.getTimestamp())
                .firstPage(event.getUrl())
                .lastPage(event.getUrl())
                .entrySource(event.getReferrer())
                .build();
    }
}
