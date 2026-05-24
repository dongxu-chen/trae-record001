package com.homestay.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;
import java.math.BigDecimal;
import java.util.List;

@Data
public class HouseSaveDTO {

    private Long id;

    @NotBlank(message = "房源标题不能为空")
    private String title;

    private String description;

    @NotBlank(message = "省份不能为空")
    private String province;

    @NotBlank(message = "城市不能为空")
    private String city;

    @NotBlank(message = "区县不能为空")
    private String district;

    @NotBlank(message = "详细地址不能为空")
    private String address;

    private BigDecimal longitude;

    private BigDecimal latitude;

    @NotNull(message = "房源类型不能为空")
    private Integer type;

    @NotNull(message = "房间数不能为空")
    private Integer roomCount;

    @NotNull(message = "床位数不能为空")
    private Integer bedCount;

    @NotNull(message = "卫生间数不能为空")
    private Integer bathCount;

    @NotNull(message = "最大入住人数不能为空")
    private Integer maxGuests;

    @NotNull(message = "基础价格不能为空")
    private BigDecimal basePrice;

    private BigDecimal cleaningFee;

    private String coverImage;

    private List<String> images;

    private List<String> facilities;
}
