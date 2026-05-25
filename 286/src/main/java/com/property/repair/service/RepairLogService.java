package com.property.repair.service;

import com.property.repair.entity.RepairLog;
import com.property.repair.entity.RepairOrder;
import com.property.repair.repository.RepairLogRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class RepairLogService {

    @Autowired
    private RepairLogRepository repairLogRepository;

    public void addLog(RepairOrder order, String action, Long operatorId, String operatorName, String remark) {
        RepairLog log = new RepairLog();
        log.setOrderId(order.getId());
        log.setOrderNo(order.getOrderNo());
        log.setAction(action);
        log.setOperatorId(operatorId);
        log.setOperatorName(operatorName);
        log.setRemark(remark);
        repairLogRepository.save(log);
    }

    public List<RepairLog> getOrderLogs(Long orderId) {
        return repairLogRepository.findByOrderIdOrderByCreateTimeDesc(orderId);
    }
}
