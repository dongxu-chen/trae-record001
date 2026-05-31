package com.datacheck.repair;

import com.datacheck.check.CheckEngine;
import com.datacheck.datasource.DataSourceAdapter;
import com.datacheck.datasource.DataSourceAdapterFactory;
import com.datacheck.model.CheckTask;
import com.datacheck.model.DataRecord;
import com.datacheck.model.DiffResult;
import com.datacheck.model.enums.DiffType;
import com.datacheck.model.enums.RepairStatus;
import com.datacheck.service.WebSocketService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.TransactionStatus;
import org.springframework.transaction.support.DefaultTransactionDefinition;

@Slf4j
@Service
public class AutoRepairService {

    private final DataSourceAdapterFactory adapterFactory;
    private final WebSocketService webSocketService;
    private final CheckEngine checkEngine;
    private final PlatformTransactionManager transactionManager;

    @Value("${check.auto-repair.enabled:true}")
    private boolean autoRepairEnabled;

    @Value("${check.auto-repair.transactional:true}")
    private boolean transactionalRepair;

    @Autowired
    public AutoRepairService(DataSourceAdapterFactory adapterFactory,
                             WebSocketService webSocketService,
                             CheckEngine checkEngine,
                             PlatformTransactionManager transactionManager) {
        this.adapterFactory = adapterFactory;
        this.webSocketService = webSocketService;
        this.checkEngine = checkEngine;
        this.transactionManager = transactionManager;
    }

    @Async("repairTaskExecutor")
    public void repair(DiffResult diff, CheckTask task) {
        if (!autoRepairEnabled && (task.getAutoRepair() == null || !task.getAutoRepair())) {
            log.debug("Auto repair disabled, skipping repair for diff: {}", diff.getId());
            return;
        }

        diff.setRepairStatus(RepairStatus.IN_PROGRESS);
        webSocketService.sendRepairUpdate(diff);

        boolean success = false;
        String errorMessage = null;

        if (transactionalRepair) {
            DefaultTransactionDefinition def = new DefaultTransactionDefinition();
            def.setName("repair-" + diff.getId());
            def.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
            def.setIsolationLevel(TransactionDefinition.ISOLATION_READ_COMMITTED);

            TransactionStatus status = transactionManager.getTransaction(def);
            try {
                success = doRepair(diff, task);
                if (success) {
                    transactionManager.commit(status);
                } else {
                    transactionManager.rollback(status);
                    errorMessage = "Repair operation returned false";
                }
            } catch (Exception e) {
                transactionManager.rollback(status);
                errorMessage = e.getMessage();
                log.error("Repair transaction rolled back for diff: {}", diff.getId(), e);
            }
        } else {
            try {
                success = doRepair(diff, task);
                if (!success) {
                    errorMessage = "Repair operation returned false";
                }
            } catch (Exception e) {
                errorMessage = e.getMessage();
                log.error("Repair failed for diff: {}", diff.getId(), e);
            }
        }

        diff.setRepairStatus(success ? RepairStatus.SUCCESS : RepairStatus.FAILED);
        diff.setRepairAttempts(1);
        diff.setRepairErrorMessage(errorMessage);
        webSocketService.sendRepairUpdate(diff);
        checkEngine.updateDiff(diff);

        log.info("Repair {} for diff: {}, key: {}, type: {}, transactional: {}",
                success ? "succeeded" : "failed", diff.getId(), diff.getKey(),
                diff.getDiffType(), transactionalRepair);
    }

    private boolean doRepair(DiffResult diff, CheckTask task) {
        DataSourceAdapter adapter = adapterFactory.getAdapter(diff.getSourceType());

        return switch (diff.getDiffType()) {
            case MISSING_IN_TARGET -> repairMissingInTarget(diff, adapter, task);
            case MISSING_IN_SOURCE -> repairMissingInSource(diff, adapter, task);
            case VALUE_MISMATCH -> repairValueMismatch(diff, adapter, task);
            case LATENCY_EXCEEDED -> verifyLatency(diff, adapter, task);
        };
    }

    private boolean repairMissingInTarget(DiffResult diff, DataSourceAdapter adapter, CheckTask task) {
        if (diff.getSourceData() == null) {
            log.warn("Cannot repair missing in target, no source data for key: {}", diff.getKey());
            return false;
        }
        DataRecord record = DataRecord.builder()
                .key(diff.getKey())
                .data(diff.getSourceData())
                .sourceType(diff.getSourceType())
                .timestamp(System.currentTimeMillis())
                .tableName(diff.getTableName())
                .build();
        return adapter.insertTarget(record, task);
    }

    private boolean repairMissingInSource(DiffResult diff, DataSourceAdapter adapter, CheckTask task) {
        return adapter.deleteTarget(diff.getKey(), task);
    }

    private boolean repairValueMismatch(DiffResult diff, DataSourceAdapter adapter, CheckTask task) {
        if (diff.getSourceData() == null) {
            log.warn("Cannot repair value mismatch, no source data for key: {}", diff.getKey());
            return false;
        }
        DataRecord record = DataRecord.builder()
                .key(diff.getKey())
                .data(diff.getSourceData())
                .sourceType(diff.getSourceType())
                .timestamp(System.currentTimeMillis())
                .tableName(diff.getTableName())
                .build();

        DataRecord existing = adapter.getTargetRecord(diff.getKey(), task);
        if (existing == null) {
            return adapter.insertTarget(record, task);
        } else {
            return adapter.updateTarget(record, task);
        }
    }

    private boolean verifyLatency(DiffResult diff, DataSourceAdapter adapter, CheckTask task) {
        try {
            Thread.sleep(1000);
            DataRecord sourceRecord = adapter.getSourceRecord(diff.getKey(), task);
            DataRecord targetRecord = adapter.getTargetRecord(diff.getKey(), task);

            if (sourceRecord != null && targetRecord != null) {
                long newLatency = Math.abs(sourceRecord.getTimestamp() - targetRecord.getTimestamp());
                long threshold = task.getLatencyThresholdMs() != null ?
                        task.getLatencyThresholdMs() : 5000;
                return newLatency <= threshold;
            }
            return false;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return false;
        }
    }
}
