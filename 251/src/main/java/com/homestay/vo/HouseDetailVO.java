package com.homestay.vo;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Data
public class HouseDetailVO {

    private Long id;

    private Long hostId;

    private String hostName;

    private String hostAvatar;

    private String title;

    private String description;

    private String province;

    private String city;

    private String district;

    private String address;

    private BigDecimal longitude;

    private BigDecimal latitude;

    private Integer type;

    private Integer roomCount;

    private Integer bedCount;

    private Integer bathCount;

    private Integer maxGuests;

    private BigDecimal basePrice;

    private BigDecimal cleaningFee;

    private Integer status;

    private String coverImage;

    private List<String> images;

    private List<String> facilities;

    private BigDecimal rating;

    private Integer reviewCount;

    private LocalDateTime createTime;
}
