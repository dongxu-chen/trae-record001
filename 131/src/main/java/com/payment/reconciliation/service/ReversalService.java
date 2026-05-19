package com.payment.reconciliation.service;

import com.payment.reconciliation.entity.Discrepancy;
import com.payment.reconciliation.entity.ReversalTask;

import java.util.List;

public interface ReversalService {

    ReversalTask createReversalTask(Discrepancy discrepancy);

    void processReversalTasks();

    void executeReversalTask(ReversalTask task);

    ReversalTask getReversalTaskById(Long id);

    List<ReversalTask> listReversalTasks(String channelCode, Integer status);
}
