package com.homestay.dto;

import lombok.Data;
import java.math.BigDecimal;

@Data
public class MapHouseDTO {

    private BigDecimal minLat;

    private BigDecimal maxLat;

    private BigDecimal minLng;

    private BigDecimal maxLng;

    private Integer zoom;
}
