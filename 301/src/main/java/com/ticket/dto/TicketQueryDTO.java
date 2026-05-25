package com.ticket.dto;

import com.ticket.enums.TicketPriority;
import com.ticket.enums.TicketStatus;
import com.ticket.enums.TicketType;
import lombok.Data;

@Data
public class TicketQueryDTO {

    private String title;

    private TicketStatus status;

    private TicketPriority priority;

    private TicketType ticketType;

    private Long assigneeId;

    private Long creatorId;

    private Integer pageNum = 1;

    private Integer pageSize = 10;

    private String sortBy = "createdAt";

    private String sortOrder = "desc";
}
