package com.meeting.booking.entity;

import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
public class Booking {
    private Long id;
    private Long roomId;
    private Long userId;
    private String title;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private Integer attendees;
    private String description;
    private Integer status;
    private Integer needApproval;
    private Integer approvalStatus;
    private Integer isRecurring;
    private String recurringRule;
    private String recurringDays;
    private LocalDate recurringEndDate;
    private Long recurringParentId;
    private Integer version;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
    private MeetingRoom room;
    private User user;
}
