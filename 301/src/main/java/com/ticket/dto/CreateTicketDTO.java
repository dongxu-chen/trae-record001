package com.ticket.dto;

import com.ticket.enums.TicketPriority;
import com.ticket.enums.TicketType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CreateTicketDTO {

    @NotBlank(message = "工单标题不能为空")
    private String title;

    @NotNull(message = "工单类型不能为空")
    private TicketType ticketType;

    @NotNull(message = "优先级不能为空")
    private TicketPriority priority;

    private String description;

    @NotNull(message = "创建人ID不能为空")
    private Long creatorId;

    private Long assigneeId;

    private Long templateId;

    private Long parentTicketId;

    private String customFields;
}
