package com.econtract.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.econtract.common.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("sys_user")
public class User extends BaseEntity {

    private static final long serialVersionUID = 1L;

    private String username;

    private String password;

    private String realName;

    private String phone;

    private String idCard;

    private String email;

    private String faceImage;

    private Integer status;

    private Integer identityVerified;
}
