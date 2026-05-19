package com.configcenter.approval.repository;

import com.configcenter.approval.entity.ConfigApproval;
import com.configcenter.common.repository.InMemoryRepository;
import org.springframework.stereotype.Repository;

import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;

@Repository
public class ApprovalRepository extends InMemoryRepository<ConfigApproval, String> {

    public List<ConfigApproval> findByServiceName(String serviceName) {
        return storage.values().stream()
                .filter(a -> serviceName.equals(a.getServiceName()))
                .sorted(Comparator.comparing(ConfigApproval::getRequestedAt).reversed())
                .collect(Collectors.toList());
    }

    public List<ConfigApproval> findByStatus(ConfigApproval.ApprovalStatus status) {
        return storage.values().stream()
                .filter(a -> status == a.getStatus())
                .sorted(Comparator.comparing(ConfigApproval::getRequestedAt).reversed())
                .collect(Collectors.toList());
    }

    public List<ConfigApproval> findByRequestedBy(String requestedBy) {
        return storage.values().stream()
                .filter(a -> requestedBy.equals(a.getRequestedBy()))
                .sorted(Comparator.comparing(ConfigApproval::getRequestedAt).reversed())
                .collect(Collectors.toList());
    }
}
