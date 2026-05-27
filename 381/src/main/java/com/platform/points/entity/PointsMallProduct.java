package com.platform.points.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("points_mall_product")
public class PointsMallProduct {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String productName;

    private String productImage;

    private String productDesc;

    private Integer pointsRequired;

    private Integer stock;

    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
