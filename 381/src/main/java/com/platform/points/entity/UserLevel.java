package com.platform.points.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("user_level")
public class UserLevel {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;

    private Long currentLevelId;

    private String currentLevelCode;

    private String currentLevelName;

    private Integer currentLevelOrder;

    private Integer totalPoints;

    private Integer levelPoints;

    private Integer nextLevelPoints;

    private String nextLevelName;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime levelUpTime;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
