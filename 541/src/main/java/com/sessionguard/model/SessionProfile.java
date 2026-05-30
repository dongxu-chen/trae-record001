package com.sessionguard.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SessionProfile implements Serializable {

    private static final long serialVersionUID = 1L;

    private String sessionId;

    private String userId;

    private String cookieId;

    private IpContext ipContext;

    private DeviceFingerprint deviceFingerprint;

    private LocalDateTime createdAt;

    private LocalDateTime lastAccessedAt;

    private LocalDateTime lastVerifiedAt;

    private String lastActiveRegion;

    private int accessCount;

    private boolean active;

    private boolean invalidated;

    private String invalidationReason;
}
