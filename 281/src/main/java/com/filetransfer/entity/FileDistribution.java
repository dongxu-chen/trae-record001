package com.filetransfer.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "file_distribution")
public class FileDistribution {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "distribution_id", unique = true, nullable = false)
    private String distributionId;

    @Column(name = "source_user_id", nullable = false)
    private Long sourceUserId;

    @Column(name = "source_username")
    private String sourceUsername;

    @Column(name = "title")
    private String title;

    @Column(name = "message")
    private String message;

    @Column(name = "total_files")
    private Integer totalFiles = 0;

    @Column(name = "total_size")
    private Long totalSize = 0L;

    @Column(name = "total_recipients")
    private Integer totalRecipients = 0;

    @Column(name = "view_count")
    private Integer viewCount = 0;

    @Column(name = "download_count")
    private Integer downloadCount = 0;

    @Column(name = "expired_at")
    private LocalDateTime expiredAt;

    @Column(name = "is_active")
    private Boolean isActive = true;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
