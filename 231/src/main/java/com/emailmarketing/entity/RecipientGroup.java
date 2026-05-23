package com.emailmarketing.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("recipient_group")
public class RecipientGroup extends BaseEntity {
    private String name;
    private String description;
    private Integer recipientCount;
}
