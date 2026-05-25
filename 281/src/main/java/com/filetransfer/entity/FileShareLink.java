package com.filetransfer.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "file_share_link")
public class FileShareLink {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "share_code", unique = true, nullable = false)
    private String shareCode;

    @Column(name = "file_id", nullable = false)
    private Long fileId;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "title")
    private String title;

    @Column(name = "enable_watermark")
    private Boolean enableWatermark = true;

    @Column(name = "watermark_text")
    private String watermarkText;

    @Column(name = "enable_download")
    private Boolean enableDownload = true;

    @Column(name = "enable_preview")
    private Boolean enablePreview = true;

    @Column(name = "max_views")
    private Integer maxViews;

    @Column(name = "view_count")
    private Integer viewCount = 0;

    @Column(name = "password")
    private String password;

    @Column(name = "is_password_protected")
    private Boolean isPasswordProtected = false;

    @Column(name = "is_active")
    private Boolean isActive = true;

    @Column(name = "expired_at")
    private LocalDateTime expiredAt;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
