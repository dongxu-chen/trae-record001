package com.property.repair.service;

import com.property.repair.entity.RepairOrder;
import com.property.repair.entity.RepairType;
import com.property.repair.repository.RepairOrderRepository;
import com.property.repair.websocket.NotificationWebSocket;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Service
public class RemindService {

    @Autowired
    private RepairOrderRepository orderRepository;

    @Autowired
    private RepairTypeService repairTypeService;

    @Autowired
    private NotificationWebSocket webSocket;

    @Autowired
    private RepairLogService logService;

    @Value("${repair.remind.default-overdue-minutes:60}")
    private Integer defaultOverdueMinutes;

    @Value("${repair.remind.default-interval-minutes:30}")
    private Integer defaultIntervalMinutes;

    @Value("${repair.remind.emergency-overdue-minutes:15}")
    private Integer emergencyOverdueMinutes;

    @Value("${repair.remind.emergency-interval-minutes:10}")
    private Integer emergencyIntervalMinutes;

    @Scheduled(fixedDelay = 60000)
    public void checkOverdueOrders() {
        List<RepairOrder> assignedOrders = orderRepository.findByStatus("ASSIGNED");

        for (RepairOrder order : assignedOrders) {
            if (order.getAssignTime() == null) {
                continue;
            }

            int remindMinutes = getRemindMinutes(order);
            int intervalMinutes = getIntervalMinutes(order);
            LocalDateTime overdueTime = LocalDateTime.now().minusMinutes(remindMinutes);

            if (order.getAssignTime().isBefore(overdueTime)) {
                if (order.getLastRemindTime() == null || 
                    order.getLastRemindTime().plusMinutes(intervalMinutes).isBefore(LocalDateTime.now())) {
                    remindWorker(order);
                }
            }
        }
    }

    private int getRemindMinutes(RepairOrder order) {
        if (order.getRepairTypeId() != null) {
            RepairType type = repairTypeService.getById(order.getRepairTypeId());
            if (type != null && type.getRemindMinutes() != null) {
                return type.getRemindMinutes();
            }
            if (type != null && Boolean.TRUE.equals(type.getIsEmergency())) {
                return emergencyOverdueMinutes;
            }
        }
        return defaultOverdueMinutes;
    }

    private int getIntervalMinutes(RepairOrder order) {
        if (order.getRepairTypeId() != null) {
            RepairType type = repairTypeService.getById(order.getRepairTypeId());
            if (type != null && Boolean.TRUE.equals(type.getIsEmergency())) {
                return emergencyIntervalMinutes;
            }
        }
        return defaultIntervalMinutes;
    }

    private void remindWorker(RepairOrder order) {
        order.setRemindCount(order.getRemindCount() + 1);
        order.setLastRemindTime(LocalDateTime.now());
        orderRepository.save(order);

        boolean isEmergency = isEmergencyOrder(order);
        String message = isEmergency ? 
            "【紧急】您有一张紧急故障工单即将超时，请立即处理！" : 
            "您有一张工单即将超时，请尽快处理！";

        webSocket.sendToWorker(order.getWorkerId(), "REMIND", Map.of(
            "orderId", order.getId(),
            "orderNo", order.getOrderNo(),
            "message", message,
            "remindCount", order.getRemindCount(),
            "isEmergency", isEmergency
        ));

        logService.addLog(order, "超时催办", 1L, "系统", 
            "第" + order.getRemindCount() + "次催办，" + 
            (isEmergency ? "【紧急】" : "") + "提醒维修工尽快接单");
    }

    private boolean isEmergencyOrder(RepairOrder order) {
        if (order.getRepairTypeId() != null) {
            RepairType type = repairTypeService.getById(order.getRepairTypeId());
            return type != null && Boolean.TRUE.equals(type.getIsEmergency());
        }
        return false;
    }

    public void notifyNewOrder(RepairOrder order) {
        if (order.getWorkerId() != null) {
            webSocket.sendToWorker(order.getWorkerId(), "NEW_ORDER", Map.of(
                "orderId", order.getId(),
                "orderNo", order.getOrderNo(),
                "repairType", order.getRepairTypeName(),
                "address", order.getAddress(),
                "message", "您有新的维修工单，请及时接单"
            ));
        }
    }

    public void notifyOrderStatusChange(RepairOrder order) {
        webSocket.sendToOwner(order.getOwnerId(), "STATUS_CHANGE", Map.of(
            "orderId", order.getId(),
            "orderNo", order.getOrderNo(),
            "status", order.getStatus(),
            "message", getStatusMessage(order.getStatus())
        ));
    }

    private String getStatusMessage(String status) {
        switch (status) {
            case "ASSIGNED":
                return "您的工单已分配维修工";
            case "IN_PROGRESS":
                return "维修工已接单，正在处理中";
            case "COMPLETED":
                return "工单已完成，请进行评价";
            case "EVALUATED":
                return "工单已评价完成";
            default:
                return "工单状态已更新";
        }
    }
}
