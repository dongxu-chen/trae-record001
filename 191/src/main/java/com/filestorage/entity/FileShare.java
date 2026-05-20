package com.filestorage.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "file_share", indexes = {
        @Index(name = "idx_share_code", columnList = "share_code"),
        @Index(name = "idx_tenant_id", columnList = "tenant_id"),
        @Index(name = "idx_expire_at", columnList = "expire_at")
})
public class FileShare {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "tenant_id", nullable = false)
    private Long tenantId;

    @Column(name = "file_id", nullable = false)
    private Long fileId;

    @Column(name = "share_code", nullable = false, unique = true, length = 32)
    private String shareCode;

    @Column(name = "extract_code", length = 16)
    private String extractCode;

    @Column(name = "share_user", length = 64)
    private String shareUser;

    @Column(name = "view_count")
    private Integer viewCount = 0;

    @Column(name = "download_count")
    private Integer downloadCount = 0;

    @Column(name = "expire_at")
    private LocalDateTime expireAt;

    @Column(name = "status")
    private Integer status = 1;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
