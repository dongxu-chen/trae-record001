package com.ticket.dto;

import com.ticket.enums.TicketStatus;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class UpdateTicketStatusDTO {

    @NotNull(message = "工单ID不能为空")
    private Long ticketId;

    @NotNull(message = "目标状态不能为空")
    private TicketStatus targetStatus;

    private Long operatorId;

    private String remark;

    private String resolution;
}
