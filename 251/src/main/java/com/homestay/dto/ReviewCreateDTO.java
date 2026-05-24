package com.homestay.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class ReviewCreateDTO {

    @NotNull(message = "订单ID不能为空")
    private Long orderId;

    @NotNull(message = "评分不能为空")
    private Integer rating;

    private String content;

    private String images;

    private Integer cleanliness;

    private Integer accuracy;

    private Integer communication;

    private Integer location;

    private Integer checkIn;

    private Integer value;
}
