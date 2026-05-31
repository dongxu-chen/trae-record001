package com.datacheck.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class WebSocketMessage<T> {
    private String type;
    private T payload;
    private LocalDateTime timestamp;

    public static <T> WebSocketMessage<T> of(String type, T payload) {
        return WebSocketMessage.<T>builder()
                .type(type)
                .payload(payload)
                .timestamp(LocalDateTime.now())
                .build();
    }
}
