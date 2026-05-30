package com.distid.tracking;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class IdLifecycleEvent {

    public enum Stage {
        GENERATED,
        ASSIGNED,
        CONSUMED,
        EXPIRED,
        ARCHIVED
    }

    private final long id;
    private final String readableId;
    private final Stage stage;
    private final String bizTag;
    private final String mode;
    private final long timestamp;
    private final String traceId;
    private final String spanId;
    private final String dcCode;
    private final String podName;
    private final String detail;

    public String toRedisValue() {
        return stage.name() + "|" + timestamp + "|" + bizTag + "|" + mode + "|"
                + (traceId != null ? traceId : "") + "|"
                + (spanId != null ? spanId : "") + "|"
                + (dcCode != null ? dcCode : "") + "|"
                + (podName != null ? podName : "") + "|"
                + (detail != null ? detail : "");
    }

    public static IdLifecycleEvent fromRedisValue(long id, String readableId, String value) {
        String[] parts = value.split("\\|", -1);
        return IdLifecycleEvent.builder()
                .id(id)
                .readableId(readableId)
                .stage(Stage.valueOf(parts[0]))
                .timestamp(parts.length > 1 ? Long.parseLong(parts[1]) : 0)
                .bizTag(parts.length > 2 ? parts[2] : "")
                .mode(parts.length > 3 ? parts[3] : "")
                .traceId(parts.length > 4 ? parts[4] : "")
                .spanId(parts.length > 5 ? parts[5] : "")
                .dcCode(parts.length > 6 ? parts[6] : "")
                .podName(parts.length > 7 ? parts[7] : "")
                .detail(parts.length > 8 ? parts[8] : "")
                .build();
    }
}
