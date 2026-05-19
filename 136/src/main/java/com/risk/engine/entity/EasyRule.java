package com.risk.engine.entity;

import lombok.Data;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "t_easy_rule", indexes = {
    @Index(name = "idx_rule_scene", columnList = "scene"),
    @Index(name = "idx_rule_status", columnList = "status"),
    @Index(name = "idx_rule_priority", columnList = "priority")
})
public class EasyRule {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "rule_code", unique = true, nullable = false, length = 128)
    private String ruleCode;

    @Column(name = "rule_name", nullable = false, length = 256)
    private String ruleName;

    @Column(name = "description", length = 512)
    private String description;

    @Column(name = "scene", length = 64)
    private String scene = "DEFAULT";

    @Column(name = "priority")
    private Integer priority = 0;

    @Column(name = "condition_type", length = 32)
    private String conditionType = "MVEL";

    @Lob
    @Column(name = "condition_expr", columnDefinition = "TEXT")
    private String conditionExpr;

    @Column(name = "action_type", length = 32)
    private String actionType = "MVEL";

    @Lob
    @Column(name = "action_expr", columnDefinition = "TEXT")
    private String actionExpr;

    @Lob
    @Column(name = "yaml_content", columnDefinition = "TEXT")
    private String yamlContent;

    @Column(name = "status", length = 16)
    private String status = "DISABLED";

    @Column(name = "version", length = 32)
    private String version;

    @Column(name = "tags", length = 256)
    private String tags;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @Column(name = "update_time")
    private LocalDateTime updateTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
        updateTime = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updateTime = LocalDateTime.now();
    }
}
