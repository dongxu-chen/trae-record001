package com.apigateway.mock.entity;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Order {

    private String orderId;
    private Long userId;
    private List<OrderItem> items;
    private Double totalAmount;
    private String status;
    private String address;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
