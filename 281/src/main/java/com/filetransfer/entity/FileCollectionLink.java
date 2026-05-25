package com.filetransfer.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "file_collection_link")
public class FileCollectionLink {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "link_code", unique = true, nullable = false)
    private String linkCode;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "title", nullable = false)
    private String title;

    @Column(name = "description")
    private String description;

    @Column(name = "max_file_size")
    private Long maxFileSize;

    @Column(name = "max_files")
    private Integer maxFiles;

    @Column(name = "total_files")
    private Integer totalFiles = 0;

    @Column(name = "total_size")
    private Long totalSize = 0L;

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
