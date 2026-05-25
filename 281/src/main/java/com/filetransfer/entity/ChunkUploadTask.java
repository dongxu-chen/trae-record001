package com.filetransfer.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "chunk_upload_task")
public class ChunkUploadTask {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "upload_id", unique = true, nullable = false)
    private String uploadId;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "file_name", nullable = false)
    private String fileName;

    @Column(name = "file_size", nullable = false)
    private Long fileSize;

    @Column(name = "file_md5")
    private String fileMd5;

    @Column(name = "chunk_size", nullable = false)
    private Long chunkSize;

    @Column(name = "total_chunks", nullable = false)
    private Integer totalChunks;

    @Column(name = "uploaded_chunks")
    private Integer uploadedChunks = 0;

    @Column(name = "content_type")
    private String contentType;

    @Column(name = "status")
    private String status = "UPLOADING";

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @Column(name = "expired_at")
    private LocalDateTime expiredAt;
}
