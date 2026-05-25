package com.filetransfer.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "file_version")
public class FileVersion {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "file_id", nullable = false)
    private Long fileId;

    @Column(name = "file_md5", nullable = false)
    private String fileMd5;

    @Column(name = "version_number", nullable = false)
    private Integer versionNumber;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "username")
    private String username;

    @Column(name = "object_name", nullable = false)
    private String objectName;

    @Column(name = "file_size", nullable = false)
    private Long fileSize;

    @Column(name = "change_description")
    private String changeDescription;

    @Column(name = "is_current")
    private Boolean isCurrent = true;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
