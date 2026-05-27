package com.sso.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;
import java.util.HashSet;
import java.util.Set;

@Data
@Entity
@Table(name = "sso_applications")
public class Application {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "app_code", unique = true, nullable = false, length = 50)
    private String appCode;

    @Column(name = "app_name", nullable = false, length = 100)
    private String appName;

    @Column(name = "description")
    private String description;

    @Column(name = "app_url")
    private String appUrl;

    @Column(name = "icon_url")
    private String iconUrl;

    @Column(name = "protocol", length = 20)
    private String protocol;

    @Column(name = "client_id")
    private String clientId;

    @Column(name = "enabled")
    private boolean enabled = true;

    @Column(name = "visible_in_portal")
    private boolean visibleInPortal = true;

    @Column(name = "sort_order")
    private int sortOrder = 0;

    @ManyToMany(fetch = FetchType.LAZY)
    @JoinTable(
            name = "sso_application_permissions",
            joinColumns = @JoinColumn(name = "application_id"),
            inverseJoinColumns = @JoinColumn(name = "permission_id")
    )
    private Set<Permission> permissions = new HashSet<>();

    @ManyToMany(fetch = FetchType.LAZY)
    @JoinTable(
            name = "sso_application_roles",
            joinColumns = @JoinColumn(name = "application_id"),
            inverseJoinColumns = @JoinColumn(name = "role_id")
    )
    private Set<Role> allowedRoles = new HashSet<>();

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
