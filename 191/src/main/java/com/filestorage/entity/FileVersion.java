package com.filestorage.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "file_version", indexes = {
        @Index(name = "idx_file_id", columnList = "file_id"),
        @Index(name = "idx_tenant_id", columnList = "tenant_id"),
        @Index(name = "idx_version", columnList = "file_id, version_number")
})
public class FileVersion {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "tenant_id", nullable = false)
    private Long tenantId;

    @Column(name = "file_id", nullable = false)
    private Long fileId;

    @Column(name = "version_number", nullable = false)
    private Integer versionNumber;

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

    @Column(name = "change_description", length = 500)
    private String changeDescription;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
