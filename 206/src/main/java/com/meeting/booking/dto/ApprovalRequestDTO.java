package com.meeting.booking.dto;

import lombok.Data;
import javax.validation.constraints.NotNull;

@Data
public class ApprovalRequestDTO {
    @NotNull(message = "审批记录ID不能为空")
    private Long approvalId;

    @NotNull(message = "审批人ID不能为空")
    private Long approverId;

    @NotNull(message = "审批状态不能为空")
    private Integer status;

    private String remark;
}
