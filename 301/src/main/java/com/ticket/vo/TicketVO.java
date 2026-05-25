package com.ticket.vo;

import com.ticket.enums.SlaStatus;
import com.ticket.enums.TicketPriority;
import com.ticket.enums.TicketStatus;
import com.ticket.enums.TicketType;
import lombok.Data;

import java.time.LocalDateTime;

@Data
public class TicketVO {

    private Long id;

    private String ticketNo;

    private String title;

    private TicketType ticketType;

    private TicketPriority priority;

    private TicketStatus status;

    private String description;

    private Long creatorId;

    private String creatorName;

    private Long assigneeId;

    private String assigneeName;

    private SlaStatus slaStatus;

    private LocalDateTime responseDeadline;

    private LocalDateTime resolutionDeadline;

    private LocalDateTime respondedAt;

    private LocalDateTime resolvedAt;

    private String resolution;

    private String customFields;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
