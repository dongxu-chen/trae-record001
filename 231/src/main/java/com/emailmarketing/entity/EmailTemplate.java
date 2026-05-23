package com.emailmarketing.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("email_template")
public class EmailTemplate extends BaseEntity {
    private String name;
    private String subject;
    private String content;
    private Integer status;
}
