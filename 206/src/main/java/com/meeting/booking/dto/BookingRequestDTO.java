package com.meeting.booking.dto;

import lombok.Data;
import javax.validation.constraints.*;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

@Data
public class BookingRequestDTO {
    @NotNull(message = "会议室ID不能为空")
    private Long roomId;

    @NotNull(message = "用户ID不能为空")
    private Long userId;

    @NotBlank(message = "会议主题不能为空")
    @Size(max = 200, message = "会议主题不能超过200字符")
    private String title;

    @NotNull(message = "开始时间不能为空")
    private LocalDateTime startTime;

    @NotNull(message = "结束时间不能为空")
    private LocalDateTime endTime;

    @NotNull(message = "参会人数不能为空")
    @Min(value = 1, message = "参会人数至少1人")
    private Integer attendees;

    @Size(max = 500, message = "会议描述不能超过500字符")
    private String description;

    private Boolean isRecurring = false;

    private String recurringRule;

    private List<Integer> recurringDays;

    private LocalDate recurringEndDate;
}
