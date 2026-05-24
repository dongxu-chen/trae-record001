package com.homestay.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("house_facility")
public class HouseFacility {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long houseId;

    private String facilityName;

    private String facilityCode;

    private String icon;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
