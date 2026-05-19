package com.payment.reconciliation.ddd.application.handler;

import com.payment.reconciliation.ddd.application.command.CreateReconciliationCommand;
import com.payment.reconciliation.ddd.core.CommandHandler;
import com.payment.reconciliation.ddd.domain.aggregate.ReconciliationAggregate;
import com.payment.reconciliation.ddd.domain.repository.ReconciliationRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CreateReconciliationHandler implements CommandHandler<CreateReconciliationCommand, String> {

    private static final Logger log = LoggerFactory.getLogger(CreateReconciliationHandler.class);

    @Autowired
    private ReconciliationRepository reconciliationRepository;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public String handle(CreateReconciliationCommand command) {
        log.info("处理创建对账命令, reconciliationNo: {}", command.getReconciliationNo());

        ReconciliationAggregate reconciliation = ReconciliationAggregate.create(
                command.getReconciliationNo(),
                command.getChannelCode(),
                command.getReconciliationDate(),
                command.getFileName(),
                command.getFilePath()
        );

        reconciliationRepository.save(reconciliation);

        log.info("对账创建成功, reconciliationNo: {}", command.getReconciliationNo());
        return command.getReconciliationNo();
    }
}
