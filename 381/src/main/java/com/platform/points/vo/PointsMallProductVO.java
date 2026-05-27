package com.platform.points.vo;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class PointsMallProductVO {

    private Long id;

    private String productName;

    private String productImage;

    private String productDesc;

    private Integer pointsRequired;

    private Integer stock;

    private Integer status;

    private LocalDateTime createTime;
}
