package com.apigateway.mock.entity;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Recommendation {

    private Long productId;
    private String productName;
    private Double score;
    private String reason;
}
