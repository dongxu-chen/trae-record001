package com.ticket.dto;

import com.ticket.enums.RelationType;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CreateRelationDTO {

    @NotNull(message = "源工单ID不能为空")
    private Long sourceTicketId;

    @NotNull(message = "目标工单ID不能为空")
    private Long targetTicketId;

    @NotNull(message = "关联类型不能为空")
    private RelationType relationType;

    private Long createdById;
}
