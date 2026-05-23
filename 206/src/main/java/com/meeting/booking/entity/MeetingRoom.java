package com.meeting.booking.entity;

import lombok.Data;
import java.time.LocalDateTime;
import java.util.List;

@Data
public class MeetingRoom {
    private Long id;
    private String name;
    private String location;
    private Integer capacity;
    private String description;
    private Integer status;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
    private List<Equipment> equipments;
}
