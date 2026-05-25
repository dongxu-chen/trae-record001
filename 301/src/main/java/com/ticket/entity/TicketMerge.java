package com.ticket.entity;

import com.ticket.enums.MergeStatus;
import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "ticket_merge", indexes = {
        @Index(name = "idx_main_ticket_id", columnList = "main_ticket_id"),
        @Index(name = "idx_merged_ticket_id", columnList = "merged_ticket_id"),
        @Index(name = "idx_status", columnList = "status"),
        @Index(name = "idx_similarity", columnList = "similarity")
})
public class TicketMerge {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "main_ticket_id", nullable = false)
    private Ticket mainTicket;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "merged_ticket_id", nullable = false)
    private Ticket mergedTicket;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private MergeStatus status;

    @Column(nullable = false)
    private Double similarity;

    @Column(length = 1000)
    private String mergeReason;

    @Column(length = 1000)
    private String rejectReason;

    @Column(nullable = false)
    private Boolean autoDetected = false;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "operator_id")
    private User operator;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "created_by")
    private User createdBy;

    private LocalDateTime mergedAt;

    @CreationTimestamp
    @Column(updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;
}
