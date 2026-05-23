package com.shortlink.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "access_log", indexes = {
    @Index(name = "idx_short_code", columnList = "shortCode"),
    @Index(name = "idx_access_time", columnList = "accessTime"),
    @Index(name = "idx_ip", columnList = "ip")
})
public class AccessLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 16)
    private String shortCode;

    @Column(length = 64)
    private String ip;

    @Column(length = 512)
    private String userAgent;

    @Column(length = 64)
    private String deviceType;

    @Column(length = 64)
    private String browser;

    @Column(length = 64)
    private String os;

    @Column(length = 128)
    private String country;

    @Column(length = 128)
    private String province;

    @Column(length = 128)
    private String city;

    @Column(length = 255)
    private String referer;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime accessTime;
}
