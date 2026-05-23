package com.meeting.booking.entity;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class User {
    private Long id;
    private String username;
    private String name;
    private String email;
    private String phone;
    private String department;
    private Integer status;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
