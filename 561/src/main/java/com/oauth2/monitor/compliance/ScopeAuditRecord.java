package com.oauth2.monitor.compliance;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ScopeAuditRecord {

    private String auditId;
    private String clientId;
    private String userId;
    private Set<String> requestedScopes;
    private String grantType;
    private String ipAddress;
    private Instant timestamp;
    private boolean hasViolations;
    private Set<String> violations;

    @Builder.Default
    private Set<String> historicScopes = ConcurrentHashMap.newKeySet();

    public void addHistoricScopes(Set<String> scopes) {
        if (scopes != null) {
            this.historicScopes.addAll(scopes);
        }
    }

    public Set<String> getHistoricScopes() {
        return new HashSet<>(historicScopes);
    }

    public boolean hasNewSensitiveScope(Set<String> sensitiveScopes) {
        if (historicScopes == null || historicScopes.isEmpty()) {
            return false;
        }
        Set<String> newlyRequested = new HashSet<>(requestedScopes);
        newlyRequested.removeAll(historicScopes);
        newlyRequested.retainAll(sensitiveScopes);
        return !newlyRequested.isEmpty();
    }
}
