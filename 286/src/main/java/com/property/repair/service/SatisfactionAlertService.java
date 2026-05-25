package com.property.repair.service;

import com.property.repair.entity.RepairEvaluation;
import com.property.repair.entity.RepairWorker;
import com.property.repair.entity.SatisfactionAlert;
import com.property.repair.repository.RepairEvaluationRepository;
import com.property.repair.repository.RepairWorkerRepository;
import com.property.repair.repository.SatisfactionAlertRepository;
import com.property.repair.websocket.NotificationWebSocket;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class SatisfactionAlertService {

    @Autowired
    private SatisfactionAlertRepository alertRepository;

    @Autowired
    private RepairWorkerRepository workerRepository;

    @Autowired
    private RepairEvaluationRepository evaluationRepository;

    @Autowired
    private NotificationWebSocket webSocket;

    @Value("${satisfaction.low-rating-threshold:2}")
    private Integer lowRatingThreshold;

    @Value("${satisfaction.consecutive-threshold:3}")
    private Integer consecutiveThreshold;

    @Value("${satisfaction.training-days:7}")
    private Integer trainingDays;

    @Transactional
    public void checkAndCreateAlert(RepairEvaluation evaluation) {
        if (evaluation.getRating() == null || evaluation.getRating() > lowRatingThreshold) {
            resetConsecutiveLowRatings(evaluation.getWorkerId());
            return;
        }

        RepairWorker worker = workerRepository.findByWorkerId(evaluation.getWorkerId());
        if (worker == null) {
            return;
        }

        int consecutive = (worker.getConsecutiveLowRatings() == null ? 0 : worker.getConsecutiveLowRatings()) + 1;
        worker.setConsecutiveLowRatings(consecutive);

        SatisfactionAlert alert = new SatisfactionAlert();
        alert.setWorkerId(evaluation.getWorkerId());
        alert.setWorkerName(worker.getId().toString());
        alert.setAlertType("LOW_RATING");
        alert.setOrderId(evaluation.getOrderId());
        alert.setOrderNo(evaluation.getOrderNo());
        alert.setRating(evaluation.getRating());
        alert.setComment(evaluation.getComment());

        if (consecutive >= consecutiveThreshold) {
            alert.setAlertLevel("WARNING");
            worker.setNeedTraining(true);
            worker.setTrainingStartTime(LocalDateTime.now());
            worker.setTrainingEndTime(LocalDateTime.now().plusDays(trainingDays));
            
            sendTrainingAlert(worker);
        } else {
            alert.setAlertLevel("INFO");
        }

        alertRepository.save(alert);
        workerRepository.save(worker);
    }

    private void resetConsecutiveLowRatings(Long workerId) {
        RepairWorker worker = workerRepository.findByWorkerId(workerId);
        if (worker != null && worker.getConsecutiveLowRatings() != null && worker.getConsecutiveLowRatings() > 0) {
            worker.setConsecutiveLowRatings(0);
            workerRepository.save(worker);
        }
    }

    private void sendTrainingAlert(RepairWorker worker) {
        Map<String, Object> alertData = new HashMap<>();
        alertData.put("workerId", worker.getWorkerId());
        alertData.put("alertType", "TRAINING_REQUIRED");
        alertData.put("message", "您因连续" + consecutiveThreshold + "次差评，已被标记需要参加培训！");
        alertData.put("trainingDays", trainingDays);

        webSocket.sendToWorker(worker.getWorkerId(), "SATISFACTION_ALERT", alertData);
        webSocket.broadcast("ADMIN_ALERT", Map.of(
            "type", "WORKER_TRAINING",
            "workerId", worker.getWorkerId(),
            "message", "维修工ID:" + worker.getWorkerId() + " 因连续差评需要培训"
        ));
    }

    @Scheduled(cron = "0 0 9 * * ?")
    public void checkTrainingExpiry() {
        List<RepairWorker> workers = workerRepository.findByStatus(1);
        for (RepairWorker worker : workers) {
            if (Boolean.TRUE.equals(worker.getNeedTraining()) && 
                worker.getTrainingEndTime() != null &&
                worker.getTrainingEndTime().isBefore(LocalDateTime.now())) {
                worker.setNeedTraining(false);
                worker.setTrainingStartTime(null);
                worker.setTrainingEndTime(null);
                worker.setConsecutiveLowRatings(0);
                workerRepository.save(worker);
            }
        }
    }

    @Transactional
    public SatisfactionAlert handleAlert(Long alertId, Long handlerId, String handlerName, 
                                         String remark, boolean completeTraining) {
        SatisfactionAlert alert = alertRepository.findById(alertId).orElse(null);
        if (alert == null) {
            throw new RuntimeException("预警不存在");
        }

        alert.setStatus("HANDLED");
        alert.setHandlerId(handlerId);
        alert.setHandlerName(handlerName);
        alert.setRemark(remark);
        alert.setHandleTime(LocalDateTime.now());
        alert = alertRepository.save(alert);

        if (completeTraining && alert.getWorkerId() != null) {
            RepairWorker worker = workerRepository.findByWorkerId(alert.getWorkerId());
            if (worker != null) {
                worker.setNeedTraining(false);
                worker.setTrainingStartTime(null);
                worker.setTrainingEndTime(null);
                worker.setConsecutiveLowRatings(0);
                workerRepository.save(worker);
            }
        }

        return alert;
    }

    public List<SatisfactionAlert> getPendingAlerts() {
        return alertRepository.findByStatus("PENDING");
    }

    public List<SatisfactionAlert> getWorkerAlerts(Long workerId) {
        return alertRepository.findByWorkerIdOrderByCreateTimeDesc(workerId);
    }

    public List<SatisfactionAlert> getRecentAlerts(int days) {
        LocalDateTime startTime = LocalDateTime.now().minusDays(days);
        return alertRepository.findAll().stream()
            .filter(a -> a.getCreateTime().isAfter(startTime))
            .sorted((a, b) -> b.getCreateTime().compareTo(a.getCreateTime()))
            .collect(java.util.stream.Collectors.toList());
    }

    public boolean isWorkerInTraining(Long workerId) {
        RepairWorker worker = workerRepository.findByWorkerId(workerId);
        if (worker == null) {
            return false;
        }
        if (!Boolean.TRUE.equals(worker.getNeedTraining())) {
            return false;
        }
        if (worker.getTrainingEndTime() == null) {
            return true;
        }
        return worker.getTrainingEndTime().isAfter(LocalDateTime.now());
    }
}
