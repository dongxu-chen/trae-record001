package com.emailmarketing.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("recipient")
public class Recipient extends BaseEntity {
    private Long groupId;
    private String email;
    private String name;
    private String phone;
    private Integer status;
    private Integer unsubscribed;
}
