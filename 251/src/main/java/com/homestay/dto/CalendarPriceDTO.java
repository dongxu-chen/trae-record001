package com.homestay.dto;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

@Data
public class CalendarPriceDTO {

    private Long houseId;

    private LocalDate startDate;

    private LocalDate endDate;

    private List<LocalDate> dates;

    private BigDecimal price;

    private Integer stock;

    private Integer status;
}
