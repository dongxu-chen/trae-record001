package com.homestay.vo;

import lombok.Data;
import java.math.BigDecimal;

@Data
public class HouseMapVO {

    private Long id;

    private String title;

    private BigDecimal longitude;

    private BigDecimal latitude;

    private BigDecimal basePrice;

    private String coverImage;

    private BigDecimal rating;

    private Integer reviewCount;
}
