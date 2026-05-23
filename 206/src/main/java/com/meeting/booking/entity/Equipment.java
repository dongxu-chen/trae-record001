package com.meeting.booking.entity;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class Equipment {
    private Long id;
    private String name;
    private String code;
    private String type;
    private String description;
    private Integer status;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
