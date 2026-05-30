package com.taskflow.repository;

import com.taskflow.model.Trigger;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface TriggerRepository extends JpaRepository<Trigger, Long> {
    List<Trigger> findByWorkflowId(Long workflowId);
    List<Trigger> findByEnabledTrue();
    List<Trigger> findByTriggerTypeAndEnabledTrue(String triggerType);
    Optional<Trigger> findByWebhookPath(String webhookPath);
}
