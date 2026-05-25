package com.filetransfer.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "uploaded_chunk", uniqueConstraints = {
        @UniqueConstraint(columnNames = {"upload_id", "chunk_number"})
})
public class UploadedChunk {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "upload_id", nullable = false)
    private String uploadId;

    @Column(name = "chunk_number", nullable = false)
    private Integer chunkNumber;

    @Column(name = "chunk_size", nullable = false)
    private Long chunkSize;

    @Column(name = "chunk_md5")
    private String chunkMd5;

    @Column(name = "object_name")
    private String objectName;

    @CreationTimestamp
    @Column(name = "uploaded_at", updatable = false)
    private LocalDateTime uploadedAt;
}
