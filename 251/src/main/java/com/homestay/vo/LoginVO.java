package com.homestay.vo;

import lombok.Data;

@Data
public class LoginVO {

    private Long userId;

    private String token;

    private String username;

    private String nickname;

    private String avatar;

    private Integer role;

    private Integer hostStatus;
}
