package com.emailmarketing.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;
import java.time.LocalDateTime;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("email_task")
public class EmailTask extends BaseEntity {
    private String name;
    private Long templateId;
    private Long groupId;
    private Integer taskType;
    private LocalDateTime scheduleTime;
    private Integer status;
    private Integer totalCount;
    private Integer sentCount;
    private Integer successCount;
    private Integer failCount;
    private Integer unsubscribeCount;
}
