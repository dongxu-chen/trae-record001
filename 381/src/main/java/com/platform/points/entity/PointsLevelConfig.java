package com.platform.points.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("points_level_config")
public class PointsLevelConfig {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String levelName;

    private String levelCode;

    private Integer levelOrder;

    private Integer minPoints;

    private Integer maxPoints;

    private String levelIcon;

    private String levelPrivileges;

    private Double discountRate;

    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
