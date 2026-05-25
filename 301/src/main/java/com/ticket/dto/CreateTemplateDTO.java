package com.ticket.dto;

import com.ticket.enums.TicketPriority;
import com.ticket.enums.TicketType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CreateTemplateDTO {

    @NotBlank(message = "模板名称不能为空")
    private String name;

    private String description;

    @NotNull(message = "工单类型不能为空")
    private TicketType ticketType;

    @NotNull(message = "默认优先级不能为空")
    private TicketPriority defaultPriority;

    private String defaultDescription;

    private Long defaultAssigneeId;

    private Long slaId;

    private String customFields;

    private Boolean enabled = true;
}
