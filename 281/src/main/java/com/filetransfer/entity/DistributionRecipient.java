package com.filetransfer.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "distribution_recipient", uniqueConstraints = {
        @UniqueConstraint(columnNames = {"distribution_id", "recipient_type", "recipient_identifier"})
})
public class DistributionRecipient {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "distribution_id", nullable = false)
    private String distributionId;

    @Column(name = "recipient_type", nullable = false)
    private String recipientType;

    @Column(name = "recipient_identifier", nullable = false)
    private String recipientIdentifier;

    @Column(name = "recipient_name")
    private String recipientName;

    @Column(name = "has_viewed")
    private Boolean hasViewed = false;

    @Column(name = "has_downloaded")
    private Boolean hasDownloaded = false;

    @Column(name = "viewed_at")
    private LocalDateTime viewedAt;

    @Column(name = "downloaded_at")
    private LocalDateTime downloadedAt;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
