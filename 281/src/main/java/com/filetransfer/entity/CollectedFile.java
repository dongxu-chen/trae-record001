package com.filetransfer.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "collected_file")
public class CollectedFile {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "link_id", nullable = false)
    private Long linkId;

    @Column(name = "link_code", nullable = false)
    private String linkCode;

    @Column(name = "file_name", nullable = false)
    private String fileName;

    @Column(name = "file_size", nullable = false)
    private Long fileSize;

    @Column(name = "content_type")
    private String contentType;

    @Column(name = "object_name")
    private String objectName;

    @Column(name = "uploader_name")
    private String uploaderName;

    @Column(name = "uploader_email")
    private String uploaderEmail;

    @Column(name = "uploader_ip")
    private String uploaderIp;

    @Column(name = "remark")
    private String remark;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
