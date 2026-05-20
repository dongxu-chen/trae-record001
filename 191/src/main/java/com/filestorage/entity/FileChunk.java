package com.filestorage.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "file_chunk", indexes = {
        @Index(name = "idx_upload_id", columnList = "upload_id"),
        @Index(name = "idx_tenant_md5", columnList = "tenant_id, file_md5"),
        @Index(name = "idx_expired_at", columnList = "expired_at")
})
public class FileChunk {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "tenant_id", nullable = false)
    private Long tenantId;

    @Column(name = "upload_id", nullable = false, length = 64)
    private String uploadId;

    @Column(name = "file_md5", nullable = false, length = 32)
    private String fileMd5;

    @Column(name = "chunk_number", nullable = false)
    private Integer chunkNumber;

    @Column(name = "chunk_size", nullable = false)
    private Long chunkSize;

    @Column(name = "total_chunks", nullable = false)
    private Integer totalChunks;

    @Column(name = "total_size", nullable = false)
    private Long totalSize;

    @Column(name = "file_name", nullable = false, length = 255)
    private String fileName;

    @Column(name = "upload_user", length = 64)
    private String uploadUser;

    @Column(name = "status")
    private Integer status = 0;

    @Column(name = "expired_at", nullable = false)
    private LocalDateTime expiredAt;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
