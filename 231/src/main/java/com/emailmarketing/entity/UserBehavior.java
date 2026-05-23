package com.emailmarketing.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("user_behavior")
public class UserBehavior {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long recipientId;
    private String email;
    private Long taskId;
    private Integer behaviorType;
    private String itemCategory;
    private String itemId;
    private LocalDateTime behaviorTime;
    private Integer stayDuration;
    private Integer clickCount;
    private LocalDateTime createdAt;
}
