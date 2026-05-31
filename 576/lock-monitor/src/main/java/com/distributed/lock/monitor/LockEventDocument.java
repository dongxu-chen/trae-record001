package com.distributed.lock.monitor;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.elasticsearch.annotations.Document;
import org.springframework.data.elasticsearch.annotations.Field;
import org.springframework.data.elasticsearch.annotations.FieldType;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(indexName = "lock-events")
public class LockEventDocument {

    @Id
    private String eventId;

    @Field(type = FieldType.Keyword)
    private String lockKey;

    @Field(type = FieldType.Keyword)
    private String lockType;

    @Field(type = FieldType.Keyword)
    private String eventType;

    @Field(type = FieldType.Keyword)
    private String threadId;

    @Field(type = FieldType.Text)
    private String threadName;

    @Field(type = FieldType.Keyword)
    private String hostName;

    @Field(type = FieldType.Keyword)
    private String applicationName;

    @Field(type = FieldType.Long)
    private long timestamp;

    @Field(type = FieldType.Long)
    private Long waitTimeMs;

    @Field(type = FieldType.Long)
    private Long holdTimeMs;

    @Field(type = FieldType.Long)
    private Long leaseTimeMs;

    @Field(type = FieldType.Boolean)
    private boolean success;

    @Field(type = FieldType.Text)
    private String errorMessage;

    @Field(type = FieldType.Keyword)
    private String ownerId;
}