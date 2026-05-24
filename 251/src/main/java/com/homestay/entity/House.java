package com.homestay.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("house")
public class House {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long hostId;

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

    private BigDecimal rating;

    private Integer reviewCount;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
