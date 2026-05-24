package com.homestay.dto;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

@Data
public class HouseSearchDTO {

    private String keyword;

    private String province;

    private String city;

    private String district;

    private LocalDate checkInDate;

    private LocalDate checkOutDate;

    private BigDecimal minPrice;

    private BigDecimal maxPrice;

    private Integer roomCount;

    private Integer bedCount;

    private Integer bathCount;

    private Integer minGuests;

    private List<String> facilities;

    private BigDecimal minRating;

    private String sortBy;

    private String sortOrder;

    private BigDecimal userLatitude;

    private BigDecimal userLongitude;

    private Integer pageNum = 1;

    private Integer pageSize = 10;
}
