package com.ticket.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "ticket_satisfaction", indexes = {
        @Index(name = "idx_ticket_id", columnList = "ticket_id"),
        @Index(name = "idx_creator_id", columnList = "creator_id"),
        @Index(name = "idx_assignee_id", columnList = "assignee_id"),
        @Index(name = "idx_rating", columnList = "rating"),
        @Index(name = "idx_created_at", columnList = "createdAt")
})
public class TicketSatisfaction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "ticket_id", nullable = false, unique = true)
    private Ticket ticket;

    @Column(nullable = false)
    private Integer rating;

    @Column(length = 500)
    private String comment;

    private Boolean responseTimely;

    private Boolean problemSolved;

    private Boolean attitudeGood;

    @Column(length = 500)
    private String improvement;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "creator_id", nullable = false)
    private User creator;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "assignee_id")
    private User assignee;

    @Column(nullable = false)
    private Boolean submitted = false;

    @Column(nullable = false)
    private Boolean reminded = false;

    private LocalDateTime remindedAt;

    private LocalDateTime submittedAt;

    @CreationTimestamp
    @Column(updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;
}
