package com.filetransfer.repository;

import com.filetransfer.entity.DistributionRecipient;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface DistributionRecipientRepository extends JpaRepository<DistributionRecipient, Long> {
    List<DistributionRecipient> findByDistributionId(String distributionId);
    Optional<DistributionRecipient> findByDistributionIdAndRecipientTypeAndRecipientIdentifier(
            String distributionId, String recipientType, String recipientIdentifier);
}
