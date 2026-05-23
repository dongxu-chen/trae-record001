package com.meeting.booking.entity;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class ApprovalRecord {
    private Long id;
    private Long bookingId;
    private Long approverId;
    private Integer status;
    private String remark;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
    private User approver;
    private Booking booking;
}
