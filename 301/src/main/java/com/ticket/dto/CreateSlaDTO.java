package com.ticket.dto;

import com.ticket.enums.TicketPriority;
import com.ticket.enums.TicketType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CreateSlaDTO {

    @NotBlank(message = "SLA名称不能为空")
    private String name;

    private String description;

    @NotNull(message = "工单类型不能为空")
    private TicketType ticketType;

    @NotNull(message = "优先级不能为空")
    private TicketPriority priority;

    @NotNull(message = "响应时间不能为空")
    private Integer responseTime;

    @NotNull(message = "解决时间不能为空")
    private Integer resolutionTime;

    private Integer warningThreshold;

    private Boolean enabled = true;
}
