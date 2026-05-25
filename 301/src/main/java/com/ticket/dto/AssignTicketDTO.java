package com.ticket.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class AssignTicketDTO {

    @NotNull(message = "工单ID不能为空")
    private Long ticketId;

    @NotNull(message = "处理人ID不能为空")
    private Long assigneeId;

    private Long operatorId;

    private String remark;

    private Boolean autoAssign = false;
}
