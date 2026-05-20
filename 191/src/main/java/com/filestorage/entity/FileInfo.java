package com.filestorage.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "file_info", indexes = {
        @Index(name = "idx_tenant_id", columnList = "tenant_id"),
        @Index(name = "idx_file_md5", columnList = "file_md5"),
        @Index(name = "idx_is_deleted", columnList = "is_deleted")
})
public class FileInfo {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "tenant_id", nullable = false)
    private Long tenantId;

    @Column(name = "file_md5", nullable = false, length = 32)
    private String fileMd5;

    @Column(name = "file_name", nullable = false, length = 255)
    private String fileName;

    @Column(name = "file_path", nullable = false, length = 512)
    private String filePath;

    @Column(name = "file_size", nullable = false)
    private Long fileSize;

    @Column(name = "file_type", length = 64)
    private String fileType;

    @Column(name = "file_extension", length = 16)
    private String fileExtension;

    @Column(name = "upload_user", length = 64)
    private String uploadUser;

    @Column(name = "is_deleted")
    private Integer isDeleted = 0;

    @Column(name = "has_thumbnail")
    private Integer hasThumbnail = 0;

    @Column(name = "thumbnail_path", length = 512)
    private String thumbnailPath;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
