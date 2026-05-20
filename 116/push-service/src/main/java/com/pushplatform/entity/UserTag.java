package com.pushplatform.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.pushplatform.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("user_tag")
public class UserTag extends BaseEntity {

    private String userId;

    private String tagCode;

    private String tagName;

    private String tagValue;
}
