package com.platform.points.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("user_level_log")
public class UserLevelLog {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;

    private Long beforeLevelId;

    private String beforeLevelCode;

    private String beforeLevelName;

    private Long afterLevelId;

    private String afterLevelCode;

    private String afterLevelName;

    private Integer changeType;

    private String changeReason;

    private Integer triggerPoints;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableLogic
    private Integer deleted;
}
