package com.shortlink.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "short_link", indexes = {
    @Index(name = "idx_short_code", columnList = "shortCode", unique = true),
    @Index(name = "idx_origin_url", columnList = "originUrl"),
    @Index(name = "idx_expire_time", columnList = "expireTime")
})
public class ShortLink {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 2048)
    private String originUrl;

    @Column(nullable = false, length = 16, unique = true)
    private String shortCode;

    @Column(length = 255)
    private String description;

    private LocalDateTime expireTime;

    @Column(nullable = false)
    private Boolean enabled = true;

    @Column(nullable = false)
    private Long pvCount = 0L;

    @Column(nullable = false)
    private Long uvCount = 0L;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime createTime;

    @UpdateTimestamp
    @Column(nullable = false)
    private LocalDateTime updateTime;
}
