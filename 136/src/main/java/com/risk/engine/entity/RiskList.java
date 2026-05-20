package com.risk.engine.entity;

import lombok.Data;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "t_risk_list")
public class RiskList {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "list_type", nullable = false, length = 16)
    private String listType;

    @Column(name = "match_type", nullable = false, length = 16)
    private String matchType;

    @Column(name = "field_name", nullable = false, length = 64)
    private String fieldName;

    @Column(name = "field_value", nullable = false, length = 512)
    private String fieldValue;

    @Column(name = "list_desc", length = 256)
    private String listDesc;

    @Column(name = "status", nullable = false, length = 16)
    private String status = "ENABLED";

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @Column(name = "expire_time")
    private LocalDateTime expireTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
    }
}
