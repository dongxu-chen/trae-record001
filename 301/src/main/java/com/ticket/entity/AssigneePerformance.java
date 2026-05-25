package com.ticket.entity;

import com.ticket.enums.TicketPriority;
import com.ticket.enums.TicketType;
import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "assignee_performance", indexes = {
        @Index(name = "idx_assignee_id", columnList = "assignee_id"),
        @Index(name = "idx_ticket_type", columnList = "ticketType"),
        @Index(name = "idx_priority", columnList = "priority")
})
public class AssigneePerformance {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "assignee_id", nullable = false)
    private User assignee;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private TicketType ticketType;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private TicketPriority priority;

    @Column(nullable = false)
    private Long totalTickets = 0L;

    @Column(nullable = false)
    private Long completedTickets = 0L;

    @Column(nullable = false)
    private Long avgResponseTime = 0L;

    @Column(nullable = false)
    private Long avgResolutionTime = 0L;

    @Column(nullable = false)
    private Double avgSatisfaction = 0.0;

    @Column(nullable = false)
    private Long slaMetCount = 0L;

    @Column(nullable = false)
    private Long slaViolatedCount = 0L;

    private LocalDateTime lastTicketAt;

    @CreationTimestamp
    @Column(updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;

    public Double getSlaComplianceRate() {
        long total = slaMetCount + slaViolatedCount;
        if (total == 0) {
            return 100.0;
        }
        return (double) slaMetCount / total * 100;
    }

    public Double getCompletionRate() {
        if (totalTickets == 0) {
            return 0.0;
        }
        return (double) completedTickets / totalTickets * 100;
    }
}
